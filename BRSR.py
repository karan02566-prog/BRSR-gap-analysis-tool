# BRSR Gap Analysis Tool — Module 1: PDF Extraction
# Install dependencies

import pdfplumber
import fitz  # PyMuPDF, better for scanned/complex layouts
import json
import re
from pathlib import Path

def extract_text_pdfplumber(pdf_path, start_page=None, end_page=None):
    """
    Extract text page-by-page using pdfplumber.
    BRSR reports are often 100+ pages with the BRSR section embedded
    inside the annual report — use start_page/end_page once you've
    located the BRSR section manually.
    """
    extracted = {}
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[start_page:end_page] if start_page else pdf.pages
        for i, page in enumerate(pages):
            page_num = (start_page or 0) + i
            text = page.extract_text() or ""
            tables = page.extract_tables()
            extracted[page_num] = {"text": text, "tables": tables}
    return extracted

def find_brsr_section(pdf_path, keywords=None):
    """
    Scans the full PDF to locate where the BRSR section starts.
    Most annual reports have it as a distinct section — search for
    standard section headers.
    """
    if keywords is None:
        keywords = [
            "Business Responsibility and Sustainability Report",
            "Section A: General Disclosures",
            "Section B: Management and Process",
            "Section C: Principle Wise Performance"
        ]
    
    doc = fitz.open(pdf_path)
    hits = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        for kw in keywords:
            if kw.lower() in text.lower():
                hits.append({"page": page_num, "keyword": kw})
    doc.close()
    return hits

def chunk_by_principle(extracted_pages, principle_markers=None):
    """
    BRSR Section C is organized by 9 Principles (P1-P9).
    This chunks raw text by principle so you can feed one
    principle at a time to Claude (better extraction accuracy
    than dumping the whole section).
    """
    if principle_markers is None:
        principle_markers = [f"Principle {i}:" for i in range(1, 10)]
    
    full_text = "\n".join([p["text"] for p in extracted_pages.values()])
    chunks = {}
    
    positions = []
    for marker in principle_markers:
        for match in re.finditer(re.escape(marker), full_text):
            positions.append((match.start(), marker))
    positions.sort()
    
    for idx, (pos, marker) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(full_text)
        if marker not in chunks:  # take first occurrence as section start
            chunks[marker] = full_text[pos:end]
    
    return chunks

# --- Usage ---
pdf_path = "tata_steel_brsr_2024.pdf"

# Step 1: locate BRSR section
hits = find_brsr_section(pdf_path)
print("BRSR section markers found at pages:", hits)

# Step 2: find the LAST occurrence of Section C (the real content, not the index)
section_c_pages = [h["page"] for h in hits if "Section C" in h["keyword"]]
section_c_start = section_c_pages[-1]

extracted = extract_text_pdfplumber(pdf_path, start_page=section_c_start, end_page=section_c_start + 80)

# Step 3: chunk by principle for cleaner Claude extraction
chunks = chunk_by_principle(extracted)

# Save raw chunks for inspection/debugging
with open("tata_steel_chunks.json", "w") as f:
    json.dump(chunks, f, indent=2)

print(f"Extracted {len(chunks)} principle sections")
for k in chunks:
    print(f"  {k}: {len(chunks[k])} chars")

#for k in chunks:
#    print(f"\n--- {k} (first 300 chars) ---")
#    print(chunks[k][:300])
#    print("...")
# --- Module 2: Structured Extraction via Claude API ---
import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()  # reads your .env file
client = Anthropic()  # automatically picks up ANTHROPIC_API_KEY from environment

def extract_disclosures(principle_text, principle_name):
    """
    Sends one principle's raw text to Claude and asks for structured
    JSON extraction of key disclosures (indicator, value, unit, year).
    """
    prompt = f"""You are analyzing a section of an Indian company's BRSR (Business
Responsibility and Sustainability Report) filing. Below is the raw text for {principle_name}.

Extract every specific disclosure you can find into a JSON array. Each item should have:
- "indicator": short description of what's being measured
- "value": the reported figure or answer (as stated, don't calculate anything)
- "unit": unit of measurement if applicable (%, GJ, number, etc.), else null
- "year": reporting period if stated, else null

Only include disclosures explicitly present in the text. Do not infer or estimate missing data.
Respond with ONLY the JSON array, no other text, no markdown formatting.

TEXT:
{principle_text}
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_output = response.content[0].text
    return raw_output

    # --- Module 3: BRSR Core Gap Analysis (no API needed, pure Python) ---

def run_gap_analysis(company_name, extracted_file, reference_file):
    """
    Compares extracted disclosures against the BRSR Core reference checklist.
    For each of the 9 core attributes, checks whether the extracted data
    contains matching disclosures (via keyword matching), and reports
    which attributes are covered vs. missing.
    """
    with open(extracted_file, "r") as f:
        extracted = json.load(f)

    with open(reference_file, "r") as f:
        reference = json.load(f)

    # Flatten all extracted indicator text into one lowercase searchable string
    all_indicator_text = ""
    for principle, disclosures in extracted.items():
        for item in disclosures:
            all_indicator_text += " " + item.get("indicator", "").lower()

    results = []
    for attribute, details in reference.items():
        matched_keywords = [kw for kw in details["keywords"] if kw in all_indicator_text]
        coverage = len(matched_keywords) / len(details["keywords"])

        if coverage >= 0.5:
            status = "Covered"
        elif coverage > 0:
            status = "Partially Covered"
        else:
            status = "Missing"

        results.append({
            "attribute": attribute,
            "principle": details["principle"],
            "status": status,
            "matched_keywords": matched_keywords,
            "coverage_pct": round(coverage * 100, 1)
        })

    return results


# --- Run gap analysis on Tata Steel ---
gap_results = run_gap_analysis(
    company_name="Tata Steel",
    extracted_file="tata_steel_extracted.json",
    reference_file="brsr_core_reference.json"
)

print("\n--- BRSR Core Gap Analysis: Tata Steel ---\n")
for r in gap_results:
    print(f"[{r['status']}] {r['attribute']} ({r['principle']}) — {r['coverage_pct']}% keyword match")

# Save results
with open("tata_steel_gap_analysis.json", "w") as f:
    json.dump(gap_results, f, indent=2)