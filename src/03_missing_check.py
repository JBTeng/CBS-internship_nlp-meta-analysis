import rispy
import pandas as pd
import os

# ================= Configuration / 配置 =================
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# Input: Final deduplicated file / 输入：最终去重后的文件
input_file = os.path.join(current_script_dir, '../data/processed/02_SMART_DEDUPLICATED_FINAL.ris')

# Output: Small file with incomplete records for manual fix / 输出：仅包含有问题记录的小文件
output_ris = os.path.join(current_script_dir, '../data/processed/03_incomplete_records_for_manual_fix.ris')

print(f"🚀 Checking file / 正在检查文件: {os.path.basename(input_file)} ...\n")

# 1. Load Data / 加载数据
if not os.path.exists(input_file):
    print(f"❌ Error: File not found / 错误：找不到文件 {input_file}")
    exit()

try:
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        entries = rispy.loads(f.read())
    df = pd.DataFrame(entries)
except Exception as e:
    print(f"❌ Read Failed / 读取失败: {e}")
    exit()

# 2. Scan for Missing Data / 扫描缺失数据
missing_log = []
indices_to_fix = []

print(f"{'='*90}")
print(f"{'MISSING FIELD / 缺失字段':<25} | {'TITLE (First 60 chars) / 标题'}")
print(f"{'-'*90}")

for idx, row in df.iterrows():
    missing_cols = []
    
    # [NEW] Check Title / [新增] 检查标题
    # Criteria: Must exist, not be NaN, not 'none', and length > 3
    title = str(row.get('title', ''))
    if pd.isna(row.get('title')) or title.strip().lower() in ["", "nan", "none"] or len(title) < 3:
        missing_cols.append("Title")

    # Check Abstract / 检查摘要
    abstract = str(row.get('abstract', ''))
    if pd.isna(row.get('abstract')) or abstract.strip().lower() in ["", "nan", "none"] or len(abstract) < 5:
        missing_cols.append("Abstract")
        
    # Check DOI / 检查 DOI
    doi = str(row.get('doi', ''))
    if pd.isna(row.get('doi')) or doi.strip().lower() in ["", "nan", "none"]:
        missing_cols.append("DOI")
        
    # If missing found, print and log / 如果有缺失，打印并记录
    if missing_cols:
        indices_to_fix.append(idx)
        
        # Display Title (or placeholder if missing) / 显示标题 (如果缺失则显示占位符)
        if "Title" in missing_cols:
            title_display = "[NO TITLE FOUND / 未找到标题]"
        else:
            title_display = title.strip()[:60]

        missing_str = " & ".join(missing_cols)
        
        # 🔥 Print to terminal / 直接在终端打印
        print(f"{missing_str:<25} | {title_display}")
        
        missing_log.append(idx)

print(f"{'='*90}\n")

# 3. Summary & Export / 总结与生成待修补文件

if not missing_log:
    print("✅ Perfect! All records have Titles, Abstracts, and DOIs.")
else:
    print(f"⚠️  Found {len(missing_log)} incomplete records. / 共发现 {len(missing_log)} 条记录有缺失。")
    
    # Generate RIS Subset / 生成 RIS 子集
    def clean_text(text):
        if pd.isna(text) or text == "" or str(text).lower() in ['nan', 'none']: return None
        return str(text).replace('\n', ' ').strip()

    subset_df = df.loc[indices_to_fix]

    with open(output_ris, 'w', encoding='utf-8') as f:
        for _, row in subset_df.iterrows():
            f.write("TY  - JOUR\n")
            
            # Write Title
            t = clean_text(row.get('title'))
            if t: f.write(f"TI  - {t}\n")
            
            # Write Abstract
            a = clean_text(row.get('abstract'))
            if a: f.write(f"AB  - {a}\n")
            
            # Write Year
            y = clean_text(row.get('year'))
            if y: f.write(f"PY  - {y}\n")
            
            # Write DOI
            d = clean_text(row.get('doi'))
            if d: f.write(f"DO  - {d}\n")
            
            # Write Authors
            auths = row.get('authors')
            if isinstance(auths, list):
                for au in auths: f.write(f"AU  - {clean_text(au)}\n")
            elif pd.notna(auths) and str(auths).lower() not in ["", "nan", "none"]:
                f.write(f"AU  - {clean_text(auths)}\n")
            
            f.write("ER  - \n\n")

    print(f"💾 File generated / 已生成待修补文件: {os.path.basename(output_ris)}")
    print(f"👉 Suggestion: Open this file, fill in the missing Title/Abstract/DOI, and save.")