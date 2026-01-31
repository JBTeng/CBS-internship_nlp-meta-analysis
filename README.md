# Meta-analysis:

## Project Overview
This repository contains the code and data analysis for my Master's Thesis in Statistics & Data Science at Leiden University, conducted in collaboration with **Statistics Netherlands (CBS)**.

**Objective:**

## 📂 Repository Structure

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

## Tools Used
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
