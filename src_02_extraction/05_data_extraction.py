import pandas as pd
import os
import requests
import re

# ==========================================
# --- Core Path Configuration / 核心路径配置 ---
# ==========================================

# 1. Get the absolute path of the current script / 自动获取当前脚本所在的绝对路径
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Define the target file path / 拼接出目标路径
FILE_PATH = os.path.join(current_script_dir, '../data/processed/05_Data_Extraction_for_R.xlsx')

# 3. Normalize the path for cross-platform compatibility / 标准化路径 (兼容 Win/Mac)
FILE_PATH = os.path.normpath(FILE_PATH)

# ==========================================
# --- Data Dictionary / 数据字典配置 ---
# ==========================================

# Dictionary format: { "Column Name": "Prompt Description" }
COLUMNS_DICT = {
    "Study_ID": "Study ID (Auto-generated)",
    "DOI": "Digital Object Identifier",
    "First_Author": "First Author Surname",
    "Pub_Year": "Publication Year",
    "Domain": "Domain (e.g., Occupation/Industry)",
    "Class_System": "Classification System (e.g., ICD-10/ISCO-08)",
    "Num_Classes": "Total Number of Classes",
    "Task_Type": "Task Type (Single-label/Multi-label)",
    "Data_Source": "Data Source (Admin_Record/Survey/etc.)",
    "Language": "Text Language",
    "Sample_Size": "Total Sample Size",
    "Imbalance_Ratio": "Imbalance Ratio / Gini Coefficient",
    "Base_Model": "Base Model (Rule-based/LLM/etc.)",
    "Train_Paradigm": "Training Paradigm (Supervised/Zero_shot)",
    "Hierarch_Strategy": "Hierarchical Strategy (Flat/TopDown)",
    "Handle_Imbalance": "Handle Imbalance (1=Yes, 0=No)",
    "Human_in_Loop": "Human-in-the-Loop (1=Yes, 0=No)",
    "Top1_Accuracy": "Top-1 Accuracy",
    "TopK_Accuracy": "Top-K Accuracy",
    "Macro_F1": "Macro-Average F1",
    "Micro_F1": "Micro-Average F1",
    "Hierarch_Metric": "Hierarchical Metric Used (1=Yes, 0=No)"
}

def load_or_create_excel():
    """Load existing Excel or create a new one / 读取现有表格或新建"""
    if os.path.exists(FILE_PATH):
        return pd.read_excel(FILE_PATH)
    return pd.DataFrame(columns=COLUMNS_DICT.keys())

def get_next_study_num(df):
    """Parse the next study number from existing IDs / 从已有的 ID 中计算下一个编号"""
    if df.empty or "Study_ID" not in df.columns:
        return 1
    
    ids = df["Study_ID"].astype(str).tolist()
    nums = []
    for study_id in ids:
        # Match pattern like "Study_001_" / 匹配提取数字
        match = re.search(r"Study_(\d+)_", study_id)
        if match:
            nums.append(int(match.group(1)))
    
    return max(nums) + 1 if nums else 1

def fetch_info_from_doi(doi):
    """Fetch basic metadata from Crossref API / 联网抓取基础信息"""
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json().get('message', {})
            # Extract author / 提取作者
            author = data['author'][0].get('family', 'Unknown') if 'author' in data else 'Unknown'
            
            # Extract year / 提取年份
            year = ""
            if 'published-print' in data:
                year = data['published-print']['date-parts'][0][0]
            elif 'published-online' in data:
                year = data['published-online']['date-parts'][0][0]
                
            return {"First_Author": author, "Pub_Year": str(year)}
    except:
        pass # Ignore errors and return empty dict / 忽略报错，返回空字典
    return {}

def collect_data(study_id, doi, auto_info):
    """Logic for single row data entry / 单条数据录入逻辑"""
    new_data = {"Study_ID": study_id, "DOI": doi}
    
    for col, prompt in COLUMNS_DICT.items():
        if col in ["Study_ID", "DOI"]: continue # Skip auto-filled fields / 跳过已填充字段
        
        suggestion = auto_info.get(col, "")
        if suggestion:
            # Prompt with fetched suggestion / 带有抓取建议值的提示
            user_input = input(f"[{col}] {prompt} (Suggested: {suggestion}, Press Enter to confirm): ").strip()
            new_data[col] = user_input if user_input else suggestion
        else:
            # Normal prompt / 普通输入提示
            user_input = input(f"[{col}] {prompt}: ").strip()
            new_data[col] = user_input if user_input else "NA"
            
    return new_data

def save_to_excel(new_row_dict):
    """Append new row and save to Excel / 追加新行并保存"""
    df = load_or_create_excel()
    new_row_df = pd.DataFrame([new_row_dict])
    
    # Append the data / 追加数据
    df = pd.concat([df, new_row_df], ignore_index=True)
    
    try:
        df.to_excel(FILE_PATH, index=False)
        print(f"✅ Data saved successfully to: {FILE_PATH}")
        print(f"📊 Current total records: {len(df)}")
    except PermissionError:
        print("❌ Error: The Excel file is currently open. Please close it and try again!")

def main_flow():
    """Main execution loop / 主运行循环"""
    df = load_or_create_excel()
    current_study_num = get_next_study_num(df)

    while True:
        print(f"\n{'='*20} Entering Data for Study {current_study_num:03d} {'='*20}")