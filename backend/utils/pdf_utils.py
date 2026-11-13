"""PyMuPDF 封装的 PDF 工具函数"""

import re

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


def get_pdf_info(file_path: str) -> dict:
    """获取 PDF 基本信息"""
    if not HAS_PYMUPDF:
        return {"page_count": 0, "title": "", "error": "PyMuPDF 未安装"}
    doc = fitz.open(file_path)
    meta = doc.metadata
    info = {
        "page_count": doc.page_count,
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
    }
    doc.close()
    return info


# 已知期刊/会议全名关键词 → 缩写
_JOURNAL_KEYWORDS: list[tuple[str, str]] = [
    # IEEE 期刊
    ("Transactions on Parallel and Distributed Systems", "TPDS"),
    ("Transactions on Computers", "TC"),
    ("Transactions on Software Engineering", "TSE"),
    ("Transactions on Pattern Analysis and Machine Intelligence", "TPAMI"),
    ("Transactions on Image Processing", "TIP"),
    ("Transactions on Knowledge and Data Engineering", "TKDE"),
    ("Transactions on Information Forensics and Security", "TIFS"),
    ("Transactions on Dependable and Secure Computing", "TDSC"),
    ("Transactions on Visualization and Computer Graphics", "TVCG"),
    ("Transactions on Mobile Computing", "TMC"),
    ("Transactions on Networking", "TON"),
    ("Journal on Selected Areas in Communications", "JSAC"),
    # ACM 期刊
    ("Transactions on Software Engineering and Methodology", "TOSEM"),
    ("Transactions on Graphics", "TOG"),
    ("Transactions on Information Systems", "TOIS"),
    ("Transactions on Computer Systems", "TOCS"),
    ("Transactions on Architecture and Code Optimization", "TACO"),
    ("Transactions on Storage", "TOS"),
    # 其他期刊
    ("Journal of Machine Learning Research", "JMLR"),
    # 常见会议全名
    ("International Conference on Software Engineering", "ICSE"),
    ("International Conference on Machine Learning", "ICML"),
    ("Conference on Neural Information Processing Systems", "NeurIPS"),
    ("Conference on Computer Vision and Pattern Recognition", "CVPR"),
    ("International Conference on Computer Vision", "ICCV"),
    ("European Conference on Computer Vision", "ECCV"),
    ("International Conference on Learning Representations", "ICLR"),
    ("Conference on Empirical Methods in Natural Language Processing", "EMNLP"),
    ("Annual Meeting of the Association for Computational Linguistics", "ACL"),
    ("Symposium on Operating Systems Principles", "SOSP"),
    ("Symposium on Theory of Computing", "STOC"),
    ("Symposium on Foundations of Computer Science", "FOCS"),
    ("International Conference on Data Engineering", "ICDE"),
    ("International Conference on Very Large Data Bases", "VLDB"),
    ("Conference on Management of Data", "SIGMOD"),
    ("International Conference on Distributed Computing Systems", "ICDCS"),
    ("International Parallel and Distributed Processing Symposium", "IPDPS"),
    ("Conference on Pervasive and Ubiquitous Computing", "UbiComp"),
    ("Conference on Human Factors in Computing Systems", "CHI"),
    ("Conference on Object-Oriented Programming", "OOPSLA"),
    ("Conference on Programming Language Design and Implementation", "PLDI"),
    ("Symposium on Cloud Computing", "SoCC"),
    ("Symposium on Networked Systems Design and Implementation", "NSDI"),
    ("Symposium on Security and Privacy", "S&P"),  # also matches USENIX Security
    ("International Conference on Distributed Computing and Networking", "ICDCN"),
    ("International World Wide Web Conference", "WWW"),
    ("Conference on Knowledge Discovery and Data Mining", "KDD"),
    ("International Conference on Research in Security and Privacy", "ESORICS"),
    ("International Conference on Parallel and Distributed Systems", "ICPADS"),
    ("International Conference on Parallel Processing", "ICPP"),
    ("International Symposium on Computer Architecture", "ISCA"),
    ("International Symposium on Microarchitecture", "MICRO"),
    ("International Symposium on High-Performance Computer Architecture", "HPCA"),
    ("Architectural Support for Programming Languages and Operating Systems", "ASPLOS"),
    ("International Conference for High Performance Computing", "SC"),
    ("International Conference on Mobile Computing and Networking", "MobiCom"),
    ("International Conference on Embedded Wireless Systems and Networks", "EWSN"),
    ("Real-Time Systems Symposium", "RTSS"),
    ("Design Automation Conference", "DAC"),
    ("International Conference on Computer-Aided Design", "ICCAD"),
    ("Symposium on Discrete Algorithms", "SODA"),
    ("International Colloquium on Automata, Languages and Programming", "ICALP"),
    ("International Conference on Dependable Systems and Networks", "DSN"),
    ("International Symposium on Software Testing and Analysis", "ISSTA"),
    ("International Conference on Software Analysis, Evolution and Reengineering", "SANER"),
    ("Symposium on Edge Computing", "SEC"),
    ("International Conference on Edge Computing", "EDGE"),
    # 常见出版商版权声明中的期刊名
    ("IEEE Transactions on Parallel and Distributed Systems", "TPDS"),
    ("IEEE Transactions on Computers", "TC"),
    ("IEEE Transactions on Knowledge and Data Engineering", "TKDE"),
    ("IEEE/ACM Transactions on Networking", "TON"),
    ("Proceedings of the VLDB Endowment", "VLDB"),
    ("ACM Computing Surveys", "CSUR"),
    ("ACM Transactions on", "ACM-T"),  # generic match for ACM Transactions
]


