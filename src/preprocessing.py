import pandas as pd
import rispy
import glob
import os
import re
import numpy as np
from rapidfuzz import fuzz # 必须安装：pip install rapidfuzz

# ================= 0. 基础路径配置 =================
# 自动定位：无论你在哪运行，脚本都会基于它所在的位置去找 data 文件夹
current_script_dir = os.path.dirname(os.path.abspath(__file__))
raw_dir = os.path.join(current_script_dir, '../data/raw')
output_file = os.path.join(current_script_dir, '../data/processed/smart_deduplicated.ris')

print(f"🚀 脚本启动位置: {current_script_dir}")
print(f"📂 数据读取目录: {os.path.abspath(raw_dir)}")

# ================= 1. 读取并修复数据 (RIS & CSV) =================
ris_files = glob.glob(os.path.join(raw_dir, '*.[rR][iI][sS]'))
ris_entries = []

print(f"\n--- 1. 正在加载原始文献 ---")
# 处理 RIS 文件
for f_path in ris_files:
    try:
        with open(f_path, 'r', encoding='utf-8-sig') as f:
            entries = rispy.load(f)
            source = os.path.basename(f_path)
            for entry in entries:
                entry['custom_source'] = source
                # [关键补丁] 修复 ProQuest 标题和期刊名丢失问题
                if 'title' not in entry or not entry['title']:
                    entry['title'] = entry.get('primary_title', entry.get('secondary_title', ''))
                if 'journal_name' not in entry or not entry['journal_name']:
                    entry['journal_name'] = entry.get('alternate_title3', '')
                if 'authors' not in entry or entry['authors'] is None: 
                    entry['authors'] = []
            ris_entries.extend(entries)
            print(f"  ✅ [RIS] {source}: 读取 {len(entries)} 条")
    except Exception as e:
        print(f"  ❌ [RIS] 无法读取 {os.path.basename(f_path)}: {e}")

df_ris = pd.DataFrame(ris_entries)

# 处理 OpenAlex CSV 文件
csv_path = os.path.join(raw_dir, 'openalex.csv')
if os.path.exists(csv_path):
    try:
        df_csv = pd.read_csv(csv_path)
        # OpenAlex 专属列名映射
        mapping = {
            'doi': 'doi', 
            'display_name': 'title', 
            'publication_year': 'year', 
            'host_venue.display_name': 'journal_name', 
            'ab_original': 'abstract'
        }
        actual_mapping = {k: v for k, v in mapping.items() if k in df_csv.columns}
        df_csv_final = df_csv.rename(columns=actual_mapping)
        cols = [c for c in df_csv_final.columns if c in mapping.values()]
        df_csv_final = df_csv_final[cols].copy()
        df_csv_final['custom_source'] = 'openalex.csv'
        print(f"  ✅ [CSV] openalex.csv: 读取 {len(df_csv_final)} 条")
        df_total = pd.concat([df_ris, df_csv_final], ignore_index=True)
    except Exception as e:
        print(f"  ❌ [CSV] 无法读取 CSV: {e}")
        df_total = df_ris
else:
    df_total = df_ris
    print("  ⚠️ 未发现 openalex.csv")

print(f"📊 初始合并总数: {len(df_total)} 条")

# ================= 2. 数据清洗与标准化 =================
print(f"\n--- 2. 正在进行标准化清洗 ---")

# 填充基础空值
for col in ['title', 'doi', 'journal_name', 'abstract']:
    if col in df_total.columns:
        df_total[col] = df_total[col].fillna('')

# 年份正则提取 (处理 "Dec 2025" -> "2025")
def extract_year(val):
    if pd.isna(val) or not str(val): return '0000'
    match = re.search(r'\d{4}', str(val))
    return match.group(0) if match else '0000'
df_total['clean_year'] = df_total['year'].apply(extract_year)

# 标题标准化 (去符号、小写)
df_total['title_norm'] = df_total['title'].astype(str).str.lower().str.replace(r'[^a-z0-9\s]', '', regex=True).str.strip()
# DOI 标准化
df_total['doi_norm'] = df_total['doi'].astype(str).str.lower().str.strip().str.replace('https://doi.org/', '').replace('nan', '')
# 作者首姓提取
def get_first_auth(val):
    if isinstance(val, list) and len(val) > 0: return str(val[0]).split(',')[0].strip().lower()
    if isinstance(val, str) and val: return val.split(',')[0].strip().lower()
    return ""
df_total['auth_norm'] = df_total['authors'].apply(get_first_auth)

# 垃圾内容初步过滤
junk_keywords = ['table of contents', 'book review', 'front matter', 'back matter', 'editorial board']
mask_junk = df_total['title_norm'].apply(lambda x: any(k in x for k in junk_keywords))
df_total = df_total[~mask_junk].copy()
print(f"  🗑️ 已自动剔除标题中包含 Book Review 等关键词的条目: {mask_junk.sum()} 条")

