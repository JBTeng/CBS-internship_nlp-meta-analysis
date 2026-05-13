import pandas as pd
import os
import re
import json
import time
import google.generativeai as genai

# ==========================================
# --- 核心路径配置 (适配你的项目目录树) ---
# ==========================================
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 输出给 R 语言 Quarto 脚本使用的最终 Excel
FILE_PATH = os.path.normpath(os.path.join(current_script_dir, '../data/processed/05_Data_Extraction_for_R.xlsx'))
# 存放你需要解析的 PDF 文献的文件夹
PDF_DIR = os.path.normpath(os.path.join(current_script_dir, '../data/raw_pdfs'))

os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# ==========================================
# --- 🔑 Gemini API 配置 ---
# ==========================================
# 请替换为你从 Google AI Studio 获取的 API Key
API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=API_KEY)

# ==========================================
# --- 字段映射字典 ---
# ==========================================
COLUMNS_DICT = {
    "DOI": "Digital Object Identifier",
    "First_Author": "First Author Surname",
    "Pub_Year": "Publication Year",
    "Domain": "Domain (occupation, industry, product, etc.)",
    "Class_System": "Official System Name (ICD, ISCO, etc.)",
    "Taxonomy_Structure": "Original Taxonomy Structure (flat, hierarchical)",
    "Task_Type": "Task Formulation (Binary, Flat Multi-class, Hierarchical)",
    "Num_Classes": "Actual Number of Classes Predicted",
    "Data_Source": "Data Source",
    "Language": "Text Language",
    "Sample_Size": "Total Sample Size",
    "Avg_Text_Length": "Average Text Length",
    "Imbalance_Ratio": "Imbalance Ratio / Distribution",
    "Oversampling": "Oversampling applied? (yes/no/unknown)",
    "Undersampling": "Undersampling applied? (yes/no/unknown)",
    "Class_Weights": "Class Weights applied?",
    "Trial": "Trial Identifier (e.g., 1, 2, 3)",
    "NLP_Model": "NLP Core Algorithm",
    "Feature_Extraction": "Text Representation",
    "Feature_Selection": "Dimensionality Reduction",
    "Model_Approach": "Algorithmic Approach (Flat, Local, Global)",
    "Train_Paradigm": "Training Paradigm",
    "CV_Applied": "Cross-validation applied? (yes/no/unknown)",
    "CV_Folds": "Number of CV folds",
    "Train_Test_Split": "Train-Test Split ratio",
    "Hyperparam_Tuning": "Hyperparameter Tuning method",
    "Human_in_Loop": "Human in the loop? (1/0)",
    "Open_Source": "Open Source? (1/0)",
    "Accuracy": "Accuracy (0.00-1.00)",
    "F1_Score_Min": "Min F1 Score",
    "F1_Score_Max": "Max F1 Score",
    "F1_Score_Macro": "Macro F1 Score",
    "F1_Score_Weighted": "Weighted F1 Score",
    "Hierarch_Metric": "Hierarchical Metric used? (1/0)",
    "Evidence_Quote": "Brief quote validating the row's data"
}

# ==========================================
# --- 系统提示词 (System Prompt) ---
# ==========================================
SYSTEM_PROMPT = """
Role: You are an expert in natural language processing (NLP) and feature extraction.
Context: The aim of my study is to understand which and how study features relate to the performance of NLP models, using a meta-regression. The NLP models have been trained to classify occupation, industry, product, education level, or disease from text.
Task: Your task is to extract information from the provided PDF scientific journal paper. Extract data for EVERY individual trial/experiment reported.

Strict Extraction Rules:
1. Original Terminology First: Do NOT force methods into predefined categories. Use exact terms.
2. No Hallucinations: If a feature is not explicitly mentioned, output "Unknown" or "Not Reported".
3. Qualitative Fallback: If exact numeric value is missing, provide a qualitative summary.
4. Mandatory Evidence: Every extracted row MUST contain a brief quote/page reference in the 'Evidence_Quote' field.

Data Keys to Extract (You must use exactly these keys):
"First_Author", "Pub_Year", "Domain", "Class_System", "Taxonomy_Structure", "Task_Type", "Num_Classes", "Data_Source", "Language", "Sample_Size", "Avg_Text_Length", "Imbalance_Ratio", "Oversampling", "Undersampling", "Class_Weights", "Trial", "NLP_Model", "Feature_Extraction", "Feature_Selection", "Model_Approach", "Train_Paradigm", "CV_Applied", "CV_Folds", "Train_Test_Split", "Hyperparam_Tuning", "Human_in_Loop", "Open_Source", "Accuracy", "F1_Score_Min", "F1_Score_Max", "F1_Score_Macro", "F1_Score_Weighted", "Hierarch_Metric", "Evidence_Quote"

Output Requirements:
You MUST return a valid JSON object with a single key "trials", which contains an array of objects. Each object represents ONE trial/experiment.
Example:
{
  "trials": [
    {
      "Trial": "1",
      "NLP_Model": "BERT",
      "F1_Score_Macro": "0.75",
      "Evidence_Quote": "Table 2 (Page 8), BERT achieved a macro F1 of 0.75...",
      ... (include all other keys)
    }
  ]
}
"""

def load_or_create_excel():
    if os.path.exists(FILE_PATH):
        return pd.read_excel(FILE_PATH)
    return pd.DataFrame(columns=["Study_ID"] + list(COLUMNS_DICT.keys()))

def get_next_study_num(df):
    if df.empty or "Study_ID" not in df.columns:
        return 1
    ids = df["Study_ID"].astype(str).tolist()
    nums = [int(m.group(1)) for i in ids if (m := re.search(r"Study_(\d+)_", i))]
    return max(nums) + 1 if nums else 1

