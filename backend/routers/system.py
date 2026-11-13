from fastapi import APIRouter, Request
from ..database import get_db
from ..services.native_scorer import native_status

router = APIRouter(tags=["system"])


@router.get("/ping")
async def ping():
    return {"status": "ok", "version": "0.1.0"}


@router.get("/library/status")
def library_status(request: Request):
    conn = get_db()
    try:
        revision = conn.execute("SELECT revision FROM library_state WHERE id = 1").fetchone()[0]
        count = conn.execute("SELECT COUNT(*) FROM papers WHERE file_missing = 0").fetchone()[0]
    finally:
        conn.close()
    return {**request.app.state.paper_watcher.status(), "revision": revision,
            "paper_count": count, "scorer": native_status()}


@router.post("/library/rescan")
def rescan_library(request: Request):
    request.app.state.paper_watcher.request_scan()
    return {"status": "scheduled"}
