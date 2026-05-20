from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/ping")
async def ping():
    return {"status": "ok", "version": "0.1.0"}
