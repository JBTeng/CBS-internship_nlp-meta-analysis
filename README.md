
# 📊 Meta-Analysis: NLP Models for Automated Coding

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![R](https://img.shields.io/badge/R-metafor-276DC3.svg)
![ASReview](https://img.shields.io/badge/Tool-ASReview-orange.svg)
![Quarto](https://img.shields.io/badge/Quarto-4185CF?logo=quarto&logoColor=white)

## 🎯 Project Overview
This repository contains the code and data analysis for my Master's Thesis in Statistics & Data Science at Leiden University, conducted in collaboration with **Statistics Netherlands (CBS)**.

### **Objective:**
This study performs a three-level meta-analysis on Natural Language Processing (NLP) models applied to high-dimensional/structural Automated Coding tasks (e.g., occupation coding, clinical coding).

## 🛠️ Tools & Tech Stack
* **Python:** For data extraction, deduplication, and preprocessing via custom CLI tools.
* **ASReview:** For active learning-based literature screening (Human-in-the-loop).
* **R & metafor:** For meta-analytical statistical modeling.
* **Quarto:** For chunk-based interactive R execution and generating publication-ready scientific reports.

## 📂 Repository Structure
The project follows a standard data science workflow, carefully separating data ingestion, manual screening, feature extraction, and statistical reporting into sequential phases.

```text
├── data/
│   ├── dummy/             # sample labeled (as relevant/irrelevant) dataset for asreview stimulation study
│   ├── raw/               # Original exports from various databases (WOS, Scopus, etc.)
│   ├── intermediate/      # Merged/Deduplicated data ready for ASReview
│   └── processed/         # Final structured datasets ready for R meta-analysis
├── src_01_screening/      # Phase 1: Data ingestion and deduplication before ASReview
│   ├── 01_ingest_and_standardize.py 
│   ├── 02_smart_deduplication.py
│   ├── 03_audit_missing.py          # Script for manual audit of missing metadata
│   └── 04_reconcile_and_finalize.py # Outputs the final .ris file for ASReview
├── src_02_extraction/     # Phase 2: Data extraction from eligible papers
│   └── 05_data_extraction.py        # Semi-automated CLI tool for data extraction
├── src_03_meta_analysis/  # Phase 3: Meta-analysis and statistical reporting
│   └── 06_meta_analysis.qmd         # Quarto document for interactive R execution
├── results/               # Generated outputs from the meta-analysis
│   ├── figures/           # Forest plots, funnel plots, etc.
│   └── tables/            # Summary statistics and regression tables
├── internship_schedule_template.csv # Timeline & progress tracking
├── .gitignore
└── README.md
```
*(Note: Real raw/processed data is stored locally for CBS security compliance and is strictly `.gitignore`d.)*

## 🚀 Pipeline & Reproducibility
This project strictly follows the **PRISMA** (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) workflow. Due to the "Human-in-the-loop" nature of this research, the pipeline alternates between automated scripts and manual operations.

**Phase 1: Pre-Screening Data Preparation**
Automatically clean and merge raw database exports, followed by a manual audit to impute missing metadata.
```bash
python src_01_screening/01_ingest_and_standardize.py
python src_01_screening/02_smart_deduplication.py
python src_01_screening/03_audit_missing.py # 🛑 Requires manual input via CLI (Command Line Interface)
python src_01_screening/04_reconcile_and_finalize.py
```

**Phase 2: Active Learning & PRISMA Screening**
1. **Title/Abstract Screening:** Conducted via the **ASReview LAB** web interface using active learning.
2. **Full-text Eligibility (PRISMA):** Manual review of the ASReview outputs to exclude papers that do not meet the strict inclusion criteria.

**Phase 3: Interactive Data Extraction**
Data extraction for the final eligible papers is performed using a custom semi-automated CLI tool. It fetches basic metadata via the Crossref API and prompts for specific statistical metrics.
```bash
python src_02_extraction/05_data_extraction.py
```

**Phase 4: Meta-Analysis & Reporting (Quarto)**
The final statistical modeling is conducted in R using **Quarto** (`.qmd`) within VS Code. 
* **To run the analysis:** Open `src_03_meta_analysis/06_meta_analysis.qmd` in VS Code and execute the R chunks sequentially.
* This chunk-based execution allows for parameter tuning and inline visualization. All final publication-ready plots and tables are automatically routed to the `results/` directory.

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
* **Internal Supervisors:** Joep Burger, Jonas Klingwort (CBS)