def extract_pdf_metadata(file_path: str) -> dict:
    """从 PDF 内部提取元数据（标题/作者/DOI/期刊等）"""
    result = {
        "embedded_title": "",
        "authors_text": "",
        "doi": "",
        "venue_from_text": "",
        "year_from_text": None,
    }
    if not HAS_PYMUPDF:
        return result

    doc = fitz.open(file_path)
    meta = doc.metadata

    # 基本元数据
    result["embedded_title"] = (meta.get("title") or "").strip()
    result["authors_text"] = (meta.get("author") or "").strip()

    # 尝试从 XMP 元数据中提取 DOI
    try:
        xmp = doc.xref_get_key(-1, "metadata")
        if xmp:
            doi_match = re.search(r'(?:doi|DOI)[\s:=]+(10\.\d{4,}/[^\s<"\']+)', str(xmp))
            if doi_match:
                result["doi"] = doi_match.group(1)
    except Exception:
        pass

    # 如果没有从 XMP 找到，尝试从第一页文本找 DOI
    if not result["doi"]:
        try:
            first_page_text = doc[0].get_text()
            doi_match = re.search(r'(?:doi|DOI)[\s:]*?(10\.\d{4,}/[^\s]+)', first_page_text)
            if doi_match:
                result["doi"] = doi_match.group(1)
        except Exception:
            pass

    # 从 DOI 提取年份 (如 ...63350.2024.00039 → 2024)
    if result["doi"] and not result["year_from_text"]:
        doi_year = re.search(r'[./]((?:19|20)\d{2})[./]', result["doi"])
        if doi_year:
            result["year_from_text"] = int(doi_year.group(1))

    # 从首页文本搜索期刊/会议全名
    try:
        text = doc[0].get_text()
        for full_name, abbrev in _JOURNAL_KEYWORDS:
            if full_name.lower() in text.lower():
                result["venue_from_text"] = abbrev
                break
        # 从文本中寻找年份（如 © 2024, Copyright 2023, 20XX IEEE/ACM）
        year_match = re.search(
            r'(?:©|Copyright|Published)\s*(\d{4})|'
            r'(?:19|20)\d{2}\s+(?:IEEE|ACM|Springer|Elsevier)',
            text
        )
        if year_match:
            y = year_match.group(1)
            if y:
                result["year_from_text"] = int(y)
    except Exception:
        pass

    doc.close()
    return result


def extract_text(file_path: str, pages: list[int] | None = None) -> str:
    """提取 PDF 文本（指定页或全部）"""
    return "\n\n".join(extract_page_texts(file_path, pages))


def extract_page_texts(file_path: str, pages: list[int] | None = None) -> list[str]:
    """保留真实页边界，页内空行不影响页面评分和渲染页码。"""
    if not HAS_PYMUPDF:
        return []
    doc = fitz.open(file_path)
    target = pages if pages else list(range(doc.page_count))
    texts = []
    for i in target:
        if 0 <= i < doc.page_count:
            texts.append(doc[i].get_text())
    doc.close()
    return texts


def render_page(file_path: str, page_num: int,
                max_width: int = 2048) -> bytes | None:
    """将指定页渲染为 JPEG 图片"""
    if not HAS_PYMUPDF:
        return None
    doc = fitz.open(file_path)
    if page_num < 0 or page_num >= doc.page_count:
        doc.close()
        return None
    page = doc[page_num]
    zoom = min(max_width / page.rect.width, 2.0)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = pix.tobytes("jpeg")
    doc.close()
    return img


def render_page_base64(file_path: str, page_num: int,
                       max_width: int = 2048) -> str | None:
    """将指定页渲染为 base64 JPEG"""
    import base64
    img = render_page(file_path, page_num, max_width)
    if img:
        return base64.b64encode(img).decode("ascii")
    return None
