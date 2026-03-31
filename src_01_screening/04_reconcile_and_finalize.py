import rispy
import pandas as pd
import os
import re
from rapidfuzz import fuzz

# ================= Configuration / 配置 =================
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Master File (From Step 02) / 主文件
path_02_master = os.path.join(current_script_dir, '../data/intermediate/02_SMART_DEDUPLICATED_FINAL.ris')

# 2. Original Patch File (From Step 03 - Unedited) / 原始补丁文件 (未编辑)
path_03_original = os.path.join(current_script_dir, '../data/intermediate/03_incomplete_records_for_manual_fix.ris')

# 3. User Fixed File (In Processed folder) / 用户修复后的文件
# ⚠️ Please ensure your fixed file is named '03_fixed.ris'
path_03_fixed = os.path.join(current_script_dir, '../data/processed/03_manually_updated.ris')

# 4. Final Output / 最终输出
output_file = os.path.join(current_script_dir, '../data/processed/04_FINAL_MERGED_DEDUPLICATED.ris')

print(f"{'='*80}")
print(f"🚀 PHASE 4: Compare, Merge & Final Dedupe / 第4阶段：对比、合并与最终去重")
print(f"{'='*80}\n")

# ================= PART 1: Load Files / 加载文件 =================

def load_ris(path, name):
    if not os.path.exists(path):
        print(f"❌ Error: {name} not found at {path}")
        return None
    print(f"📖 Loading {name}...")
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        data = rispy.loads(f.read())
    print(f"   - Count: {len(data)}")
    return data

master_data = load_ris(path_02_master, "Master File (02)")
orig_patch_data = load_ris(path_03_original, "Original Patch (03)")
fixed_patch_data = load_ris(path_03_fixed, "Fixed Patch (User Edited)")

if not master_data or not fixed_patch_data:
    print("❌ Critical files missing. Aborting.")
    exit()

# ================= PART 2: Compare Fixes & Categorize / 修复对比与分类 =================

print(f"\n🔍 Analyzing Repair Status / 正在分析修复状态...")

# 1. Map original patch by Original_ID for lookup
# 建立原始数据的映射
orig_map = {}
if orig_patch_data:
    for entry in orig_patch_data:
        nid = None
        notes = entry.get('notes', [])
        if isinstance(notes, str): notes = [notes]
        for n in notes:
            if 'Original_ID:' in n:
                nid = n.split('Original_ID:')[1].strip()
                break
        if nid: orig_map[nid] = entry

# 2. Categorization Lists
# 分类列表
list_full_repair = []    # Title + Abstract + DOI fit
list_partial_repair = [] # Some fixed, some still missing
list_no_repair = []      # Still has all original missing tags

def is_missing(text):
    """Check if text contains [MISSING or is effectively empty"""
    if text is None: return True
    s = str(text).strip()
    if len(s) < 2: return True
    if '[MISSING' in s: return True
    return False

for fixed in fixed_patch_data:
    # Get ID
    nid = None
    notes = fixed.get('notes', [])
    if isinstance(notes, str): notes = [notes]
    for n in notes:
        if 'Original_ID:' in n:
            nid = n.split('Original_ID:')[1].strip()
            break
            
    # Current Status
    missing_fields = []
    if is_missing(fixed.get('title')): missing_fields.append('Title')
    if is_missing(fixed.get('abstract')): missing_fields.append('Abstract')
    if is_missing(fixed.get('doi')): missing_fields.append('DOI')
    
    # Logic to categorize
    # 逻辑：如果没有 missing_fields -> 完全修复
    # 逻辑：如果 missing_fields 数量等于原始缺失数量 (或者全缺) -> 没修复
    # 逻辑：介于两者之间 -> 部分修复
    
    status = ""
    original_entry = orig_map.get(nid)
    
    if len(missing_fields) == 0:
        list_full_repair.append(nid)
        status = "Full"
    elif len(missing_fields) == 3: # Title, Abs, DOI all missing
        list_no_repair.append({'id': nid, 'missing': missing_fields})
        status = "None"
    else:
        # Check if it was "Partial" to begin with or if user did partial work
        # If the user fixed at least ONE thing compared to original, but not all.
        # Or if it remains partially broken.
        
        # Determine strict "No Repair" (User didn't touch the missing tags)
        # 判断是否完全没动过
        if original_entry:
            orig_missing = []
            if is_missing(original_entry.get('title')): orig_missing.append('Title')
            if is_missing(original_entry.get('abstract')): orig_missing.append('Abstract')
            if is_missing(original_entry.get('doi')): orig_missing.append('DOI')
            
            if set(missing_fields) == set(orig_missing):
                list_no_repair.append({'id': nid, 'missing': missing_fields})
                status = "None"
            else:
                list_partial_repair.append({'id': nid, 'missing': missing_fields})
                status = "Partial"
        else:
            # Fallback if original not found
            list_partial_repair.append({'id': nid, 'missing': missing_fields})
            status = "Partial"