# ================= 3. 智能去重逻辑 =================
print(f"\n--- 3. 正在执行智能匹配 (DOI + 标题 + 作者) ---")

df_total['dup_group_id'] = -1 
group_counter = 0

# A. 基于 DOI 的硬匹配
mask_has_doi = df_total['doi_norm'] != ''
for doi, group in df_total[mask_has_doi].groupby('doi_norm'):
    if len(group) > 1:
        df_total.loc[group.index, 'dup_group_id'] = group_counter
        group_counter += 1

# B. 基于 标题+年份+作者 的软匹配
years = df_total['clean_year'].unique()
for year in years:
    if year == '0000': continue
    year_indices = df_total[df_total['clean_year'] == year].index.tolist()
    if len(year_indices) < 2: continue
    
    # 获取当年记录
    year_recs = df_total.loc[year_indices].to_dict('records')
    for i in range(len(year_recs)):
        idx_i = year_indices[i]
        gid_i = df_total.loc[idx_i, 'dup_group_id']
        
        for j in range(i + 1, len(year_recs)):
            idx_j = year_indices[j]
            gid_j = df_total.loc[idx_j, 'dup_group_id']
            if gid_i != -1 and gid_i == gid_j: continue # 已在同一组
                
            rec_i, rec_j = year_recs[i], year_recs[j]
            # 计算相似度
            t_sim = fuzz.token_set_ratio(rec_i['title_norm'], rec_j['title_norm'])
            a_match = (rec_i['auth_norm'][:4] == rec_j['auth_norm'][:4]) if rec_i['auth_norm'] and rec_j['auth_norm'] else True
            
            # 判定重复：标题极度相似，或标题较相似且作者一致
            if t_sim > 96 or (t_sim > 88 and a_match):
                if gid_i == -1 and gid_j == -1:
                    df_total.loc[[idx_i, idx_j], 'dup_group_id'] = group_counter
                    gid_i = group_counter
                    group_counter += 1
                elif gid_i != -1 and gid_j == -1: df_total.loc[idx_j, 'dup_group_id'] = gid_i
                elif gid_i == -1 and gid_j != -1: df_total.loc[idx_i, 'dup_group_id'] = gid_j; gid_i = gid_j
                else: df_total.loc[df_total['dup_group_id'] == gid_j, 'dup_group_id'] = gid_i

# ================= 4. 详细日志合并 (增强打印) =================
print(f"\n--- 4. 正在详细审查并合并重复组 ---")
indices_to_drop = []
grouped = df_total[df_total['dup_group_id'] != -1].groupby('dup_group_id')

for gid, group in grouped:
    # 择优标准：有DOI优先，有摘要优先，标题长的优先
    group['has_doi'] = group['doi_norm'] != ''
    group['has_abs'] = group['abstract'] != ''
    group['title_len'] = group['title'].str.len()
    sorted_group = group.sort_values(by=['has_doi', 'has_abs', 'title_len'], ascending=[False, False, False])
    
    keep_idx = sorted_group.index[0]
    drop_indices = sorted_group.index[1:]
    
    # 【打印详细去重日志】
    print(f"  [组 {gid}] 发现 {len(group)} 个重复。")
    print(f"     ✅ 保留: {sorted_group.loc[keep_idx, 'custom_source']} | {str(sorted_group.loc[keep_idx, 'title'])[:60]}...")
    for d_idx in drop_indices:
        print(f"     ❌ 丢弃: {sorted_group.loc[d_idx, 'custom_source']}")
    
    indices_to_drop.extend(drop_indices)

df_final = df_total.drop(index=indices_to_drop).copy()

# ================= 5. 标准化类型并导出 =================
# 清理辅助列，特别是 unknown_tag，防止报错
cols_to_drop = [
    'clean_year', 'auth_norm', 'title_norm', 'doi_norm', 'dup_group_id', 
    'unknown_tag', 'id', 'custom_source', 
    'primary_title', 'secondary_title', 'alternate_title3'
]
output_df = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns], errors='ignore')
output_df = output_df.fillna('')

# 修复作者为 list 格式
def fix_auth(val):
    if isinstance(val, list): return [str(v) for v in val]
    return [str(val)] if (isinstance(val, str) and val.strip()) else []
if 'authors' in output_df.columns:
    output_df['authors'] = output_df['authors'].apply(fix_auth)

# 统一类型
output_df['type_of_reference'] = output_df.get('type_of_reference', 'JOUR')
output_df['type_of_reference'] = output_df['type_of_reference'].replace({'Scholarly Journals': 'JOUR'}).fillna('JOUR')

# 保存
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    rispy.dump(output_df.to_dict('records'), f)

print(f"\n✨ 完工！")
print(f"📊 统计: 原始 {len(df_total)} 条 -> 去重后 {len(df_final)} 条 (共删除了 {len(indices_to_drop)} 条重复)")
print(f"💾 最终文件已保存至: {output_file}")