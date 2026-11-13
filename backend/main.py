from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database import init_db
from .routers import papers, system, recycle, speedread
from .services.file_watcher import PaperWatcher
from .services.library_index import sync_library


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    watcher = PaperWatcher(sync_library)
    app.state.paper_watcher = watcher
    watcher.start()
    try:
        yield
    finally:
        watcher.stop()


app = FastAPI(
    title="Thesis-Reader",
    version="0.1.0",
    docs_url="/api/docs" if settings.debug else None,
    redoc_url=None,
    lifespan=lifespan,
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
