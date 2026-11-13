import re
from pathlib import Path
from ..models.paper import PaperResponse

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
    (r'\btpds\b', 'TPDS'), (r'\btc\b', 'TC'), (r'\btdsc\b', 'TDSC'),
    (r'\btifs\b', 'TIFS'), (r'\btkde\b', 'TKDE'), (r'\btois\b', 'TOIS'),
    (r'\btoc\b', 'TOC'), (r'\btodaes\b', 'TODAES'),
    (r'\bisca\b', 'ISCA'), (r'\bmicro\b', 'MICRO'), (r'\bhpca\b', 'HPCA'),
    (r'\basplos\b', 'ASPLOS'), (r'\bsc\b', 'SC'),
    (r'\bmobicom\b', 'MobiCom'), (r'\bmobisys\b', 'MobiSys'),
    (r'\bsensys\b', 'SenSys'), (r'\bipts\b', 'IPSN'),
    (r'\brtss\b', 'RTSS'), (r'\brtas\b', 'RTAS'),
    (r'\bemsoft\b', 'EMSOFT'), (r'\bcases\b', 'CASES'),
    (r'\bdac\b', 'DAC'), (r'\biccad\b', 'ICCAD'),
    (r'\barxiv\b', 'arXiv'),
]


def infer_metadata(filename: str, pdf_meta: dict | None = None) -> dict:
    """从文件名和 PDF 内部元数据推断 venue、year、title"""
    name = Path(filename).stem.lower()
    pdf_meta = pdf_meta or {}
    venue = pdf_meta.get("venue_from_text", "")
    year = pdf_meta.get("year_from_text", None)

    # 如果 PDF 文本没找到 venue，回退到文件名匹配
    if not venue:
        for pattern, label in VENUE_PATTERNS:
            p = pattern[:-2] + r'(?:\d{2,4})?(?:\b|_)'
            if re.search(p, name):
                venue = label
                break

    # 如果 PDF 没找到年份，回退到文件名匹配
    if not year:
        year_match = re.search(r'(?:^|\D)(\d{2}|\d{4})(?:\D|$)', name)
        if year_match:
            y = int(year_match.group(1))
            year = 2000 + y if y < 100 else 1900 + y if y > 50 else y

    # 标题：优先用 PDF 嵌入的标题，否则从文件名清理
    title = pdf_meta.get("embedded_title", "")
    if title:
        # 清理嵌入标题中常见的多余信息
        title = re.sub(r'\s+', ' ', title).strip()
    if not title:
        title = Path(filename).stem
        # 构建扩展 venue 模式（含年份后缀变体），用于标题清理
        extended_patterns = []
        for pat, _ in VENUE_PATTERNS:
            p = pat[:-2] + r'(?:\d{2,4})?(?:\b|_)'
            extended_patterns.append(p)
        title = re.sub(r'(?:\b|_)(?:' + '|'.join(extended_patterns) + r')',
                       ' ', title, flags=re.IGNORECASE)
        title = re.sub(r'(?:^|(?<=\D))(\d{2,4})(?=\D|$)', ' ', title)
        title = re.sub(r'[_-]', ' ', title).strip()
        title = re.sub(r'\s+', ' ', title)

    return {"venue": venue, "year": year, "title": title}


def import_paper(file_path: str) -> PaperResponse:
    """手动导入和目录监听共用同一套索引与去重规则。"""
    from .library_index import import_file
    return import_file(file_path)
