import rispy
import pandas as pd
import os

# ================= Configuration / 配置 =================
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# Input: Final deduplicated file / 输入：最终去重后的文件
input_file = os.path.join(current_script_dir, '../data/intermediate/02_SMART_DEDUPLICATED_FINAL.ris')

# Output: Small file for manual fix / 输出：用于手动修复的小文件
output_ris = os.path.join(current_script_dir, '../data/intermediate/03_incomplete_records_for_manual_fix.ris')

print(f"🚀 Checking file / 正在检查文件: {os.path.basename(input_file)} ...\n")

# 1. Load Data / 加载数据
if not os.path.exists(input_file):
    print(f"❌ Error: File not found / 错误：找不到文件 {input_file}")
    exit()

try:
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        entries = rispy.loads(f.read())
    df = pd.DataFrame(entries)
    print(f"📊 Total records loaded / 已加载总记录: {len(df)}")
except Exception as e:
    print(f"❌ Read Failed / 读取失败: {e}")
    exit()

# 2. Scan & Export Logic / 扫描与导出逻辑
indices_to_fix = []
missing_count = 0

print(f"{'='*100}")
print(f"{'ID':<5} | {'MISSING FIELD / 缺失字段':<25} | {'TYPE':<6} | {'TITLE / 标题预览'}")
print(f"{'-'*100}")

# Helper to check validity / 检查有效性的辅助函数
def is_valid(text, min_len=3):
    if pd.isna(text) or text is None: return False
    s = str(text).strip().lower()
    if s in ["", "nan", "none", "null"]: return False
    if len(s) < min_len: return False
    return True

# Prepare to write immediately / 准备立即写入
# We iterate first to find them, then write to file / 我们先遍历查找，然后写入文件

records_to_write = []

for idx, row in df.iterrows():
    missing_cols = []
    
    has_title = is_valid(row.get('title'), 3)
    has_abstract = is_valid(row.get('abstract'), 5)
    has_doi = is_valid(row.get('doi'), 3)
    
    if not has_title: missing_cols.append("Title")
    if not has_abstract: missing_cols.append("Abstract")
    # DOI is optional but good to check / DOI 是可选的但最好检查一下
    if not has_doi: missing_cols.append("DOI")

    # If anything is missing, add to fix list / 如果有缺失，加入修复列表
    if missing_cols:
        indices_to_fix.append(idx)
        records_to_write.append((idx, row, has_title, has_abstract, has_doi))
        
        # Log to terminal / 终端打印日志
        title_display = str(row.get('title', ''))[:40] if has_title else "[NO TITLE]"
        r_type = str(row.get('type_of_reference', 'GEN'))
        
        print(f"{idx:<5} | {' & '.join(missing_cols):<25} | {r_type:<6} | {title_display}")
        missing_count += 1

print(f"{'='*100}\n")

if missing_count == 0:
    print("✅ Perfect! No missing data found.")
    exit()

print(f"⚠️  Found {missing_count} records to fix. / 发现 {missing_count} 条记录需要修复。")
print(f"💾 Generating patch file with placeholders... / 正在生成带占位符的补丁文件...")

def clean_text(text):
    if pd.isna(text) or text == "" or str(text).lower() in ['nan', 'none']: return ""
    return str(text).replace('\n', ' ').strip()

with open(output_ris, 'w', encoding='utf-8') as f:
    for idx, row, has_title, has_abstract, has_doi in records_to_write:
        # 1. Type (Preserve Original) / 类型 (保留原始)
        t = row.get('type_of_reference')
        if not t or pd.isna(t): t = 'JOUR'
        f.write(f"TY  - {t}\n")
        
        # 2. Title / 标题
        if has_title:
            f.write(f"TI  - {clean_text(row.get('title'))}\n")
        else:
            # 🔥 Placeholder / 占位符
            f.write(f"TI  - [MISSING TITLE - PLEASE MANUALLY ADD HERE]\n")

        # 3. Abstract / 摘要
        if has_abstract:
            f.write(f"AB  - {clean_text(row.get('abstract'))}\n")
        else:
            # 🔥 Placeholder / 占位符
            f.write(f"AB  - [MISSING ABSTRACT - PLEASE MANUALLY ADD HERE]\n")

        # 4. DOI / DOI
        if has_doi:
            f.write(f"DO  - {clean_text(row.get('doi'))}\n")
        else:
            # 🔥 Placeholder / 占位符 (DOI isn't strictly required for ASReview, but good to have)
            f.write(f"DO  - [MISSING DOI - PLEASE ADD IF AVAILABLE]\n")

        # 5. Year & Authors (Write existing ones) / 年份和作者 (写入已有的)
        y = clean_text(row.get('year'))
        if y: f.write(f"PY  - {y}\n")
        
        auths = row.get('authors')
        if isinstance(auths, list):
            for au in auths: f.write(f"AU  - {clean_text(au)}\n")
        elif pd.notna(auths):
            f.write(f"AU  - {clean_text(auths)}\n")

        # 6. CRITICAL: The Original ID / 关键：原始 ID
        f.write(f"N1  - Original_ID:{idx}\n")
        
        f.write("ER  - \n\n")
        
# ================= 3. INSTRUCTIONS FOR USER / 用户操作指南 =================

print(f"\n✅ Raw file generated at: data/intermediate/{os.path.basename(output_ris)}")
print(f"\n{'='*80}")
print(f"🛑 NEXT STEPS (ACTION REQUIRED) / 下一步操作 (必读)")
print(f"{'='*80}")
print(f"1. COPY the file:  data/intermediate/{os.path.basename(output_ris)}")
print(f"2. PASTE it into:  data/processed/")
print(f"3. RENAME it to:   03_manually_updated.ris")
print(f"4. EDIT '03_manually_updated.ris' to fill in the missing info. if you don't have the info, just don't change the [MISSING ...] placeholders. ")
print(f"5. SAVE it.")
print(f"{'-'*80}")
print(f"👉 Once finished, run script 04 to merge it back.")
print(f"👉 完成后，请运行脚本 04 将其合并回去。")
print(f"{'='*80}\n")