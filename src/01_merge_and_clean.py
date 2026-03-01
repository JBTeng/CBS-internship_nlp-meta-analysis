import pandas as pd
import rispy
import glob
import os

# ================= 0. Configuration / 环境配置 =================

# 获取当前脚本所在的目录
current_script_dir = os.path.dirname(os.path.abspath(__file__))

# 定义数据处理目录 (假设在脚本目录的上一级的 data/processed)
processed_dir = os.path.abspath(os.path.join(current_script_dir, '../data/processed'))

# 输入文件：刚才生成的合并文件
input_file = os.path.join(processed_dir, 'preliminary_merged_for_asreview.ris')

# 输出文件：最终给 ASReview 的完美文件
output_file = os.path.join(processed_dir, 'SMART_DEDUPLICATED_FINAL.ris')

# 打印一下确认路径是否正确
print(f"Reading from: {input_file}")
print(f"Saving to: {output_file}")

# ================= 1. EndNote Smart Parser / 智能 EndNote 解析器 =================
# ================= 1. EndNote Parser / EndNote (.enw) 解析器 =================
def parse_enw(file_path):
    """
    Manually parse EndNote (.enw) format into a list of dictionaries.
    手动解析 EndNote (.enw) 格式并转换为字典列表。
    """
    records = []
    current_record = {}
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Start of a new record / 新记录开始
        if line.startswith('%0'):
            if current_record:
                records.append(current_record)
            current_record = {'type': 'JOUR'} # Default to Journal / 默认为期刊
            
        # Parse fields / 解析字段
        elif line.startswith('%T '): current_record['title'] = line[3:]
        elif line.startswith('%A '): 
            if 'authors' not in current_record: current_record['authors'] = []
            current_record['authors'].append(line[3:])
        elif line.startswith('%X '): current_record['abstract'] = line[3:] # Abstract / 摘要
        elif line.startswith('%J '): current_record['journal'] = line[3:]
        elif line.startswith('%D '): current_record['year'] = line[3:]
        elif line.startswith('%R '): current_record['doi'] = line[3:]
        
    if current_record:
        records.append(current_record)
        
    return records

# ================= 2. Field Normalization / 字段标准化 =================
def normalize_entry(entry, source_name):
    """
    Standardize fields across different database formats.
    统一不同数据库来源的字段名称。
    """
    # Title: Handle multiple possible tags (ProQuest uses T1/TI)
    title = entry.get('title') or entry.get('primary_title') or entry.get('TI') or entry.get('T1') or ""
    
    # Abstract: Check common tags AB, N2, and abstract
    abstract = entry.get('abstract') or entry.get('AB') or entry.get('N2') or ""
    
    # Year: Extract 4-digit year using regex
    year_raw = str(entry.get('year') or entry.get('PY') or entry.get('Y1') or '')
    year_match = re.search(r'\d{4}', year_raw)
    year = year_match.group(0) if year_match else ""
    
    # DOI: Clean URL prefixes and whitespace
    doi = str(entry.get('doi') or entry.get('DO', '')).lower().replace('https://doi.org/', '').strip()
    
    return {
        'title': str(title).strip(),
        'abstract': str(abstract).strip(),
        'year': year,
        'doi': doi,
        'authors': entry.get('authors') or [],
        'source': source_name
    }

# ================= 3. Processing All Files / 读取并处理所有文件 =================
all_records = []

# 3.1 Handle .enw files (Commonly from ACM)/处理 .enw 文件（通常来自 ACM 数据库）
enw_files = glob.glob(os.path.join(raw_dir, '*.enw'))
for f_path in enw_files:
    fname = os.path.basename(f_path)
    print(f"🔄 Converting EndNote file / 正在转换 EndNote 文件: {fname} ...")
    entries = parse_enw(f_path)
    for e in entries:
        all_records.append(normalize_entry(e, fname))

# 3.2 Handle .ris files (IEEE, WoS, OpenAlex, ProQuest)/处理 .ris 文件（IEEE, WoS, OpenAlex, ProQuest 等）
ris_files = glob.glob(os.path.join(raw_dir, '*.[rR][iI][sS]'))
for f_path in ris_files:
    fname = os.path.basename(f_path)
    print(f"📖 Reading RIS file / 正在读取 RIS 文件: {fname} ...")
    
    try:
        # Pre-read to fix ProQuest "TY - Undefined" issue/预读取：修复 ProQuest 导出的 "TY - Undefined" 类型错误
        with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Force repair of broken ProQuest types
        # 强制修复 ProQuest 的怪异类型定义
        if "TY  - Undefined" in content:
            print(f"  ⚠️ Detected 'TY - Undefined' in {fname}, auto-fixing... / 检测到错误类型，正在修复...")
            content = content.replace("TY  - Undefined", "TY  - JOUR")
            
        entries = rispy.loads(content)
        for e in entries:
            all_records.append(normalize_entry(e, fname))
            
    except Exception as ex:
        print(f"  ❌ Failed to read / 读取失败 {fname}: {ex}")

# ================= 4. Diagnostics & Export / 诊断与导出 =================
df = pd.DataFrame(all_records)
print(f"\n📊 Total records read / 总计读取: {len(df)} records")

# Check for missing abstracts / 检查摘要缺失情况
missing_abs = df[df['abstract'] == ""]
if len(missing_abs) > 0:
    print(f"⚠️ Warning: {len(missing_abs)} records are missing abstracts!")
    print("  Source distribution / 来源分布:", missing_abs['source'].value_counts().to_dict())
    print("  👉 Suggestion: Re-export from source and ensure 'Abstract' is checked./建议：重新从数据库导出，并确保勾选了“摘要”选项")

# Export to clean RIS format for ASReview
# 导出为 ASReview 兼容的干净 RIS 格式
def clean_text(text):
    """Remove newlines and extra spaces / 清除换行符和多余空格"""
    if not text: return ""
    return str(text).replace('\n', ' ').replace('\r', ' ').strip()

with open(output_file, 'w', encoding='utf-8') as f:
    for _, row in df.iterrows():
        f.write("TY  - JOUR\n") # Default to Journal / 默认为期刊类型
        
        t = clean_text(row['title'])
        if t: f.write(f"TI  - {t}\n")
        
        a = clean_text(row['abstract'])
        if a: f.write(f"AB  - {a}\n")
        
        # Handle authors (List vs String) / 处理作者字段（列表或字符串）
        if isinstance(row['authors'], list):
            for au in row['authors']:
                f.write(f"AU  - {clean_text(au)}\n")
        elif row['authors']:
            f.write(f"AU  - {clean_text(row['authors'])}\n")
            
        # Year and DOI / 年份和 DOI
        if row['year']: f.write(f"PY  - {row['year']}\n")
        if row['doi']: f.write(f"DO  - {row['doi']}\n")
        
        f.write("ER  - \n\n") # End of Record / 记录结束标志

print(f"\n✅ Done! File saved to / 转换完成！文件保存至: {output_file}")