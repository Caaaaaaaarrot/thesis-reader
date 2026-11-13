"""C ABI + ctypes：无需 Python 开发头文件，缺少编译产物时回退 Python。"""

import ctypes
import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)
_load_error = ""


def library_path() -> Path:
    suffix = ".dll" if sys.platform == "win32" else ".dylib" if sys.platform == "darwin" else ".so"
    return Path(__file__).resolve().parent.parent / "native" / f"thesis_scorer{suffix}"


@lru_cache(maxsize=1)
def _load():
    global _load_error
    _load_error = ""
    if os.getenv("THESIS_READER_NATIVE", "1") == "0":
        _load_error = "已通过环境变量关闭"
        return None
    try:
        lib = ctypes.CDLL(str(library_path()))
        lib.tr_abi_version.argtypes = []
        lib.tr_abi_version.restype = ctypes.c_int
        if lib.tr_abi_version() != 1:
            raise OSError("C++ 模块接口版本不匹配，请重新编译")
        strings = ctypes.POINTER(ctypes.c_char_p)
        lengths = ctypes.POINTER(ctypes.c_size_t)
        lib.tr_create_matcher.argtypes = [strings, lengths, ctypes.c_size_t]
        lib.tr_create_matcher.restype = ctypes.c_void_p
        lib.tr_count_keywords.argtypes = [ctypes.c_void_p, strings, lengths, ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint64)]
        lib.tr_count_keywords.restype = ctypes.c_int
        lib.tr_destroy_matcher.argtypes = [ctypes.c_void_p]
        lib.tr_destroy_matcher.restype = None
        return lib
    except (OSError, AttributeError) as exc:
        _load_error = str(exc)
        logger.info("页面评分使用 Python：%s", exc)
        return None


class _Matcher:
    def __init__(self, keywords):
        self.lib = _load()
        encoded = [k.encode("utf-8") for k in keywords]
        self.handle = self.lib.tr_create_matcher(
            (ctypes.c_char_p * len(encoded))(*encoded),
            (ctypes.c_size_t * len(encoded))(*(len(k) for k in encoded)), len(encoded))
        if not self.handle:
            raise RuntimeError("C++ 关键词索引初始化失败")

    def __del__(self):
        if getattr(self, "handle", None):
            self.lib.tr_destroy_matcher(self.handle)


@lru_cache(maxsize=8)
def _matcher(keywords: tuple[str, ...]):
    return _Matcher(keywords)


def count_keywords(texts: list[str], keywords: list[str]) -> list[list[int]] | None:
    if not texts:
        return []
    if not keywords:
        return [[] for _ in texts]
    if not _load() or any(not k for k in keywords):
        return None
    try:
        matcher = _matcher(tuple(keywords))
        encoded = [t.encode("utf-8") for t in texts]
        output = (ctypes.c_uint64 * (len(texts) * len(keywords)))()
        status = matcher.lib.tr_count_keywords(
            matcher.handle, (ctypes.c_char_p * len(encoded))(*encoded),
            (ctypes.c_size_t * len(encoded))(*(len(t) for t in encoded)), len(encoded), output)
        if status != 0:
            raise RuntimeError("C++ 页面评分失败")
        width = len(keywords)
        return [list(output[i * width:(i + 1) * width]) for i in range(len(texts))]
    except (OSError, RuntimeError, ValueError) as exc:
        logger.warning("C++ 页面评分回退 Python：%s", exc)
        return None


def native_status() -> dict:
    return {"engine": "cpp" if _load() else "python", "available": bool(_load()), "reason": _load_error}
