import pandas as pd
import rispy
import glob
import os
import re
from Bio import Medline # Required: pip install biopython / 需安装 biopython
import bibtexparser    # Required: pip install bibtexparser / 需安装 bibtexparser

# ================= 0. Configuration / 配置 =================
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# Raw data directory / 原始数据目录
raw_dir = os.path.join(current_script_dir, '../data/raw') 
# Output file path / 输出文件路径
output_file = os.path.join(current_script_dir, '../data/intermediate/01_preliminary_merged.ris')

# Create output directory if not exists / 如果不存在则创建输出目录
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Stats dictionary / 统计字典
source_stats = {}

# ================= 1. Helper Functions / 辅助函数 =================

def clean_doi(doi_str):
    """
    Standardize DOI: remove URL prefixes, brackets, and whitespace.
    标准化 DOI：移除 URL 前缀、中括号后缀及多余空格。
    """
    if not doi_str or pd.isna(doi_str): return ""
    doi = str(doi_str).lower().strip()
    # Remove URL prefixes / 移除 URL 前缀
    doi = re.sub(r'https?://(dx\.)?doi\.org/', '', doi)
    # Remove PubMed style [doi] suffix / 移除 PubMed 风格的 [doi] 后缀
    doi = doi.split('[')[0].strip() 
    # Remove 'doi:' prefix / 移除 'doi:' 前缀
    doi = re.sub(r'^doi:\s*', '', doi)
    return doi

def map_ris_type_strict(raw_type):
    """
    Strict mapping. If not explicitly a journal or conference, return 'GEN' (Unknown).
    严格映射。如果不是明确的期刊或会议，返回 'GEN' (代表未知)。
    """
    if not raw_type: return "GEN" # Missing type -> Unknown / 缺失类型 -> 未知
    
    t = str(raw_type).lower().strip()
    
    # Explicit Journal Indicators / 明确的期刊指示符
    if t in ['article', 'journal article', 'jour', 'journal']:
        return 'JOUR'
        
    # Explicit Conference Indicators / 明确的会议指示符
    if t in ['conf', 'inproceedings', 'conference paper', 'conference', 'proc']:
        return 'CONF'
        
    # Explicit Book Indicators / 明确的书籍指示符
    if t in ['book', 'chap', 'inbook']:
        return 'BOOK'

    # If the file already has a valid 4-letter RIS tag (e.g., RPRT, THES), keep it.
    # 如果文件已经有标准的 4 字母 RIS 标签（如 RPRT, THES），保留它。
    if len(t) == 4 and t.isupper():
        return t
        
    # Default to Generic/Unknown for RIS standard
    # 默认为 RIS 标准中的通用/未知类型
    return "GEN" 

def normalize_entry(entry, source_name, source_format='ris'):
    """
    Normalize fields and track stats.
    标准化字段并追踪统计信息。
    """
    # Initialize stats for this source / 初始化该源的统计信息
    if source_name not in source_stats:
        source_stats[source_name] = {
            'count': 0, 
            'is_journal': 0, 
            'is_unknown': 0,
            'no_abstract': 0, # Track missing abstract / 追踪无摘要
            'no_doi': 0       # Track missing DOI / 追踪无 DOI
        }

    # --- 1. Type Handling (Strict) / 类型处理 (严格) ---
    raw_type_val = entry.get('type_of_reference') or entry.get('ENTRYTYPE') or entry.get('PT')
    if isinstance(raw_type_val, list): raw_type_val = raw_type_val[0]
    
    # Map strictly / 严格映射
    ris_type = map_ris_type_strict(raw_type_val)
    
    # Update stats based on result / 根据结果更新统计
    if ris_type == 'JOUR':
        source_stats[source_name]['is_journal'] += 1
    elif ris_type == 'GEN':
        source_stats[source_name]['is_unknown'] += 1

    # --- 2. Title & Abstract / 标题与摘要 ---
    title = str(entry.get('title') or entry.get('TI') or entry.get('T1') or "").strip()
    # Remove newlines / 移除换行符
    title = title.replace('\n', ' ').replace('\r', '')
    
    abstract = str(entry.get('abstract') or entry.get('AB') or entry.get('N2') or "").strip()
    
    # --- 3. DOI Handling / DOI 处理 ---
    raw_doi = entry.get('doi') or entry.get('DO') or entry.get('LID') or ""
    if isinstance(raw_doi, list):
        final_doi = ""
        for item in raw_doi:
            if '[doi]' in item.lower() or '10.' in item: 
                final_doi = clean_doi(item)
                break
    else:
        final_doi = clean_doi(raw_doi)

    # --- 4. Year Extraction / 年份提取 ---
    year_raw = str(entry.get('year') or entry.get('PY') or entry.get('DP') or entry.get('Y1') or '')
    year_match = re.search(r'\d{4}', year_raw)
    year = year_match.group(0) if year_match else ""

    # --- 5. Author Handling / 作者处理 ---
    raw_authors = entry.get('author') or entry.get('AU') or entry.get('authors') or []
    clean_authors = []
    
    if source_format == 'bib' and isinstance(raw_authors, str):
        # Split BibTeX authors / 分割 BibTeX 作者
        clean_authors = [a.strip() for a in raw_authors.split(' and ')]
    elif isinstance(raw_authors, list):
        clean_authors = raw_authors
    elif isinstance(raw_authors, str):
        clean_authors = [raw_authors]

    # --- Update Counts / 更新计数 ---
    source_stats[source_name]['count'] += 1
    if not abstract: source_stats[source_name]['no_abstract'] += 1
    if not final_doi: source_stats[source_name]['no_doi'] += 1

    return {
        'type': ris_type,
        'title': title,
        'abstract': abstract,
        'year': year,
        'doi': final_doi,
        'authors': clean_authors
    }

