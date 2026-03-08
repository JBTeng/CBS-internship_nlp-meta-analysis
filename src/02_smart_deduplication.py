import rispy
import pandas as pd
from rapidfuzz import fuzz
import os
import numpy as np

# ================= Configuration / 配置 =================
# Input file (Result from script 01) / 输入文件（脚本 01 的结果）
input_file = os.path.join(os.path.dirname(__file__), '../data/intermediate/01_preliminary_merged.ris')
# Final Output file for ASReview / 最终输出给 ASReview 的文件
output_file = os.path.join(os.path.dirname(__file__), '../data/intermediate/02_SMART_DEDUPLICATED_FINAL.ris')

print(f"🚀 Starting Deduplication / 开始去重: {os.path.basename(input_file)}...")

# 1. Load Data / 加载数据
if not os.path.exists(input_file):
    print(f"❌ Error: File not found / 错误：找不到文件 {input_file}")
    exit()

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        entries = rispy.load(f)
    df = pd.DataFrame(entries)
    print(f"📊 Initial Count / 初始记录数: {len(df)}")
except Exception as e:
    print(f"❌ Read Failed / 读取失败: {e}")
    exit()

# 2. Standardization / 标准化处理
required_cols = ['title', 'abstract', 'doi', 'year', 'type_of_reference', 'authors']
for col in required_cols:
    if col not in df.columns:
        df[col] = None 

# Normalize Title / 归一化标题
df['title_norm'] = df['title'].fillna('').astype(str).str.lower().str.replace(r'[^a-z0-9]', '', regex=True)

# Normalize DOI / 归一化 DOI
df['doi_norm'] = df['doi'].fillna('').astype(str).str.lower().str.strip()

# Calculate Abstract Length (Key Metric) / 计算摘要长度 (核心指标)
df['abstract_len'] = df['abstract'].fillna('').astype(str).apply(len)

# Initialize Group ID / 初始化重复组ID
df['dup_id'] = -1 
next_group_id = 0

# 3. Deduplication Logic / 智能去重逻辑

# A. Exact Match by DOI / DOI 精确匹配
print("🔍 Step 1: Matching by DOI / 第一步：DOI 精确匹配....")
mask_doi = (df['doi_norm'].str.len() > 5)
if mask_doi.any():
    doi_dupes = df[mask_doi].groupby('doi_norm').filter(lambda x: len(x) > 1)
    for doi, group in doi_dupes.groupby('doi_norm'):
        indices = group.index.tolist()
        df.loc[indices, 'dup_id'] = next_group_id
        next_group_id += 1

# B. Exact Match by Normalized Title / 标题精确匹配
print("🔍 Step 2: Matching by Normalized Title / 第二步：标题精确匹配...")
mask_ungrouped = (df['dup_id'] == -1) & (df['title_norm'].str.len() > 10)
if mask_ungrouped.any():
    title_dupes = df[mask_ungrouped].groupby('title_norm').filter(lambda x: len(x) > 1)
    for title, group in title_dupes.groupby('title_norm'):
        indices = group.index.tolist()
        df.loc[indices, 'dup_id'] = next_group_id
        next_group_id += 1

# C. Fuzzy Match by Title / 标题模糊匹配
print("🔍 Step 3: Fuzzy Matching / 第三步：模糊匹配...")
candidate_indices = df[df['dup_id'] == -1].index.tolist()
count = 0

for i in range(len(candidate_indices)):
    idx_i = candidate_indices[i]
    title_i = df.loc[idx_i, 'title_norm']
    
    if len(title_i) < 10: continue 

    # Look ahead window of 50 / 向后查看 50 个候选
    for j in range(i + 1, min(i + 50, len(candidate_indices))):
        idx_j = candidate_indices[j]
        if df.loc[idx_j, 'dup_id'] != -1: continue

        title_j = df.loc[idx_j, 'title_norm']
        if abs(len(title_i) - len(title_j)) > 20: continue # Length check / 长度检查

        if fuzz.ratio(title_i, title_j) > 95:
            current_group = df.loc[idx_i, 'dup_id']
            if current_group == -1:
                current_group = next_group_id
                next_group_id += 1
                df.loc[idx_i, 'dup_id'] = current_group
            
            df.loc[idx_j, 'dup_id'] = current_group
            count += 1

print(f"   ℹ️ Found {count} fuzzy matches / 发现 {count} 个模糊匹配")

# 4. Survival of the Fittest (Completeness First) / 优胜劣汰 (完整性优先)
print("⚔️ Selection: Keeping the most complete records / 筛选：保留最完整的记录...")
final_indices = []

# Sort criteria: 
# 1. Abstract Length (Longer is better) / 摘要长度 (越长越好)
# 2. Year (Newer is better) / 年份 (越新越好)
sort_cols = ['abstract_len', 'year']
ascending_order = [False, False] 

# Assign ID to unique records / 为独立记录分配 ID
df.loc[df['dup_id'] == -1, 'dup_id'] = range(next_group_id, next_group_id + len(df[df['dup_id'] == -1]))

for gid, group in df.groupby('dup_id'):
    if len(group) == 1:
        final_indices.append(group.index[0])
    else:
        # Sort and pick the top one / 排序并选取第一条
        best_record_idx = group.sort_values(by=sort_cols, ascending=ascending_order).index[0]
        final_indices.append(best_record_idx)

df_final = df.loc[final_indices].copy()

# 5. Final Export / 最终导出
removed_count = len(df) - len(df_final)
print(f"\n📉 Result: Reduced from {len(df)} to {len(df_final)} records.")
print(f"📉 结果: 从 {len(df)} 条减少到 {len(df_final)} 条 (Removed {removed_count} duplicates)")

def clean_text(text):
    if pd.isna(text) or text == "" or str(text).lower() == 'nan': return None
    return str(text).replace('\n', ' ').strip()

print(f"💾 Writing to disk / 写入磁盘: {output_file}...")

with open(output_file, 'w', encoding='utf-8') as f:
    for _, row in df_final.iterrows():
        # Write Original Type (Essential for correct formatting)
        # 写入原始类型 (对正确格式至关重要)
        r_type = row.get('type_of_reference')
        if not r_type or pd.isna(r_type): r_type = 'JOUR' # Fallback only if strictly None / 仅在完全为空时回退
        f.write(f"TY  - {r_type}\n")
        
        if row.get('title'): f.write(f"TI  - {clean_text(row['title'])}\n")
        if row.get('abstract'): f.write(f"AB  - {clean_text(row['abstract'])}\n")
        
        if row.get('authors'):
            auths = row['authors']
            if isinstance(auths, list):
                for au in auths: 
                    clean_au = clean_text(au)
                    if clean_au: f.write(f"AU  - {clean_au}\n")
            elif isinstance(auths, str):
                f.write(f"AU  - {clean_text(auths)}\n")

        if row.get('year'): f.write(f"PY  - {clean_text(row['year'])}\n")
        if row.get('doi'): f.write(f"DO  - {clean_text(row['doi'])}\n")
        
        f.write("ER  - \n\n")

print(f"✅ Final File Generated / 最终文件已生成: {output_file}")
print("🎉 Next Step: Please run 03_audit_missing_data to verify data quality!")
print("🎉 下一步: 请运行 03_audit_missing_data 来验证数据质量！")