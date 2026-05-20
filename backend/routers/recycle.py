from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..config import settings
import json
import shutil
import os

router = APIRouter(tags=["recycle"])


@router.get("/recycle")
async def list_recycle():
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM recycle_bin ORDER BY deleted_at DESC")
        rows = cur.fetchall()
        result = []
        for r in rows:
            meta = json.loads(r["metadata_json"])
            result.append({
                "id": r["id"],
                "title": meta.get("title", ""),
                "venue": meta.get("venue", ""),
                "year": meta.get("year"),
                "deleted_at": r["deleted_at"],
            })
        return result
    finally:
        conn.close()


@router.post("/recycle/{recycle_id}/restore")
async def restore_paper(recycle_id: str):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM recycle_bin WHERE id = ?", (recycle_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="回收站条目不存在")

        meta = json.loads(row["metadata_json"])
        paper_id = recycle_id.replace("recycle_", "")

        # 恢复文件
        recycle_path = settings.recycle_dir / recycle_id
        papers_path = settings.papers_dir
        info_file = recycle_path / "info.json"
        if info_file.exists():
            for f in recycle_path.iterdir():
                if f.suffix.lower() == '.pdf':
                    dest = papers_path / f.name
                    shutil.move(str(f), str(dest))
                    meta["file_path"] = str(dest.relative_to(settings.workspace_root))

        # 恢复数据库记录
        tags = meta.get("tags", [])
        if isinstance(tags, list):
            tags = json.dumps(tags, ensure_ascii=False)
        conn.execute(
            """INSERT OR REPLACE INTO papers (id, file_path, title, authors, year, venue, tags, read, note, bibtex, date_added, page_count, file_size)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (paper_id, meta["file_path"], meta.get("title", ""), meta.get("authors", ""),
             meta.get("year"), meta.get("venue", ""), tags,
             meta.get("read", 0), meta.get("note", ""), meta.get("bibtex", ""),
             meta.get("date_added", ""), meta.get("page_count", 0), meta.get("file_size", 0))
        )
        conn.execute("DELETE FROM recycle_bin WHERE id = ?", (recycle_id,))
        conn.commit()

        # 清理回收站目录
        if recycle_path.exists():
            shutil.rmtree(recycle_path)

        return {"status": "ok"}
    finally:
        conn.close()


@router.post("/recycle/clear")
async def clear_recycle():
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM recycle_bin")
        ids = [r["id"] for r in cur.fetchall()]
        conn.execute("DELETE FROM recycle_bin")
        conn.commit()

        for rid in ids:
            rp = settings.recycle_dir / rid
            if rp.exists():
                shutil.rmtree(rp)

        return {"status": "ok", "cleared": len(ids)}
    finally:
        conn.close()
