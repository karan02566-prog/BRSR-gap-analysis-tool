# 📊 BRSR Gap Analysis Tool

A web app that automatically checks any Indian company's **BRSR (Business Responsibility and Sustainability Report)** filing against SEBI's **BRSR Core** — the 9 ESG attributes requiring third-party assurance.

Upload a company's Annual Report or standalone BRSR PDF and instantly see:
- Overall BRSR Core coverage score
- Attribute-by-attribute breakdown (Covered / Partially Covered / Missing)
- Interactive charts (gauge, donut, bar, radar)
- A downloadable PDF summary report

## 🔗 Live Demo

[Try it here](#) <!-- add your Streamlit Cloud link once deployed -->

## 🧠 How it works

1. **PDF Parsing** — Locates the "Principle-wise Performance" section of a BRSR filing using PyMuPDF and pdfplumber, handling formatting inconsistencies across different companies' reports (e.g. capitalization differences, varying section headers).
2. **Text Chunking** — Splits the filing into its 9 constituent Principles (P1–P9) for structured analysis.
3. **Gap Analysis** — Compares extracted disclosures against a reference checklist of BRSR Core's 9 ESG attributes using keyword matching, flagging each as Covered, Partially Covered, or Missing.
4. **Reporting** — Renders results as interactive visualizations and generates a downloadable PDF summary.

## 🛠️ Tech Stack

- **Streamlit** — web app framework
- **PyMuPDF / pdfplumber** — PDF text extraction
- **Plotly** — interactive charts
- **ReportLab** — PDF report generation
- **Claude (Anthropic)** — used in a companion pipeline for deep structured disclosure extraction on case-study companies (Tata Steel, Infosys, ITC)

## 🚀 Running locally

```bash
git clone https://github.com/karan02566-prog/brsr-gap-analysis-tool.git
cd brsr-gap-analysis-tool
pip install -r requirements.txt
streamlit run app.py
```

## 📁 Project Structure

```
├── app.py                      # Main Streamlit web app
├── brsr_core_reference.json    # BRSR Core attribute reference checklist
├── requirements.txt            # Python dependencies
└── README.md
```

## 🎯 Why I built this

As part of exploring ESG/sustainability data analytics, I wanted to understand how BRSR compliance actually gets assessed in practice. This tool automates a first-pass gap analysis that would otherwise require manually cross-referencing a 100+ page report against SEBI's disclosure requirements — the kind of work ESG analysts and consultants do by hand.

## 👤 About Me

Built by **Karan Thakur** — Geography Honours student at Delhi University, exploring ESG analytics and sustainability consulting.

- [GitHub](https://github.com/karan02566-prog)
- [LinkedIn](https://www.linkedin.com/in/karan-thakur-3486b538a/)