# ================= 2. Main Processing Loop / 主处理循环 =================

all_records = []

# 2.1 BibTeX (ACM)
for f_path in glob.glob(os.path.join(raw_dir, '*.bib')):
    fname = os.path.basename(f_path)
    print(f"🔄 Processing BibTeX / 处理 BibTeX: {fname}...")
    try:
        with open(f_path, encoding='utf-8') as bibfile:
            bib_db = bibtexparser.load(bibfile)
            for e in bib_db.entries:
                all_records.append(normalize_entry(e, fname, source_format='bib'))
    except Exception as ex:
        print(f"  ❌ Error reading {fname} / 读取错误: {ex}")

# 2.2 PubMed (.txt)
for f_path in glob.glob(os.path.join(raw_dir, 'pubmed*.txt')):
    fname = os.path.basename(f_path)
    print(f"🧬 Processing PubMed / 处理 PubMed: {fname}...")
    try:
        with open(f_path, encoding='utf-8') as handle:
            for e in Medline.parse(handle):
                all_records.append(normalize_entry(e, fname, source_format='pubmed'))
    except Exception as ex:
        print(f"  ❌ Error reading {fname} / 读取错误: {ex}")

# 2.3 RIS (IEEE, WoS, ProQuest, OpenAlex)
for f_path in glob.glob(os.path.join(raw_dir, '*.ris')):
    fname = os.path.basename(f_path)
    print(f"📖 Processing RIS / 处理 RIS: {fname}...")
    try:
        with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # ProQuest fix: Undefined -> GEN (Unknown)
            # ProQuest 修复: Undefined -> GEN (未知)
            content = content.replace("TY  - Undefined", "TY  - GEN") 
            entries = rispy.loads(content)
            for e in entries:
                all_records.append(normalize_entry(e, fname, source_format='ris'))
    except Exception as ex:
        print(f"  ❌ Error reading {fname} / 读取错误: {ex}")

# ================= 3. Export & Report / 导出与报告 =================

print("\n" + "="*100)
# Print table header with all stats / 打印包含所有统计信息的表头
print(f"{'Source File':<25} | {'Count':<12} | {'Journal':<8} | {'Unknown':<8} | {'No Abs':<15} | {'No DOI':<12}")
print("-" * 100)

for src, s in source_stats.items():
    print(f"{src[:25]:<25} | {s['count']:<12} | {s['is_journal']:<8} | {s['is_unknown']:<8} | {s['no_abstract']:<15} | {s['no_doi']:<12}")
print("="*100)

print("Note: 'Unknown' means the type was not explicitly 'Article' or 'Journal' in the source.")
print("注意: 'Unknown' 表示源文件中没有明确标记为 'Article' 或 'Journal'。")

# Write to file / 写入文件
with open(output_file, 'w', encoding='utf-8') as f:
    for r in all_records:
        f.write(f"TY  - {r['type']}\n")
        if r['title']: f.write(f"TI  - {r['title']}\n")
        if r['abstract']: f.write(f"AB  - {r['abstract']}\n")
        if r['doi']: f.write(f"DO  - {r['doi']}\n")
        if r['year']: f.write(f"PY  - {r['year']}\n")
        
        # Write authors line by line / 逐行写入作者
        for au in r['authors']:
            f.write(f"AU  - {au}\n")
            
        f.write("ER  - \n\n")

print(f"\n✅ Merged file saved to / 合并文件已保存至: {output_file}")