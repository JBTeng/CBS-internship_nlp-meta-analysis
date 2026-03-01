import rispy
import pandas as pd
from rapidfuzz import fuzz
import os

# ================= Configuration / 配置 =================
# Input file (Result from script 01) / 输入文件（脚本 01 的结果）
input_file = os.path.join(os.path.dirname(__file__), '../data/processed/preliminary_merged_for_asreview.ris')
# Final Output file for ASReview / 最终输出给 ASReview 的文件
output_file = os.path.join(os.path.dirname(__file__), '../data/processed/SMART_DEDUPLICATED_FINAL.ris')

print(f"🚀 Starting Deduplication / 开始去重: {os.path.basename(input_file)}...")

# 1. Load Data / 加载数据
if not os.path.exists(input_file):
    print(f"❌ Error: File not found/错误：找不到文件 {input_file}")
    exit()

try:
    with open(input_file, 'r', encoding='utf-8') as f:
        entries = rispy.load(f)
    df = pd.DataFrame(entries)
    print(f"📊 Initial Count / 初始记录数: {len(df)}")
    print(f"ℹ️ Detected Columns / 检测到的列名: {list(df.columns)}") # 打印列名以便调试
except Exception as e:
    print(f"❌ Read Failed / 读取失败: {e}")
    exit()

# 2. Dynamic Column Mapping/动态映射列名 (修复 KeyError 的核心)
def get_column_name(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None

# auto-detect title, abstract, DOI, year columns/自动寻找标题、摘要、DOI、年份对应的列名
col_title = get_column_name(df, ['title', 'primary_title', 'TI', 'T1'])
col_abstract = get_column_name(df, ['abstract', 'AB', 'N2', 'notes'])
col_doi = get_column_name(df, ['doi', 'DO'])
col_year = get_column_name(df, ['year', 'PY', 'Y1', 'DA'])
col_authors = get_column_name(df, ['authors', 'AU'])

if not col_title:
    print("❌ Fatal Error: No Title Column Found / 致命错误：未找到标题列")
    exit()

print(f"✅ Field Mapping / 字段映射: Title=[{col_title}], Abstract=[{col_abstract}], DOI=[{col_doi}]")

# 3. Prepare Data for Matching / 准备匹配数据
# Normalize Title: lowercase, alphanumeric only / 标题归一化：小写，仅保留字母数字
df['title_norm'] = df[col_title].fillna('').str.lower().str.replace(r'[^a-z0-9]', '', regex=True)

# Normalize DOI / DOI 归一化
if col_doi:
    df['doi_norm'] = df[col_doi].fillna('').str.lower().str.strip()
else:
    df['doi_norm'] = ""

# Calculate Abstract Length (Criteria for selection) / 计算摘要长度（择优标准）
if col_abstract:
    df['abstract_len'] = df[col_abstract].fillna('').astype(str).apply(len)
else:
    df['abstract_len'] = 0

df['dup_id'] = -1 # Initialize Group ID / 初始化重复组ID

# 4. Deduplication Logic / 智能去重逻辑

# A. Exact Match by DOI / 基于 DOI 的精确匹配
print("🔍 Matching by DOI / 正在进行 DOI 匹配....")
mask_doi = (df['doi_norm'] != "") & (df['doi_norm'] != "nan")
if mask_doi.any():
    for doi, group in df[mask_doi].groupby('doi_norm'):
        if len(group) > 1:
            df.loc[group.index, 'dup_id'] = group.index[0]

# B. Fuzzy Match by Title / 基于标题的模糊匹配
print("🔍 Matching by Fuzzy Title / 正在进行标题模糊匹配...")
candidates = df.index.tolist()
for i in range(len(candidates)):
    idx_i = candidates[i]
    if df.loc[idx_i, 'title_norm'] == "": continue

    for j in range(i + 1, len(candidates)):
        idx_j = candidates[j]
        
        # Skip if already grouped / 如果已分组则跳过
        id_i = df.loc[idx_i, 'dup_id']
        id_j = df.loc[idx_j, 'dup_id']
        if id_i != -1 and id_i == id_j:
            continue
            
        # Calculate Similarity / 计算相似度
        t1 = df.loc[idx_i, 'title_norm']
        t2 = df.loc[idx_j, 'title_norm']
        
        # Threshold: 95% / 阈值：95%
        if fuzz.ratio(t1, t2) > 95:
            target_id = id_i if id_i != -1 else idx_i
            df.loc[idx_i, 'dup_id'] = target_id
            df.loc[idx_j, 'dup_id'] = target_id
            
            # Merge groups if needed / 必要时合并组
            if id_j != -1 and id_j != target_id:
                df.loc[df['dup_id'] == id_j, 'dup_id'] = target_id

# 5. Survival of the Fittest/优胜劣汰 
print("⚔️ Selection: Keeping records with abstracts / 筛选：保留有摘要的记录...")
final_indices = []

# Sort criteria: 1. Abstract Length, 2. Year / 排序标准：1. 摘要长度，2. 年份
sort_cols = ['abstract_len']
ascending_order = [False]
if col_year:
    sort_cols.append(col_year)
    ascending_order.append(False)

for gid, group in df.groupby('dup_id'):
    if gid == -1:
        final_indices.extend(group.index.tolist())
    else:
        # Sort by: longer abstracts first, then newer years/排序：优先摘要长的，其次年份新的
        best_idx = group.sort_values(by=sort_cols, ascending=ascending_order).index[0]
        final_indices.append(best_idx)

df_final = df.loc[final_indices].copy()

# 6. Final Export / 最终导出
print(f"\n📉 去重结果: 从 {len(df)} 条减少到 {len(df_final)} 条 ( {len(df)-len(df_final)} duplicates were removed)")
def clean_text(text):
    if pd.isna(text) or text == "" or str(text).lower() == 'nan': return None
    return str(text).replace('\n', ' ').strip()

with open(output_file, 'w', encoding='utf-8') as f:
    for _, row in df_final.iterrows():
        f.write("TY  - JOUR\n")
        
        # 动态使用之前检测到的列名
        if col_title and row.get(col_title): 
            f.write(f"TI  - {clean_text(row[col_title])}\n")
            
        if col_abstract and row.get(col_abstract): 
            f.write(f"AB  - {clean_text(row[col_abstract])}\n")
        
        if col_authors and row.get(col_authors):
            auths = row[col_authors]
            if isinstance(auths, list):
                for au in auths: f.write(f"AU  - {clean_text(au)}\n")
            else:
                f.write(f"AU  - {clean_text(auths)}\n")

        if col_year and row.get(col_year): 
            f.write(f"PY  - {clean_text(row[col_year])}\n")
            
        if col_doi and row.get(col_doi): 
            f.write(f"DO  - {clean_text(row[col_doi])}\n")
            
        f.write(f"N2  - Deduplicated Record\n")
        f.write("ER  - \n\n")

print(f"✅ Final File Generated / 最终文件已生成: {output_file}")
print("🎉 Ready for ASReview! / 可以上传到 ASReview 了！")