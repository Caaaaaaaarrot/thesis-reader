"""AI 速读 API — SSE 流式返回"""

import json
import asyncio
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from ..database import get_db
from ..services.speedread_pipeline import run_speedread, _get_cached, _mark_read

router = APIRouter(tags=["speedread"])


@router.get("/speedread/{paper_id}")
async def get_speedread(paper_id: str):
    """获取已缓存的速读结果"""
    result = _get_cached(paper_id)
    if result:
        _mark_read(paper_id)
    else:
        # 检查是否正在生成
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT status, error_message FROM speed_reads WHERE paper_id = ?",
                (paper_id,)
            ).fetchone()
            if row and row["status"] == "running":
                return {"status": "running"}
            if row and row["status"] == "error":
                return {"status": "error", "error_message": row["error_message"]}
        finally:
            conn.close()
        raise HTTPException(status_code=404, detail="未找到速读结果，请先生成")
    return {"status": "success", "result": result}


@router.post("/speedread/{paper_id}")
async def generate_speedread(
    paper_id: str,
    request: Request,
    force: bool = Query(default=False, description="强制重新生成"),
    max_images: int = Query(default=4, ge=1, le=8, description="最大图片数"),
):
    """生成 AI 速读，SSE 流式返回进度和结果"""
    # 读取请求体中的 AI 配置
    ai_config = None
    try:
        body = await request.json()
        ai_config = {
            "endpoint": body.get("endpoint", ""),
            "api_key": body.get("api_key", "") or body.get("apiKey", ""),
            "model": body.get("model", ""),
        }
    except Exception:
        pass

    # 验证论文存在
    conn = get_db()
    try:
        paper = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if not paper:
            raise HTTPException(status_code=404, detail="论文不存在")
    finally:
        conn.close()

    async def event_stream():
        try:
            async for event in run_speedread(paper_id, force, max_images, ai_config):
                data = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {event['event']}\ndata: {data}\n\n"
                await asyncio.sleep(0)  # 让出控制权
        except Exception as e:
            yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
