import pandas as pd
import os
import re
import time
import json_repair
# 导入全新的官方 SDK
from google import genai
from google.genai import types

# ==========================================
# --- 核心路径配置 ---
# ==========================================
current_script_dir = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.normpath(os.path.join(current_script_dir, '../data/processed/05_Data_Extraction_for_R.xlsx'))
PDF_DIR = os.path.normpath(os.path.join(current_script_dir, '../data/raw_pdfs'))

os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# ==========================================
# --- 🔑 Gemini API 配置 ---
# ==========================================
# replace your API Key from  Google AI Studio 
API_KEY = "YOUR_GEMINI_API_KEY"
client = genai.Client(api_key=API_KEY)

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
# --- 魔法区域：动态构建强制 JSON Schema ---
# 这会让 AI 彻底失去“乱改格式”和“漏掉字段”的自由
# ==========================================
schema_properties = {}
for key, desc in COLUMNS_DICT.items():
    if key in ["Study_ID", "DOI"]: continue
    schema_properties[key] = types.Schema(
        type=types.Type.STRING,
        description=desc
    )

# 构建一个铁壳子，强制要求所有的 Key 必须全部输出
RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "trials": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties=schema_properties,
                required=list(schema_properties.keys()) # 核心：强制要求所有字段一个都不能少！
            )
        )
    },
    required=["trials"]
)

# ==========================================
# --- 系统提示词 (System Prompt) ---
# ==========================================
SYSTEM_PROMPT = """
Role: You are an expert in natural language processing (NLP) and feature extraction.
Context: The aim of my study is to understand which and how study features relate to the performance of NLP models, using a meta-regression.
Task: Your task is to extract information from the provided PDF scientific journal paper. Extract data for EVERY individual trial/experiment reported.

Strict Extraction Rules:
1. Original Terminology First: Do NOT force methods into predefined categories. Use exact terms.
2. No Hallucinations: If a feature is not explicitly mentioned, output "Unknown" or "Not Reported". Do NOT leave it blank.
3. Qualitative Fallback: If exact numeric value is missing, provide a qualitative summary.
4. Mandatory Location Evidence: Instead of long quotes, you MUST provide the EXACT location for every trial.
Format: "Page X, Section Y, [Table/Figure Z if applicable]".
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
    print(f"\n⏳ 正在上传 PDF 至云端: {os.path.basename(pdf_full_path)} ...")
    uploaded_file = None
    try:
        uploaded_file = client.files.upload(file=pdf_full_path)
        print("☁️ Google 云端正在解析 PDF，请稍候...")
        while True:
            file_info = client.files.get(name=uploaded_file.name)
            if file_info.state.name == "ACTIVE":
                break
            elif file_info.state.name == "FAILED":
                print("❌ 文件解析失败。")
                return []
            time.sleep(3)

        print("🧠 PDF 预处理完成，正在执行高精度信息提取任务 (约需 15-30 秒)...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, "请提取所有实验的对比数据。"],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA, # <--- 启用强制 Schema 绑定
                temperature=0.1,
                max_output_tokens=8192  # <--- 新增这一行，把输出上限拉到最高
            )
        )
        
        # 解析返回的数据
        data = json_repair.loads(response.text)
        if isinstance(data, dict) and "trials" in data:
            return data["trials"]
        elif isinstance(data, list):
            return data
        return []
    except Exception as e:
        print(f"❌ Gemini 请求出错: {e}")
        return []
    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

def format_trial_data(study_id, doi, llm_trial_info):
    """因为有了 Schema 的强力保障，我们现在可以放心地直接取值"""
    new_data = {"Study_ID": study_id, "DOI": doi if doi else "NA"}
    
    if not isinstance(llm_trial_info, dict):
        return new_data

    for col in COLUMNS_DICT.keys():
        if col in ["Study_ID", "DOI"]: continue
        
        val = str(llm_trial_info.get(col, "NA")).strip()
        if val in ["", "None", "null", "[]", "{}"]:
            val = "NA"
            
        new_data[col] = val
        
    return new_data

def save_to_excel(df, new_row_dict):
    new_row_df = pd.DataFrame([new_row_dict])
    df = pd.concat([df, new_row_df], ignore_index=True)
    try:
        df.to_excel(FILE_PATH, index=False)
    except PermissionError:
        print("\n❌ 错误：Excel 文件被占用！请在 Excel 中保存并关闭文件，然后按回车键重试...")
        input("关闭后请按回车键继续...")
        df.to_excel(FILE_PATH, index=False)
    return df

def main_flow():
    print("="*60)
    print(" 🚀 NLP Meta-Analysis 强校验全自动提取 (Powered by Gemini Schema) ")
    print("="*60)
    df = load_or_create_excel()
    current_study_num = get_next_study_num(df)

    while True:
        print(f"\n>>> 准备处理 第 {current_study_num:03d} 篇 文献 <<<")
        pdf_filename = input(f"📁 请输入 PDF 文件名 (输入 'q' 退出): ").strip()
        
        if pdf_filename.lower() == 'q':
            break
            
        pdf_full_path = os.path.join(PDF_DIR, pdf_filename)
        if not os.path.exists(pdf_full_path):
            print(f"❌ 找不到文件: {pdf_full_path}")
            continue
            
        doi = input("🔍 请输入这篇文献的 DOI (直接回车跳过): ").strip()

        trials_data = extract_from_pdf_with_gemini(pdf_full_path)
        
        if trials_data:
            print(f"\n🎉 极其顺利！AI 提取出 {len(trials_data)} 个实验数据。正在写入 Excel...")
            for sub_index, llm_trial in enumerate(trials_data):
                suffix = chr(ord('a') + sub_index)
                formatted_id = f"Study_{current_study_num:03d}_{suffix}"
                entry_data = format_trial_data(formatted_id, doi, llm_trial)
                df = save_to_excel(df, entry_data)
                
            print("✅ 写入完成！字段已全部锁定对齐，请前往 Excel 查阅。")
        else:
            print("\n⚠️ 未能提取到有效的实验数据。")

        print("\n⏳ 正在冷却 API... 休息 30 秒...")
        for i in range(30, 0, -5):
            print(f" 距离下一次请求还有 {i} 秒")
            time.sleep(5)
            
        current_study_num += 1

if __name__ == "__main__":
    main_flow()