# ================= VISUALIZATION 1: SUMMARY TABLE / 汇总表 =================

print(f"\n📊 Repair Summary Table / 修复情况汇总表:")

summary_df = pd.DataFrame([
    {
        "Category (类别)": "Fully Repaired (完全修复)", 
        "Count": len(list_full_repair), 
        "Description": "Title, Abstract, & DOI are all present.",
        "Status": "✅ Excellent"
    },
    {
        "Category (类别)": "Partially Repaired (部分修复)", 
        "Count": len(list_partial_repair), 
        "Description": "Some fields fixed, others still missing.",
        "Status": "⚠️ Review"
    },
    {
        "Category (类别)": "Not Repaired (未修复)", 
        "Count": len(list_no_repair), 
        "Description": "No changes made to missing tags.",
        "Status": "❌ Discard?"
    }
])

print("-" * 80)
print(summary_df.to_string(index=False, justify='left'))
print("-" * 80)

# ================= VISUALIZATION 2: DETAILED BREAKDOWN / 详细分类统计 =================

def print_missing_breakdown(record_list, title_text):
    if not record_list:
        return

    print(f"\n{title_text}")
    print(f"{'-'*80}")
    
    # 1. Convert to DataFrame for easier grouping
    df_log = pd.DataFrame(record_list)
    
    # 2. Create a "Pattern" column (e.g., "Title + Abstract")
    # 将缺失字段列表转换为字符串，方便分组
    df_log['missing_pattern'] = df_log['missing'].apply(lambda x: " + ".join(x) if x else "None")
    
    # 3. Group by Pattern and Count
    # 统计每种缺失组合的数量
    pattern_counts = df_log['missing_pattern'].value_counts()
    
    # 4. Iterate and Print
    for pattern, count in pattern_counts.items():
        # Get all IDs for this specific pattern
        ids = df_log[df_log['missing_pattern'] == pattern]['id'].tolist()
        
        # Determine Severity / 严重程度判断
        severity = ""
        if "Title" in pattern: 
            severity = "🔴 CRITICAL (No Title)"
        elif "Abstract" in pattern and "DOI" in pattern:
            severity = "🟠 HIGH (No Abs+DOI)"
        elif "DOI" in pattern and len(pattern) < 5: # Only DOI missing
            severity = "🟢 LOW (No DOI)"
        else:
            severity = "🟡 MEDIUM"

        print(f"   📂 Pattern: [{pattern}]")
        print(f"      Count  : {count} records")
        print(f"      Impact : {severity}")
        
        # Print IDs in a readable wrapping format
        # 漂亮的 ID 列表打印
        id_str = ", ".join(str(x) for x in ids)
        print(f"      IDs    : {id_str}")
        print(f"   {'-'*40}")

# --- Execute for Partial Repairs ---
if list_partial_repair:
    print_missing_breakdown(list_partial_repair, "⚠️  PARTIAL REPAIR ANALYSIS (部分修复详细统计):")

# --- Execute for No Repairs ---
if list_no_repair:
    print_missing_breakdown(list_no_repair, "❌  NO REPAIR ANALYSIS (未修复记录详细统计):")
else:
    print("\n🎉 No 'Not Repaired' records found! Everything was touched.")

print(f"{'='*80}\n")

# ================= PART 3: Merge into Master / 合并回主文件 =================

print(f"\n🔄 Merging fixes into Master dataset / 正在将修复合并入主数据集...")

merged_count = 0
for fixed in fixed_patch_data:
    # Extract ID
    notes = fixed.get('notes', [])
    if isinstance(notes, str): notes = [notes]
    
    oid = None
    for n in notes:
        if 'Original_ID:' in n:
            match = re.search(r'Original_ID:(\d+)', n)
            if match: oid = int(match.group(1))
            
    # Update Master
    if oid is not None and 0 <= oid < len(master_data):
        target = master_data[oid]
        
        # Overwrite fields (Trusting user's fix)
        # 覆盖字段 (信任用户的修复)
        if fixed.get('title') and '[MISSING' not in fixed['title']: 
            target['title'] = fixed['title']
        if fixed.get('abstract') and '[MISSING' not in fixed['abstract']: 
            target['abstract'] = fixed['abstract']
        if fixed.get('doi') and '[MISSING' not in fixed['doi']: 
            target['doi'] = fixed['doi']
        if fixed.get('year'): target['year'] = fixed['year']
        if fixed.get('authors'): target['authors'] = fixed['authors']
        
        # Preserve Type Logic (Strict)
        if fixed.get('type_of_reference'):
            target['type_of_reference'] = fixed['type_of_reference']
            
        merged_count += 1

print(f"   ✅ Merged {merged_count} records.")

# ================= PART 4: Final Deduplication / 最终去重 =================

