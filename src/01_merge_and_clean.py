import pandas as pd
import rispy
import glob
import os
import re
from Bio import Medline # 需要安装 biopython
import bibtexparser    # 需要安装 bibtexparser

# ================= 0. Configuration / 配置 =================
current_script_dir = os.path.dirname(os.path.abspath(__file__))
raw_dir = os.path.join(current_script_dir, '../data/raw')
output_file = os.path.join(current_script_dir, '../data/processed/01_preliminary_merged.ris')

# 用来存储每个数据库的统计信息 / Used for reporting stats per database
source_stats = {}

# ================= 1. Helper Functions / 辅助工具 =================

def clean_doi(doi_str):
    """
    Standardize DOI: remove URL prefixes, brackets, and whitespace.
    标准化 DOI：移除 URL 前缀、中括号后缀及多余空格。
    """
    if not doi_str or pd.isna(doi_str): return ""
    # Convert to string and lowercase / 转为字符串并小写
    doi = str(doi_str).lower().strip()
    # Remove common URL prefixes / 移除常见的 URL 前缀
    doi = re.sub(r'https?://(dx\.)?doi\.org/', '', doi)
    # Remove PubMed style [doi] suffix / 移除 PubMed 风格的 [doi] 后缀
    doi = doi.split('[')[0].strip()
    # Remove 'doi:' prefix / 移除 'doi:' 字样前缀
    doi = re.sub(r'^doi:\s*', '', doi)
    return doi

def normalize_entry(entry, source_name):
    """
    Normalize fields across formats and track missing data.
    统一不同格式的字段，并追踪缺失数据。
    """
    # 1. Type Handling / 文章类型处理
    # Check RIS 'type_of_reference', BibTeX 'ENTRYTYPE', or PubMed 'PT'
    ref_type = entry.get('type_of_reference') or entry.get('ENTRYTYPE') or entry.get('PT') or "none"
    if isinstance(ref_type, list): ref_type = ref_type[0] # Take first if list (PubMed)
    if ref_type.lower() == "undefined": ref_type = "none"

    # 2. Title & Abstract / 标题与摘要
    title = str(entry.get('title') or entry.get('TI') or entry.get('T1') or "").strip()
    abstract = str(entry.get('abstract') or entry.get('AB') or entry.get('N2') or "").strip()
    
    # 3. DOI / DOI 归一化处理
    # PubMed uses LID for DOI, RIS uses DO/DO, Bib uses doi
    raw_doi = entry.get('doi') or entry.get('DO') or entry.get('LID') or ""
    # Handle PubMed LID list / 处理 PubMed LID 可能返回列表的情况
    if isinstance(raw_doi, list):
        final_doi = ""
        for item in raw_doi:
            if '[doi]' in item.lower(): final_doi = clean_doi(item)
    else:
        final_doi = clean_doi(raw_doi)

    # 4. Year / 年份提取
    year_raw = str(entry.get('year') or entry.get('PY') or entry.get('DP') or entry.get('Y1') or '')
    year_match = re.search(r'\d{4}', year_raw)
    year = year_match.group(0) if year_match else ""

    # --- Update Stats / 更新统计信息 ---
    if source_name not in source_stats:
        source_stats[source_name] = {'count': 0, 'no_title': 0, 'no_abstract': 0, 'no_doi': 0}
    
    source_stats[source_name]['count'] += 1
    if not title: source_stats[source_name]['no_title'] += 1
    if not abstract: source_stats[source_name]['no_abstract'] += 1
    if not final_doi: source_stats[source_name]['no_doi'] += 1

    return {
        'title': title,
        'abstract': abstract,
        'year': year,
        'doi': final_doi,
        'type': ref_type,
        'authors': entry.get('author') or entry.get('AU') or entry.get('authors') or [],
        'source': source_name
    }

# ================= 2. Main Processing Loop / 主处理循环 =================

all_records = []

# 2.1 Handle BibTeX (ACM)
for f_path in glob.glob(os.path.join(raw_dir, '*.bib')):
    fname = os.path.basename(f_path)
    print(f"🔄 Processing BibTeX: {fname}...")
    with open(f_path, encoding='utf-8') as bibfile:
        bib_db = bibtexparser.load(bibfile)
        for e in bib_db.entries:
            all_records.append(normalize_entry(e, fname))

# 2.2 Handle PubMed (.txt / Medline)
for f_path in glob.glob(os.path.join(raw_dir, 'pubmed*.txt')):
    fname = os.path.basename(f_path)
    print(f"🧬 Processing PubMed (Medline): {fname}...")
    with open(f_path, encoding='utf-8') as handle:
        for e in Medline.parse(handle):
            all_records.append(normalize_entry(e, fname))

# 2.3 Handle RIS (IEEE, WoS, OpenAlex, ProQuest)
for f_path in glob.glob(os.path.join(raw_dir, '*.ris')):
    fname = os.path.basename(f_path)
    print(f"📖 Processing RIS: {fname}...")
    with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    # Repair ProQuest error types / 修复 ProQuest 的错误类型标注
    content = content.replace("TY  - Undefined", "TY  - JOUR")
    try:
        entries = rispy.loads(content)
        for e in entries:
            all_records.append(normalize_entry(e, fname))
    except Exception as ex:
        print(f"  ❌ Error reading {fname}: {ex}")

# ================= 3. Summary Report / 生成统计报告 =================
print("\n" + "="*50)
print(f"{'Source File':<25} | {'Total':<6} | {'No Abs':<6} | {'No DOI':<6}")
print("-" * 50)
for src, s in source_stats.items():
    print(f"{src[:25]:<25} | {s['count']:<6} | {s['no_abstract']:<6} | {s['no_doi']:<6}")
print("="*50)

# ================= 4. Export to Unified RIS / 导出统一的 RIS =================
with open(output_file, 'w', encoding='utf-8') as f:
    for r in all_records:
        f.write(f"TY  - {r['type']}\n")
        if r['title']: f.write(f"TI  - {r['title']}\n")
        if r['abstract']: f.write(f"AB  - {r['abstract']}\n")
        if r['doi']: f.write(f"DO  - {r['doi']}\n")
        if r['year']: f.write(f"PY  - {r['year']}\n")
        # Author handling / 处理作者列表
        authors = r['authors']
        if isinstance(authors, list):
            for au in authors: f.write(f"AU  - {str(au)}\n")
        else:
            f.write(f"AU  - {str(authors)}\n")
        f.write("ER  - \n\n")

print(f"\n✅ All set! Merged file saved to: {output_file}")