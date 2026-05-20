"""PyMuPDF 封装的 PDF 工具函数"""

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


def extract_text(file_path: str, pages: list[int] | None = None) -> str:
    """提取 PDF 文本（指定页或全部）"""
    if not HAS_PYMUPDF:
        return ""
    doc = fitz.open(file_path)
    target = pages if pages else list(range(doc.page_count))
    texts = []
    for i in target:
        if 0 <= i < doc.page_count:
            texts.append(doc[i].get_text())
    doc.close()
    return "\n\n".join(texts)


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
