# Data Management & Pipeline

⚠️ **COMPLIANCE NOTICE (CBS):**
Due to data security regulations at **Statistics Netherlands (CBS)**, the actual bibliographic datasets (containing metadata of scientific publications) are **NOT** stored in this remote repository. All sensitive data is stored locally on secure CBS servers.

## 📂 Directory Structure

This directory follows the **Cookiecutter Data Science** standard. Although the data files are not present remotely, the logical flow of data processing is as follows:

### 1. `raw/` (Immutable)
* **Description:** The original, immutable data dump.
* **Source:** Exports from *Web of Science* and *Scopus*.
* **Format:** `.ris` (Research Information Systems) or `.csv`.
* **Note:** This folder is read-only. We never modify files here programmatically.
* *Example filename:* `2024-02-15_wos_export_nlp_metrics.ris`

### 2. `intermediate/` (In-Process)
* **Description:** Transformed data that is currently being processed or screened.
* **Tools Used:** Python (preprocessing) and ASReview (screening).
* **Contents:**
    * Cleaned datasets (deduplicated).
    * ASReview project files (`.asreview`).
    * Simulation logs.

### 3. `processed/` (Final)
* **Description:** The canonical data sets for modeling and analysis.
* **Usage:** Input for the Meta-analysis (Chapter 4 of Thesis) and statistical tests.
* **Format:** Tidy `.csv` or `.rds` (for R).

---

## 🔄 Reproduction Instructions

For authorized researchers (Supervisors/Examiners) who have access to the local raw data, the pipeline can be reproduced as follows:

1.  **Place Data:** Copy the raw export file into `data/raw/`.
2.  **Configuration:** Update the filename in `src/config.yaml` (or top of script).
3.  **Run Preprocessing:** Execute `python src/preprocessing.py`.
4.  **Run Simulation:** Execute `python src/run_simulation.py`.

## 🧪 Benchmark/Dummy Data
* `dummy_data`: A small, anonymized subset (generated synthetically) is included in the root `data/dummy/` folder to demonstrate the code functionality without violating privacy rules.