def extract_from_pdf_with_gemini(pdf_full_path):
    """上传 PDF 至 Gemini 并提取 JSON 数据"""
    print(f"\n⏳ 正在上传 PDF 至云端: {os.path.basename(pdf_full_path)} ...")
    
    uploaded_file = None
    try:
        # 上传文件
        uploaded_file = genai.upload_file(path=pdf_full_path, display_name=os.path.basename(pdf_full_path))
        
        # 轮询检查文件是否处理完毕 (对于较大 PDF，Google 需要几秒钟预处理)
        while uploaded_file.state.name == "PROCESSING":
            print("   Google 云端正在解析 PDF，请稍候...")
            time.sleep(3)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            print("❌ 文件解析失败。")
            return []

        print("🧠 PDF 预处理完成，正在执行高精度信息提取任务 (约需 10-30 秒)...")
        
        # 配置模型，强制要求返回 JSON 格式 (MIME Type 极为关键)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            system_instruction=SYSTEM_PROMPT,
            generation_config={"response_mime_type": "application/json", "temperature": 0.1}
        )
        
        # 发起多模态请求
        response = model.generate_content(
            [uploaded_file, "请仔细阅读该文献，并严格按照系统提示词的 JSON 格式要求，提取所有实验的对比数据。"]
        )
        
        # 解析返回的 JSON
        data = json.loads(response.text)
        return data.get("trials", [])
        
    except Exception as e:
        print(f"❌ Gemini 请求或解析出错: {e}")
        return []
        
    finally:
        # 无论成功失败，必须清理云端文件保护隐私，保持空间整洁
        if uploaded_file:
            genai.delete_file(uploaded_file.name)
            print("🧹 已自动销毁云端临时 PDF 文件，保护数据安全。")

def collect_data(study_id, doi, llm_trial_info):
    """交互式数据采集：人工审核大模型提取的结果"""
    new_data = {"Study_ID": study_id, "DOI": doi}
    
    print(f"\n{'-'*40}")
    print(f"✅ 正在核对子实验 (Trial): {study_id}")
    if llm_trial_info:
        evidence = llm_trial_info.get("Evidence_Quote", "未提供")
        print(f"📖 模型定位依据 (Evidence): \n   {evidence}")
    print(f"{'-'*40}")
    
    for col, prompt_desc in COLUMNS_DICT.items():
        if col in ["Study_ID", "DOI"]: continue
        
        suggestion = llm_trial_info.get(col, "")
        
        if suggestion and str(suggestion).strip() not in ["", "None", "null"]:
            user_input = input(f"[{col}] (AI建议: {suggestion})\n   👉 回车确认, 或输入修改值: ").strip()
            new_data[col] = user_input if user_input else suggestion
        else:
            user_input = input(f"[{col}] {prompt_desc}: ").strip()
            new_data[col] = user_input if user_input else "NA"
            
    return new_data

def save_to_excel(new_row_dict):
    df = load_or_create_excel()
    new_row_df = pd.DataFrame([new_row_dict])
    df = pd.concat([df, new_row_df], ignore_index=True)
    try:
        df.to_excel(FILE_PATH, index=False)
        print(f"💾 数据已成功存入: {FILE_PATH} (目前总数据条数: {len(df)})")
    except PermissionError:
        print("❌ 错误：Excel 文件被占用，请关闭 Excel 表格后程序会自动重试...")
        input("关闭后请按回车键继续...")
        df.to_excel(FILE_PATH, index=False)

def main_flow():
    print("="*60)
    print(" 🚀 NLP Meta-Analysis 智能提取助手 (Powered by Gemini 1.5 Pro) ")
    print("="*60)
    
    df = load_or_create_excel()
    current_study_num = get_next_study_num(df)

    while True:
        print(f"\n>>> 准备处理 第 {current_study_num:03d} 篇 文献 <<<")
        
        pdf_filename = input(f"📁 请输入位于 data/raw_pdfs 下的 PDF 文件名 (例如 'paper1.pdf', 输入 'q' 退出): ").strip()
        
        if pdf_filename.lower() == 'q':
            print("👋 数据处理完成，结果已保存！你可以去运行 06_meta_analysis.qmd 了。")
            break
            
        pdf_full_path = os.path.join(PDF_DIR, pdf_filename)
        
        if not os.path.exists(pdf_full_path):
            print(f"❌ 找不到文件: {pdf_full_path}。请检查文件名是否拼写正确。")
            continue
            
        doi = input("🔍 请输入这篇文献的 DOI (选填，直接回车跳过): ").strip()

        # 核心：调用大模型解析 PDF
        trials_data = extract_from_pdf_with_gemini(pdf_full_path)
        
        if trials_data:
            print(f"\n🎉 极其顺利！AI 成功识别出本文包含 {len(trials_data)} 个模型表现实验 (Trials)。")
            print("👇 接下来，请进行人工核对...")
        else:
            print("\n⚠️ AI 未能提取到有效的实验数据，将切换至纯人工输入模式。")
            trials_data = [{}]

        # 循环让用户逐条核实提取到的 Trial
        for sub_index, llm_trial in enumerate(trials_data):
            suffix = chr(ord('a') + sub_index)
            formatted_id = f"Study_{current_study_num:03d}_{suffix}"
            
            entry_data = collect_data(formatted_id, doi if doi else "NA", llm_trial)
            save_to_excel(entry_data)
        
        # ⚠️ 针对 Gemini 免费版 Rate Limit (2 Requests Per Minute) 的防御机制
        print("\n⏳ 正在冷却 API 额度中 (免费版限制)... 休息 30 秒...")
        for i in range(30, 0, -5):
            print(f"   距离下一次请求还有 {i} 秒")
            time.sleep(5)
            
        current_study_num += 1

if __name__ == "__main__":
    main_flow()
