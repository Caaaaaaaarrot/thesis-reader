import os
import re
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
from ..database import get_db
from ..config import settings
from ..models.paper import PaperResponse
from ..utils.pdf_utils import get_pdf_info

# 从文件名推断 venue/year 的规则
VENUE_PATTERNS: list[tuple[str, str]] = [
    # 软件工程
    (r'\bicse\b', 'ICSE'), (r'\base\b', 'ASE'), (r'\bfse\b', 'FSE'),
    (r'\besec\b', 'ESEC'), (r'\bissta\b', 'ISSTA'),
    (r'\bmsr\b', 'MSR'), (r'\bsaner\b', 'SANER'), (r'\bicsme\b', 'ICSME'),
    (r'\bicpc\b', 'ICPC'), (r'\bicse-src\b', 'ICSE-SRC'),
    # 人工智能
    (r'\bneurips\b', 'NeurIPS'), (r'\bicml\b', 'ICML'), (r'\biclr\b', 'ICLR'),
    (r'\baaai\b', 'AAAI'), (r'\bijcai\b', 'IJCAI'), (r'\buai\b', 'UAI'),
    (r'\baistats\b', 'AISTATS'),
    # 计算机视觉
    (r'\bcvpr\b', 'CVPR'), (r'\biccv\b', 'ICCV'), (r'\beccv\b', 'ECCV'),
    (r'\bwacv\b', 'WACV'), (r'\bbmvc\b', 'BMVC'),
    # 自然语言处理
    (r'\bacl\b', 'ACL'), (r'\bemnlp\b', 'EMNLP'), (r'\bnaacl\b', 'NAACL'),
    (r'\bcoling\b', 'COLING'), (r'\beacl\b', 'EACL'),
    # 系统/网络
    (r'\bsosp\b', 'SOSP'), (r'\bosdi\b', 'OSDI'), (r'\bnsdi\b', 'NSDI'),
    (r'\bsigcomm\b', 'SIGCOMM'), (r'\beurosys\b', 'EuroSys'),
    (r'\batc\b', 'ATC'), (r'\bfast\b', 'FAST'),
    # 安全
    (r'\bccs\b', 'CCS'), (r'\bndss\b', 'NDSS'), (r'\buss\b', 'USENIX Security'),
    (r'\bsec\b', 'IEEE S&P'), (r'\boakland\b', 'IEEE S&P'),
    # 数据库
    (r'\bsigmod\b', 'SIGMOD'), (r'\bvldb\b', 'VLDB'), (r'\bicde\b', 'ICDE'),
    # 人机交互
    (r'\bchi\b', 'CHI'), (r'\bubicomp\b', 'UbiComp'), (r'\bcscw\b', 'CSCW'),
    (r'\buist\b', 'UIST'),
    # 编程语言
    (r'\bpopl\b', 'POPL'), (r'\bpldi\b', 'PLDI'), (r'\boopsla\b', 'OOPSLA'),
    (r'\bicfp\b', 'ICFP'),
    # 其他
    (r'\bwww\b', 'WWW'), (r'\bwsdm\b', 'WSDM'), (r'\bkdd\b', 'KDD'),
    (r'\bsiggraph\b', 'SIGGRAPH'), (r'\bsigir\b', 'SIGIR'),
    (r'\btse\b', 'TSE'), (r'\btosem\b', 'TOSEM'),
    (r'\btpami\b', 'TPAMI'), (r'\btip\b', 'TIP'),
    (r'\barxiv\b', 'arXiv'),
]


def infer_metadata(filename: str) -> dict:
    """从文件名推断 venue 和 year"""
    name = Path(filename).stem.lower()
    venue = ""
    year = None

    # 匹配 venue（处理 venYEAR 如 ase25、ICSE24 和 ven_YEAR 如 icse_2024）
    for pattern, label in VENUE_PATTERNS:
        # 先匹配 venue 后跟年份数字或下划线或边界的模式
        p = pattern[:-2] + r'(?:\d{2,4})?(?:\b|_)'
        if re.search(p, name):
            venue = label
            break

    # 匹配年份
    year_match = re.search(r'(?:^|\D)(\d{2}|\d{4})(?:\D|$)', name)
    if year_match:
        y = int(year_match.group(1))
        if y < 100:
            year = 2000 + y if y <= 50 else 1900 + y
        else:
            year = y

    # 提取可能的标题（去除 venue 和 year 后的部分）
    title = Path(filename).stem
    title = re.sub(r'\b(?:' + '|'.join(p for p, _ in VENUE_PATTERNS) + r')\b',
                   '', title, flags=re.IGNORECASE)
    title = re.sub(r'(?:^|\D)\d{2,4}(?:\D|$)', ' ', title)
    title = re.sub(r'[_-]', ' ', title).strip()
    title = re.sub(r'\s+', ' ', title)

    return {"venue": venue, "year": year, "title": title}


def import_paper(file_path: str) -> PaperResponse:
    """导入论文到库中"""
    src = Path(file_path)
    filename = src.name

    # 使用 hash 作为 ID
    file_hash = hashlib.sha1(str(src).encode()).hexdigest()[:12]

    # 基本信息
    file_size = src.stat().st_size
    date_added = datetime.now().strftime("%Y-%m-%d %H:%M")

    # PDF 信息
    page_count = 0
    try:
        info = get_pdf_info(str(src))
        page_count = info.get("page_count", 0)
        # 提取内置元数据
        if info.get("title") and not info.get("title", "").strip() == "":
            pass  # 可在后续增强中利用
    except Exception:
        pass

    # 推断元数据
    meta = infer_metadata(filename)

    # 确保 papers 目录存在
    settings.papers_dir.mkdir(parents=True, exist_ok=True)

    # 复制文件
    dest_dir = settings.papers_dir
    dest = dest_dir / filename

    # 如果同名文件已存在，加后缀
    if dest.exists():
        base = dest.stem
        suffix = dest.suffix
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{base}_{counter}{suffix}"
            counter += 1

    shutil.copy2(str(src), str(dest))
    rel_path = str(dest.relative_to(settings.workspace_root))

    # 写入数据库
    conn = get_db()
    try:
        paper_id = file_hash
        conn.execute(
            """INSERT OR REPLACE INTO papers
               (id, file_path, title, venue, year, date_added, page_count, file_size)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (paper_id, rel_path, meta["title"], meta["venue"],
             meta["year"], date_added, page_count, file_size)
        )
        conn.commit()

        cur = conn.execute(
            "SELECT p.*, s.* FROM papers p LEFT JOIN speed_reads s ON p.id = s.paper_id WHERE p.id = ?",
            (paper_id,)
        )
        d = dict(cur.fetchone())
        return PaperResponse.from_row(d, d)
    finally:
        conn.close()
