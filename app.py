from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import plotly.graph_objects as go
import streamlit as st
import pdfplumber
import fitz
import json
import re

st.set_page_config(page_title="BRSR Gap Analysis Tool", layout="wide")
st.markdown("""
<style>
    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    h1 {
        font-weight: 800 !important;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #2ecc71, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    div[data-testid="stMetric"] {
        background-color: #1a1f2b !important;
        border: 1px solid #2a2f3b;
        border-radius: 12px;
        padding: 20px 15px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] div {
        color: #fafafa !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 20px rgba(46, 204, 113, 0.15);
    }
    h2, h3 {
        border-bottom: 2px solid #2ecc71;
        padding-bottom: 8px;
        display: inline-block;
    }
    div[data-testid="stFileUploader"] {
        border-radius: 12px;
    }
    div[data-testid="stTable"] {
        border-radius: 10px;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] {
        background-color: #14181f !important;
        border-right: 1px solid #2a2f3b;
    }
    section[data-testid="stSidebar"] * {
        color: #fafafa !important;
    }
    html {
        scroll-behavior: smooth;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("ℹ️ About this tool")
    st.write(
        "This tool scans any company's BRSR (Business Responsibility and "
        "Sustainability Report) filing and checks it against SEBI's "
        "**BRSR Core** — the 9 ESG attributes requiring third-party assurance."
    )
    st.divider()
    st.subheader("How to use")
    st.markdown(
        "1. Upload a company's Annual Report or standalone BRSR PDF\n"
        "2. The tool locates the Principle-wise disclosure section\n"
        "3. Each disclosure is checked against BRSR Core requirements\n"
        "4. View results as charts, tables, or a downloadable report"
    )
    st.divider()
    st.markdown(
        "Built by **Karan Thakur** · "
        "[GitHub](https://github.com/karan02566-prog) · "
        "[LinkedIn](https://www.linkedin.com/in/karan-thakur-3486b538a/)"
    )

st.title("📊 BRSR Gap Analysis Tool")
st.markdown(
    "##### Instantly check any Indian company's sustainability disclosures against SEBI's BRSR Core framework"
)
st.write("")

# --- Load the reference checklist (same one from Module 3) ---
with open("brsr_core_reference.json", "r") as f:
    REFERENCE = json.load(f)


# --- Reused functions from Module 1 ---
def find_brsr_section(doc, keywords=None):
    if keywords is None:
        keywords = [
            "Business Responsibility and Sustainability Report",
            "Section A: General Disclosures",
            "Section B: Management and Process",
            "Section C: Principle Wise Performance"
        ]
    hits = []
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        for kw in keywords:
            if kw.lower() in text.lower():
                hits.append({"page": page_num, "keyword": kw})
    return hits


def extract_text_pdfplumber(pdf_file, start_page, end_page):
    extracted = {}
    with pdfplumber.open(pdf_file) as pdf:
        pages = pdf.pages[start_page:end_page]
        for i, page in enumerate(pages):
            text = page.extract_text() or ""
            extracted[start_page + i] = {"text": text}
    return extracted


def chunk_by_principle(extracted_pages):
    principle_markers = [f"Principle {i}:" for i in range(1, 10)]
    full_text = "\n".join([p["text"] for p in extracted_pages.values()])
    chunks = {}
    positions = []
    for marker in principle_markers:
        for match in re.finditer(re.escape(marker), full_text, re.IGNORECASE):
            positions.append((match.start(), marker))
    positions.sort()
    for idx, (pos, marker) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(full_text)
        if marker not in chunks:
            chunks[marker] = full_text[pos:end]
    return chunks


def run_gap_analysis(all_text):
    all_text_lower = all_text.lower()
    results = []
    for attribute, details in REFERENCE.items():
        matched_keywords = [kw for kw in details["keywords"] if kw in all_text_lower]
        coverage = len(matched_keywords) / len(details["keywords"])
        if coverage >= 0.5:
            status = "✅ Covered"
        elif coverage > 0:
            status = "🟡 Partially Covered"
        else:
            status = "🔴 Missing"
        results.append({
            "Attribute": attribute,
            "Principle": details["principle"],
            "Status": status,
            "Match %": round(coverage * 100, 1)
        })
    return results


def generate_pdf_report(results, overall_score, covered_count, partial_count, missing_count, company_name="Company"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "TitleStyle", parent=styles["Heading1"], textColor=colors.HexColor("#2ecc71")
    )
    elements.append(Paragraph("BRSR Core Gap Analysis Report", title_style))
    elements.append(Paragraph(f"Company: {company_name}", styles["Normal"]))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"Overall BRSR Core Score: {overall_score}%", styles["Heading2"]))
    elements.append(Paragraph(
        f"Covered: {covered_count}   |   Partial: {partial_count}   |   Missing: {missing_count}",
        styles["Normal"]
    ))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Detailed Attribute Coverage", styles["Heading2"]))
    elements.append(Spacer(1, 10))

    table_data = [["Attribute", "Principle", "Status", "Match %"]]
    for r in results:
        status_clean = r["Status"].replace("✅ ", "").replace("🟡 ", "").replace("🔴 ", "")
        table_data.append([r["Attribute"], r["Principle"], status_clean, f"{r['Match %']}%"])

    table = Table(table_data, colWidths=[2.3 * inch, 1 * inch, 1.2 * inch, 1 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2ecc71")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f0f0")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


# --- Streamlit UI ---
uploaded_file = st.file_uploader("Upload BRSR / Annual Report PDF", type="pdf")

if uploaded_file is not None:
    with st.spinner("Scanning PDF for BRSR section..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        hits = find_brsr_section(doc)

    if not hits:
        st.error("Could not locate a BRSR section in this PDF.")
    else:
        section_c_pages = [h["page"] for h in hits if "Section C" in h["keyword"]]

        if not section_c_pages:
            principle_1_pages = []
            for page_num in range(len(doc)):
                text = doc[page_num].get_text()
                if "principle 1:" in text.lower():
                    principle_1_pages.append(page_num)
            section_c_pages = principle_1_pages

        if not section_c_pages:
            st.error("Could not locate the BRSR Principle-wise section in this PDF.")
        else:
            start_page = section_c_pages[-1]
            uploaded_file.seek(0)
            with st.spinner("Extracting and analyzing disclosures..."):
                extracted = extract_text_pdfplumber(uploaded_file, start_page, start_page + 80)
                chunks = chunk_by_principle(extracted)
                full_text = " ".join(chunks.values())
                results = run_gap_analysis(full_text)

            st.success(f"Analysis complete — found {len(chunks)} principle sections.")

            # --- Summary Cards ---
            total_attrs = len(results)
            covered_count = sum(1 for r in results if r["Status"] == "✅ Covered")
            partial_count = sum(1 for r in results if r["Status"] == "🟡 Partially Covered")
            missing_count = sum(1 for r in results if r["Status"] == "🔴 Missing")
            overall_score = round(sum(r["Match %"] for r in results) / total_attrs, 1)

            st.subheader("📋 Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Overall BRSR Core Score", f"{overall_score}%")
            col2.metric("✅ Covered", covered_count)
            col3.metric("🟡 Partial", partial_count)
            col4.metric("🔴 Missing", missing_count)

            st.divider()

            # --- Charts ---
            gauge_col, donut_col = st.columns([1, 1])

            with gauge_col:
                st.subheader("Overall Score")
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=overall_score,
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#2ecc71"},
                        "steps": [
                            {"range": [0, 50], "color": "#4a1a1a"},
                            {"range": [50, 80], "color": "#4a3a1a"},
                            {"range": [80, 100], "color": "#1a3a1a"}
                        ]
                    }
                ))
                fig_gauge.update_layout(margin=dict(t=30, b=10, l=30, r=30), height=280)
                st.plotly_chart(fig_gauge, use_container_width=True)

            with donut_col:
                st.subheader("Status Breakdown")
                fig_donut = go.Figure(data=[go.Pie(
                    labels=["Covered", "Partial", "Missing"],
                    values=[covered_count, partial_count, missing_count],
                    hole=0.5,
                    marker=dict(colors=["#2ecc71", "#f1c40f", "#e74c3c"])
                )])
                fig_donut.update_layout(
                    showlegend=True,
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=280
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            st.subheader("Coverage by Attribute")
            attr_names = [r["Attribute"] for r in results]
            match_pcts = [r["Match %"] for r in results]
            bar_colors = [
                "#2ecc71" if r["Status"] == "✅ Covered"
                else "#f1c40f" if r["Status"] == "🟡 Partially Covered"
                else "#e74c3c"
                for r in results
            ]

            fig_bar = go.Figure(data=[go.Bar(
                x=match_pcts,
                y=attr_names,
                orientation="h",
                marker=dict(color=bar_colors)
            )])
            fig_bar.update_layout(
                xaxis_title="Match %",
                margin=dict(t=10, b=10, l=10, r=10),
                height=400
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            st.subheader("Attribute Comparison (Radar)")
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=match_pcts + [match_pcts[0]],
                theta=attr_names + [attr_names[0]],
                fill='toself',
                line=dict(color="#3498db")
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False,
                margin=dict(t=30, b=30, l=60, r=60),
                height=500
            )
            st.plotly_chart(fig_radar, use_container_width=True)

            st.divider()

            st.subheader("📄 Detailed Attribute Coverage")
            st.table(results)

            # --- Downloadable PDF Report ---
            pdf_buffer = generate_pdf_report(
                results, overall_score, covered_count, partial_count, missing_count,
                company_name=uploaded_file.name.replace(".pdf", "")
            )
            st.download_button(
                label="📥 Download PDF Report",
                data=pdf_buffer,
                file_name=f"BRSR_Gap_Analysis_{uploaded_file.name.replace('.pdf', '')}.pdf",
                mime="application/pdf"
            )