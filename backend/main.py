from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .routers import papers, system, recycle, speedread

app = FastAPI(
    title="Thesis-Reader",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(recycle.router, prefix="/api")
app.include_router(speedread.router, prefix="/api")


@app.on_event("startup")
async def startup():
    init_db()
