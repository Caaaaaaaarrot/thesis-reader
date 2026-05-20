import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    # 路径
    workspace_root: Path = field(default_factory=lambda: Path(os.getenv(
        "THESIS_READER_ROOT",
        Path(__file__).resolve().parent.parent
    )))
    papers_dir: Path = field(default=None)
    database_path: Path = field(default=None)
    cache_dir: Path = field(default=None)
    recycle_dir: Path = field(default=None)

    # 服务
    host: str = "127.0.0.1"
    port: int = 0
    debug: bool = True

    # AI
    ai_endpoint: str = ""
    ai_api_key: str = ""
    ai_model: str = "gpt-4o"
    ai_max_tokens: int = 4096
    max_image_pages: int = 4
    max_source_chars: int = 24000

    def __post_init__(self):
        if self.papers_dir is None:
            self.papers_dir = self.workspace_root / "papers"
        if self.database_path is None:
            self.database_path = self.workspace_root / "data" / "thesis-reader.db"
        if self.cache_dir is None:
            self.cache_dir = self.workspace_root / "data" / "cache"
        if self.recycle_dir is None:
            self.recycle_dir = self.workspace_root / "data" / "recycle"

    def ensure_dirs(self):
        for d in [self.papers_dir, self.database_path.parent,
                  self.cache_dir, self.recycle_dir]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
