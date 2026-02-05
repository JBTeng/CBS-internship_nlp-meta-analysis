# Meta-analysis:

## 🎯Project Overview
This repository contains the code and data analysis for my Master's Thesis in Statistics & Data Science at Leiden University, conducted in collaboration with **Statistics Netherlands (CBS)**.

### **Objective:**
This study performs a three-level meta-analysis on NLP models applied to high-dimensional/structural Automated Coding tasks (occupation coding, clinical coding, etc.).


## 📅 Schedule (preliminary)
| Task | Schedule |
| :--- | :--- |
| **Onboarding & Organization** | 🧠 Feb W1, Feb W2 |
| **Refining project scope & goals** | 🧠 Feb W1, Feb W2 |
| **Tool setup (Python/ASReview/Git)** | 🧠 Feb W1, Feb W2 |
| **Writing thesis proposal** | ✍ Feb W3 - Mar W2 |
| **Submit thesis proposal (Milestone)** | ❗ Mar W2 |
| **Literature Search & Deduplication** | 🖥️ Mar W3, Mar W4 |
| **ASReview Screening (Active Learning)** | 🖥️ Mar W4 - Apr W2 |
| **Full-text Retrieval & Eligibility** | 👀 Apr W3, Apr W4 |
| **Data Extraction & Quality Assessment** | 🖥️ May W1 - May W4 |
| **Data Analysis in R (Meta-analysis)** | 🖥️ May W3 - Jun W4 |
| **Writing research report (Draft)** | ✍ Jun W1 - Jul W2 |
| **Review & Revisions** | 🤔 Jul W3, Jul W4 |
| **Final Presentation (Milestone)** | ❗ Aug W1 |
| **Submit Final Thesis (Milestone)** | ❗ Aug W1 |

## 📂 Repository Structure (preliminary)

The project directory is organized as follows:

```text
├── data/
│   ├── raw/               # Raw bibliographic data (e.g., .ris, .csv)
│   ├── intermediate/      # Data during ASReview screening
│   └── processed/         # Final dataset for meta-analysis
│   └── README.md          # Note: Real data is stored locally for CBS security compliance
├── notebooks/             # Jupyter Notebooks for exploration and visualization
├── src/                   # Source code for data processing and analysis
│   ├── __init__.py
│   ├── preprocessing.py   # Scripts to clean text data
│   └── analysis.py        # Statistical models (Meta-analysis)
├── results/               # Generated outputs
│   ├── figures/           # Forest plots, Funnel plots
│   └── tables/            # Summary statistics tables
├── .gitignore             # Specifies intentionally untracked files
├── README.md              # Project overview and instructions
└── requirements.txt       # Python dependencies (e.g., asreview, pandas)
```

## 🛠️Tools Used
* **ASReview:** For active learning-based literature screening.
* **Python:** For data extraction and statistical analysis.
* **R:** For meta-analytical modeling (metafor package).

## Repository Structure
* `src/`: Scripts for data processing.
* `notebooks/`: Exploratory data analysis.
* `results/`: Generated Forest plots and statistical tables.

## Reproducibility
To reproduce the screening process:
1. Install dependencies: `pip install -r requirements.txt`
2. Run the simulation script: `python src/asreview_simulation.py`

## Contact
[Shangheng Teng] - [tengsh02@gmail.com]
Internal Supervisors: Joep Burger, Jonas Klingwort (CBS)