print(f"\n🔥 Running Final Deduplication (The Re-Check) / 正在运行最终去重(二次检查)...")
print("   (Because added titles/abstracts might reveal new duplicates / 因为新增的标题摘要可能暴露新的重复)")

df = pd.DataFrame(master_data)

# 1. Normalize
df['title_norm'] = df['title'].fillna('').astype(str).str.lower().str.replace(r'[^a-z0-9]', '', regex=True)
df['doi_norm'] = df['doi'].fillna('').astype(str).str.lower().str.strip()
df['abstract_len'] = df['abstract'].fillna('').astype(str).apply(len)

# 2. Logic
df['dup_id'] = -1
next_group_id = 0

# A. Exact DOI
mask_doi = (df['doi_norm'].str.len() > 5)
if mask_doi.any():
    for doi, group in df[mask_doi].groupby('doi_norm'):
        if len(group) > 1:
            df.loc[group.index, 'dup_id'] = next_group_id
            next_group_id += 1

# B. Exact Title
mask_title = (df['dup_id'] == -1) & (df['title_norm'].str.len() > 10)
if mask_title.any():
    for title, group in df[mask_title].groupby('title_norm'):
        if len(group) > 1:
            df.loc[group.index, 'dup_id'] = next_group_id
            next_group_id += 1

# C. Fuzzy Title (Critical for patched records)
print("   running fuzzy match...")
candidates = df[df['dup_id'] == -1].index.tolist()
fuzzy_hits = 0

for i in range(len(candidates)):
    idx_i = candidates[i]
    if df.loc[idx_i, 'dup_id'] != -1: continue
    
    t1 = df.loc[idx_i, 'title_norm']
    if len(t1) < 10: continue

    # Check neighbors
    for j in range(i + 1, min(i + 100, len(candidates))):
        idx_j = candidates[j]
        if df.loc[idx_j, 'dup_id'] != -1: continue
        
        t2 = df.loc[idx_j, 'title_norm']
        if abs(len(t1) - len(t2)) > 20: continue
        
        if fuzz.ratio(t1, t2) > 95:
            gid = next_group_id
            next_group_id += 1
            df.loc[idx_i, 'dup_id'] = gid
            df.loc[idx_j, 'dup_id'] = gid
            fuzzy_hits += 1
            break

print(f"   ⚠️  Found {fuzzy_hits} NEW duplicates after your fixes!")

# 3. Selection (Keep Longest Abstract)
final_indices = []
df.loc[df['dup_id'] == -1, 'dup_id'] = range(next_group_id, next_group_id + len(df[df['dup_id'] == -1]))

for gid, group in df.groupby('dup_id'):
    if len(group) == 1:
        final_indices.append(group.index[0])
    else:
        # Sort: Longest Abstract > Newest Year
        best = group.sort_values(by=['abstract_len', 'year'], ascending=[False, False]).index[0]
        final_indices.append(best)

df_final = df.loc[final_indices].copy()
removed = len(df) - len(df_final)

# ================= PART 5: Export / 导出 =================

print(f"\n📉 FINAL REPORT / 最终报告:")
print(f"   - Initial Total (02) : {len(df)}")
print(f"   - Removed Duplicates : {removed}")
print(f"   - Final Count        : {len(df_final)}")

print(f"\n💾 Saving to: {output_file}")

def clean_text(text):
    if text is None or str(text).lower() in ['nan', 'none', '']: return None
    s = str(text).replace('\n', ' ').strip()
    if '[MISSING' in s: return None # Remove placeholders if any left
    return s

with open(output_file, 'w', encoding='utf-8') as f:
    for _, row in df_final.iterrows():
        # Clean up Notes (Remove Original_ID)
        # 清理 Notes (移除 Original_ID, 保持文件干净)
        current_notes = row.get('notes', [])
        if isinstance(current_notes, str): current_notes = [current_notes]
        final_notes = [n for n in current_notes if 'Original_ID:' not in str(n)]
        
        # Type
        t = row.get('type_of_reference')
        if not t: t = 'JOUR'
        f.write(f"TY  - {t}\n")
        
        if row.get('title'): f.write(f"TI  - {clean_text(row['title'])}\n")
        if row.get('abstract'): f.write(f"AB  - {clean_text(row['abstract'])}\n")
        if row.get('doi'): f.write(f"DO  - {clean_text(row['doi'])}\n")
        if row.get('year'): f.write(f"PY  - {clean_text(row['year'])}\n")
        
        auths = row.get('authors')
        if isinstance(auths, list):
            for au in auths: 
                c = clean_text(au)
                if c: f.write(f"AU  - {c}\n")
        elif isinstance(auths, str):
            c = clean_text(auths)
            if c: f.write(f"AU  - {c}\n")
            
        # Write clean notes
        for n in final_notes:
            c = clean_text(n)
            if c: f.write(f"N1  - {c}\n")
            
        f.write("ER  - \n\n")

print(f"✅ DONE! File ready for ASReview: {os.path.basename(output_file)}")