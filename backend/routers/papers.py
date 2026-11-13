from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from ..models.paper import PaperResponse, PaperUpdate, PaperCreate
from ..services.indexer import import_paper, infer_metadata
from ..utils.pdf_utils import extract_pdf_metadata
from pathlib import Path
from ..config import settings
import json
import os

router = APIRouter(tags=["papers"])


@router.get("/papers", response_model=list[PaperResponse])
async def list_papers(
    search: str = Query(default="", description="搜索关键词"),
    venue: str = Query(default="", description="会议筛选"),
    tag: str = Query(default="", description="标签筛选"),
    read: str = Query(default="all", description="已读筛选: all/read/unread"),
    sort: str = Query(default="date_added", description="排序字段"),
    order: str = Query(default="desc", description="升序/降序"),
):
    conn = get_db()
    try:
        query = "SELECT p.*, s.* FROM papers p LEFT JOIN speed_reads s ON p.id = s.paper_id WHERE p.file_missing = 0"
        params: list = []

        if search:
            query += " AND p.rowid IN (SELECT rowid FROM papers_fts WHERE papers_fts MATCH ?)"
            params.append(search)

        if venue:
            query += " AND p.venue = ?"
            params.append(venue)

        if tag:
            query += " AND p.tags LIKE ?"
            params.append(f'%"{tag}"%')

        if read == "read":
            query += " AND p.read = 1"
        elif read == "unread":
            query += " AND p.read = 0"

        allowed_sort = {"date_added": "p.date_added", "year": "p.year",
                        "title": "p.title", "venue": "p.venue"}
        sort_col = allowed_sort.get(sort, "p.date_added")
        sort_order = "DESC" if order == "desc" else "ASC"
        query += f" ORDER BY {sort_col} {sort_order}"

        cur = conn.execute(query, params)
        rows = cur.fetchall()
        return [PaperResponse.from_row(dict(r), dict(r)) for r in rows]
    finally:
        conn.close()


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str):
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT p.*, s.* FROM papers p LEFT JOIN speed_reads s ON p.id = s.paper_id WHERE p.id = ?",
            (paper_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="论文不存在")
        d = dict(row)
        return PaperResponse.from_row(d, d)
    finally:
        conn.close()


@router.post("/papers/import", response_model=PaperResponse)
async def import_pdf(req: PaperCreate):
    file_path = req.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文件不存在")
    if not file_path.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    try:
        paper = import_paper(file_path)
        return paper
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.put("/papers/{paper_id}", response_model=PaperResponse)
async def update_paper(paper_id: str, update: PaperUpdate):
    conn = get_db()
    try:
        # 检查论文存在
        cur = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="论文不存在")

        # 构建更新
        updates = {}
        if update.title is not None:
            updates["title"] = update.title
        if update.authors is not None:
            updates["authors"] = update.authors
        if update.year is not None:
            updates["year"] = update.year
        if update.venue is not None:
            updates["venue"] = update.venue
        if update.tags is not None:
            updates["tags"] = json.dumps(update.tags, ensure_ascii=False)
        if update.read is not None:
            updates["read"] = 1 if update.read else 0
        if update.note is not None:
            updates["note"] = update.note
        if update.bibtex is not None:
            updates["bibtex"] = update.bibtex

        if updates:
            updates["updated_at"] = "datetime('now', 'localtime')"
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [paper_id]
            conn.execute(f"UPDATE papers SET {set_clause} WHERE id = ?", values)
            conn.commit()

        # 返回更新后的
        cur = conn.execute(
            "SELECT p.*, s.* FROM papers p LEFT JOIN speed_reads s ON p.id = s.paper_id WHERE p.id = ?",
            (paper_id,)
        )
        d = dict(cur.fetchone())
        return PaperResponse.from_row(d, d)
    finally:
        conn.close()


@router.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="论文不存在")

        paper = dict(row)

        # 移入回收站
        recycle_id = f"recycle_{paper_id}"
        conn.execute(
            "INSERT OR REPLACE INTO recycle_bin (id, original_path, metadata_json) VALUES (?, ?, ?)",
            (recycle_id, paper["file_path"], json.dumps(paper, ensure_ascii=False))
        )

        # 删除论文（CASCADE 会删除关联的 speed_read）
        conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))

        # 回收站里移动物理文件
        recycle_path = settings.recycle_dir / recycle_id
        recycle_path.mkdir(parents=True, exist_ok=True)
        src = settings.workspace_root / paper["file_path"]
        if src.exists():
            import shutil
            shutil.move(str(src), str(recycle_path / src.name))
            # 保存信息
            (recycle_path / "info.json").write_text(
                json.dumps(paper, ensure_ascii=False, indent=2)
            )

        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@router.post("/papers/{paper_id}/reindex")
async def reindex_paper(paper_id: str):
    """从文件名重新推断元数据（venue/year/title）"""
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="论文不存在")

        paper = dict(row)
        file_path = str(settings.workspace_root / paper["file_path"])
        pdf_meta = {}
        try:
            pdf_meta = extract_pdf_metadata(file_path)
        except Exception:
            pass
        meta = infer_metadata(Path(paper["file_path"]).name, pdf_meta)
        conn.execute(
            "UPDATE papers SET venue = ?, year = ?, title = ? WHERE id = ?",
            (meta["venue"], meta["year"], meta["title"], paper_id)
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


@router.get("/venues")
async def list_venues():
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT venue, COUNT(*) as count FROM papers WHERE venue != '' AND file_missing = 0 GROUP BY venue ORDER BY count DESC"
        )
        return [{"name": r["venue"], "count": r["count"]} for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/tags")
async def list_tags():
    conn = get_db()
    try:
        cur = conn.execute("SELECT tags FROM papers WHERE file_missing = 0")
        tag_counts: dict[str, int] = {}
        for row in cur.fetchall():
            tags = json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"]
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        return [{"name": k, "count": v} for k, v in
                sorted(tag_counts.items(), key=lambda x: -x[1])]
    finally:
        conn.close()
