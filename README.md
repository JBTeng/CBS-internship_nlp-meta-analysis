
# 📊 Meta-Analysis: NLP Models for Automated Coding

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![R](https://img.shields.io/badge/R-metafor-276DC3.svg)
![ASReview](https://img.shields.io/badge/Tool-ASReview-orange.svg)
![Quarto](https://img.shields.io/badge/Quarto-4185CF?logo=quarto&logoColor=white)

## 🎯 Project Overview
This repository contains the code and data analysis for my Master's Thesis in Statistics & Data Science at Leiden University, conducted in collaboration with **Statistics Netherlands (CBS)**.

### **Objective:**
This study performs a three-level meta-analysis on Natural Language Processing (NLP) models applied to high-dimensional/structural Automated Coding tasks (e.g., occupation coding, clinical coding).

## 📂 Repository Structure
```text
├── data/
│   ├── raw/               # Raw bibliographic data (.bib, .txt, .ris)
│   ├── intermediate/      # Auto-generated files (Step 01-03)
│   │   ├── 01_preliminary_merged.ris
│   │   ├── 02_SMART_DEDUPLICATED_FINAL.ris
│   │   └── 03_incomplete_records_for_manual_fix.ris
│   └── processed/         # Human-verified data & Modeling inputs
│       ├── 03_manually_updated.ris         # YOUR manual fixes
│       ├── 04_FINAL_MERGED_DEDUPLICATED.ris # FINAL output for ASReview
│       └── 05_Data_Extraction_for_R.xlsx    # Extracted effect sizes
├── src_01_screening/      # Phase 1: Data Cleaning & Pre-screening
│   ├── 01_ingest_and_standardize.py 
│   ├── 02_smart_deduplication.py
│   ├── 03_audit_missing.py          # Generate patch file for missing metadata
│   └── 04_reconcile_and_finalize.py # Reconcile fixes + Secondary deduplication
├── src_02_extraction/     # Phase 2: Interactive Feature Extraction
│   └── 05_data_extraction.py        # Semi-automated CLI tool (Crossref API)
├── src_03_meta_analysis/  # Phase 3: Statistical Modeling
│   └── 06_meta_analysis.qmd         # Quarto interactive R analysis
├── results/               # Forest plots, Funnel plots, and Tables
├── internship_schedule_template.csv # Project timeline tracking
├── requirements.txt       # Environment dependencies
├── .gitignore             # CBS compliance: Data files are untracked
└── README.md
```

## 🛠️ Environment Setup
To ensure reproducibility, install the required Python and R environments:

**Python Dependencies:**
```bash
pip install pandas rispy rapidfuzz biopython bibtexparser requests openpyxl
```

**R Dependencies:**
Ensure R is installed with the `metafor` and `httpgd` packages.In VS Code, install the Quarto and R extensions for the best experience.
```R
install.packages("metafor")
```

## 🚀 The Research Pipeline (PRISMA-Compliant)

This project strictly follows the **PRISMA** workflow, integrating **Human-in-the-loop** interactions at critical stages.

### **Step 1: Data Pre-processing (The 01-04 Workflow)**
1. **Merge (`01`)**: Consolidate ACM, PubMed, and WoS exports into a standardized format.
2. **First Deduplication (`02`)**: Intelligent matching by DOI and Title (Cascading strategy).
3. **Quality Audit (`03`)**: Scan for missing titles/abstracts. A "patch file" is generated in `data/intermediate/`.
4. **Manual Imputation**: 
   * Copy the patch to `data/processed/` and rename to `03_manually_updated.ris`.
   * Manually fill in the `[MISSING]` tags (Title/Abstract/DOI).
5. **Reconcile & Second Deduplication (`04`)**: The script merges your fixes and re-runs deduplication, as new metadata may reveal previously hidden duplicates.

### **Step 2: ASReview & Eligibility Screening**
1. Import `04_FINAL_MERGED_DEDUPLICATED.ris` into **ASReview LAB**.
2. Perform Active Learning screening to identify relevant records.
3. Conduct **Full-text Retrieval** and **Eligibility Assessment** based on the PRISMA flow.

### **Step 3: Data Extraction (`05`)**
Run the interactive CLI tool to extract effect sizes and study characteristics:
```bash
python src_02_extraction/05_data_extraction.py
```
*Note: This script uses the Crossref API to auto-fill author and year based on DOI.*

### **Step 4: Meta-Analysis (`06`)**
Use the Quarto document in `src_03_meta_analysis/` to run the 3-level meta-analysis, investigate heterogeneity, and generate forest plots.

## 📅 Schedule (Preliminary)
| Task | Schedule |
| :--- | :--- |
| **Onboarding & Organization** | 🧠 Feb W1 - W2 |
| **Tool setup & Thesis proposal** | ✍ Feb W1 - Mar W2 |
| **Submit thesis proposal (Milestone)** | ❗ Mar W2 |
| **Literature Search & Deduplication** | 🖥️ Mar W3 - W4 |
| **ASReview Screening (Active Learning)** | 🖥️ Mar W4 - Apr W2 |
| **Full-text Retrieval & Eligibility** | 👀 Apr W3 - W4 |
| **Data Extraction & Quality Assessment** | 🖥️ May W1 - W4 |
| **Data Analysis in R (Meta-analysis)** | 🖥️ May W3 - Jun W4 |
| **Writing research report (Draft)** | ✍ Jun W1 - Jul W2 |
| **Review, Revisions & Final Presentation** | 🤔 Jul W3 - Aug W1 |

## 📧 Contact
* **Author:** Shangheng Teng ([tengsh02@gmail.com](mailto:tengsh02@gmail.com))
* **Supervisors:** Joep Burger, Jonas Klingwort (CBS)
