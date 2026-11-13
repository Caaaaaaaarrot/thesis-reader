"""将受管理目录中的 PDF 与数据库对齐，不复制监听到的文件。"""

import hashlib
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..database import get_db
from ..models.paper import PaperResponse
from ..utils.pdf_utils import extract_pdf_metadata, get_pdf_info
from .indexer import infer_metadata


def _key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _inspect(path: Path) -> dict:
    before = path.stat()
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    info = get_pdf_info(str(path))
    if not info.get("page_count"):
        raise ValueError("PDF 尚未写入完成、已损坏或无法读取")
    meta = infer_metadata(path.name, extract_pdf_metadata(str(path)))
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("PDF 正在写入，稍后重试")
    return {
        "file_path": str(path.relative_to(settings.workspace_root.resolve())) if path.is_relative_to(settings.workspace_root.resolve()) else str(path),
        "content_hash": hasher.hexdigest(),
        "file_size": after.st_size,
        "file_mtime_ns": after.st_mtime_ns,
        "page_count": info["page_count"],
        "authors": info.get("author", ""),
        **meta,
    }


def _upsert(conn, entry: dict, row=None) -> str:
    if row is None:
        paper_id = uuid.uuid4().hex[:16]
        values = {"id": paper_id, "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"), **entry}
        conn.execute(
            f"INSERT INTO papers ({', '.join(values)}) VALUES ({', '.join('?' for _ in values)})",
            tuple(values.values()),
        )
        return paper_id

    # 内容变了，旧摘要不再适用于新 PDF；重命名不影响摘要和笔记。
    if row["content_hash"] and row["content_hash"] != entry["content_hash"]:
        conn.execute("DELETE FROM speed_reads WHERE paper_id = ?", (row["id"],))
    updates = {k: entry[k] for k in ("file_path", "content_hash", "file_size", "file_mtime_ns", "page_count")}
    updates["file_missing"] = 0
    for key in ("title", "authors", "venue", "year"):
        if not row[key] and entry.get(key):
            updates[key] = entry[key]
    if any(row[k] != v for k, v in updates.items()):
        conn.execute(
            f"UPDATE papers SET {', '.join(k + ' = ?' for k in updates)}, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (*updates.values(), row["id"]),
        )
    return row["id"]


def sync_library() -> dict:
    root = settings.papers_dir.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"论文目录不可用：{root}")
    paths = {}

    def scan_error(error):
        raise error  # 扫描不完整时绝不把未扫描到的论文标成已移除。

    for directory, _, filenames in os.walk(root, onerror=scan_error, followlinks=False):
        for filename in filenames:
            path = Path(directory) / filename
            if path.suffix.lower() == ".pdf" and not path.is_symlink():
                paths[_key(path)] = path
    conn = get_db()
    try:
        known = {_key(settings.workspace_root / r["file_path"]): dict(r)
                 for r in conn.execute("SELECT * FROM papers")}
    finally:
        conn.close()

    entries, errors = {}, []
    for key, path in paths.items():
        try:
            stat = path.stat()
            row = known.get(key)
            if row and row["content_hash"] and (stat.st_size, stat.st_mtime_ns) == (row["file_size"], row["file_mtime_ns"]):
                entries[key] = {k: row[k] for k in (
                    "file_path", "content_hash", "file_size", "file_mtime_ns", "page_count", "title", "authors", "venue", "year")}
            else:
                entries[key] = _inspect(path)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")

    conn = get_db()
    added = moved = removed = 0
    try:
        # 开发环境可能有两个后端进程，SQLite 写事务保证不会重复建档。
        conn.execute("BEGIN IMMEDIATE")
        rows = [dict(r) for r in conn.execute("SELECT * FROM papers")]
        by_path = {_key(settings.workspace_root / r["file_path"]): r for r in rows}
        assigned = set()
        for key, entry in entries.items():
            if not paths[key].exists():
                continue
            row = by_path.get(key)
            if row is None:
                # 移动/重命名按内容识别，保留 ID、标签、笔记和速读。
                row = next((r for r in rows if r["content_hash"] == entry["content_hash"]
                            and _key(settings.workspace_root / r["file_path"]) not in paths
                            and r["id"] not in assigned), None)
                if row:
                    moved += 1
                else:
                    added += 1
            assigned.add(_upsert(conn, entry, row))
        for row in rows:
            if row["id"] not in assigned and _key(settings.workspace_root / row["file_path"]) not in paths and not row["file_missing"]:
                # 外部移除仅隐藏，文件重新出现时可找回原来的笔记。
                conn.execute("UPDATE papers SET file_missing = 1 WHERE id = ?", (row["id"],))
                removed += 1
        conn.commit()
    finally:
        conn.close()
    return {"added": added, "moved": moved, "removed": removed, "errors": errors}


def import_file(file_path: str) -> PaperResponse:
    src = Path(file_path).resolve()
    if src.suffix.lower() != ".pdf":
        raise ValueError("仅支持 PDF 文件")
    entry = _inspect(src)
    conn = get_db()
    copied = None
    temporary = None
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = [dict(r) for r in conn.execute("SELECT * FROM papers")]
        internal = src.is_relative_to(settings.papers_dir.resolve())
        row = next((r for r in rows if _key(settings.workspace_root / r["file_path"]) == _key(src)), None)
        if not internal and row is None:
            row = next((r for r in rows if r["content_hash"] == entry["content_hash"]
                        and not r["file_missing"] and (settings.workspace_root / r["file_path"]).exists()), None)
            if row:
                return _response(conn, row["id"])
        if row is None:
            row = next((r for r in rows if r["content_hash"] == entry["content_hash"]
                        and not (settings.workspace_root / r["file_path"]).exists()), None)
        if internal:
            dest = src
        else:
            dest = settings.papers_dir / src.name
            counter = 1
            while dest.exists():
                dest = settings.papers_dir / f"{src.stem}_{counter}{src.suffix}"
                counter += 1
            temporary = dest.with_name(f".{dest.name}.{uuid.uuid4().hex}.importing")
            shutil.copy2(src, temporary)
            stat = src.stat()
            if (stat.st_size, stat.st_mtime_ns) != (entry["file_size"], entry["file_mtime_ns"]):
                raise ValueError("PDF 在导入过程中发生变化，请重试")
            os.replace(temporary, dest)
            copied = dest
        entry["file_path"] = str(dest.relative_to(settings.workspace_root.resolve()))
        entry["file_mtime_ns"] = dest.stat().st_mtime_ns
        paper_id = _upsert(conn, entry, row)
        conn.commit()
        copied = None
        return _response(conn, paper_id)
    except Exception:
        conn.rollback()
        if copied:
            copied.unlink(missing_ok=True)
        raise
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
        conn.close()


def _response(conn, paper_id: str) -> PaperResponse:
    row = dict(conn.execute(
        "SELECT p.*, s.* FROM papers p LEFT JOIN speed_reads s ON p.id = s.paper_id WHERE p.id = ?", (paper_id,)
    ).fetchone())
    return PaperResponse.from_row(row, row)
