from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from ..config import settings
import time
import logging

logger = logging.getLogger(__name__)


class PaperWatcher:
    def __init__(self, callback):
        self.callback = callback
        self.observer = Observer()
        self._debounce_timer: float = 0
        self._debounce_interval = 2.0  # 2 秒防抖

    def start(self):
        if not settings.papers_dir.exists():
            settings.papers_dir.mkdir(parents=True, exist_ok=True)

        handler = _PaperHandler(self._on_change)
        self.observer.schedule(handler, str(settings.papers_dir), recursive=True)
        self.observer.start()
        logger.info(f"文件监听已启动: {settings.papers_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("文件监听已停止")

    def _on_change(self, event_type: str, file_path: str):
        now = time.time()
        if now - self._debounce_timer < self._debounce_interval:
            return
        self._debounce_timer = now

        if file_path.lower().endswith('.pdf'):
            logger.info(f"文件变更: {event_type} - {file_path}")
            if self.callback:
                self.callback(event_type, file_path)


class _PaperHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory:
            self.callback("created", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.callback("modified", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.callback("deleted", event.src_path)
