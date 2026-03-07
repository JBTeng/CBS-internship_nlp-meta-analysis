import rispy
import pandas as pd
import os

# ================= 配置 =================
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 输入：最终去重后的文件
input_file = os.path.join(current_script_dir, '../data/processed/02_SMART_DEDUPLICATED_FINAL.ris')

# 输出：仅包含有问题记录的小文件 (方便你修补)
output_ris = os.path.join(current_script_dir, '../data/processed/03_incomplete_records_for_manual_fix.ris')

print(f"🚀 正在检查文件: {os.path.basename(input_file)} ...\n")

# 1. 加载数据
if not os.path.exists(input_file):
    print(f"❌ 错误：找不到文件 {input_file}")
    exit()

try:
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        entries = rispy.loads(f.read())
    df = pd.DataFrame(entries)
except Exception as e:
    print(f"❌ 读取失败: {e}")
    exit()

# 2. 扫描缺失数据
missing_log = []
indices_to_fix = []

print(f"{'='*80}")
print(f"{'MISSING':<15} | {'TITLE (First 80 chars)':<60}")
print(f"{'-'*80}")

for idx, row in df.iterrows():
    missing_cols = []
    
    # 检查摘要 (Abstract)
    # 标准：必须存在，不是NaN，且长度大于10（过滤掉空字符串）
    abstract = str(row.get('abstract', ''))
    if pd.isna(row.get('abstract')) or abstract.strip() == "" or len(abstract) < 5:
        missing_cols.append("Abstract")
        
    # 检查 DOI
    doi = str(row.get('doi', ''))
    if pd.isna(row.get('doi')) or doi.strip() == "":
        missing_cols.append("DOI")
        
    # 如果有缺失，打印出来
    if missing_cols:
        indices_to_fix.append(idx)
        
        # 安全获取标题
        raw_title = row.get('title')
        if pd.isna(raw_title):
            title_display = "[NO TITLE FOUND]"
        else:
            title_display = str(raw_title).strip()[:80] # 只显示前80个字符

        missing_str = " & ".join(missing_cols)
        
        # 🔥 直接在终端打印
        print(f"{missing_str:<15} | {title_display}")
        
        missing_log.append(idx)

print(f"{'='*80}\n")

# 3. 总结与生成待修补文件

if not missing_log:
    print("✅ 完美！所有记录都有摘要和 DOI。你可以直接进 ASReview 了！")
    # 如果以前有旧的待修补文件，删掉它以免混淆
    if os.path.exists(output_ris): os.remove(output_ris)
else:
    print(f"⚠️  共发现 {len(missing_log)} 条记录有缺失。")
    
    # 生成 RIS 子集
    def clean_text(text):
        if pd.isna(text) or text == "" or str(text).lower() == 'nan': return None
        return str(text).replace('\n', ' ').strip()

    subset_df = df.loc[indices_to_fix]

    with open(output_ris, 'w', encoding='utf-8') as f:
        for _, row in subset_df.iterrows():
            f.write("TY  - JOUR\n")
            t = clean_text(row.get('title'))
            if t: f.write(f"TI  - {t}\n")
            a = clean_text(row.get('abstract'))
            if a: f.write(f"AB  - {a}\n")
            y = clean_text(row.get('year'))
            if y: f.write(f"PY  - {y}\n")
            d = clean_text(row.get('doi'))
            if d: f.write(f"DO  - {d}\n")
            auths = row.get('authors')
            if isinstance(auths, list):
                for au in auths: f.write(f"AU  - {clean_text(au)}\n")
            elif pd.notna(auths) and auths != "":
                f.write(f"AU  - {clean_text(auths)}\n")
            f.write("ER  - \n\n")

    print(f"💾 已生成待修补文件: {os.path.basename(output_ris)}")
    print(f"👉 操作建议：打开 'records_to_fix.ris'，手动填补缺失信息，然后保存。")