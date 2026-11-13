"""递归监听论文目录；合并事件，等文件写入稳定后再同步。"""

import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from ..config import settings

logger = logging.getLogger(__name__)


class PaperWatcher:
    def __init__(self, callback, directory=None, debounce=0.8, rescan_interval=20.0):
        self.callback = callback
        self.directory = Path(directory or settings.papers_dir)
        self.debounce = debounce
        self.rescan_interval = rescan_interval
        self.observer = Observer()
        self._condition = threading.Condition()
        self._stopping = False
        self._deadline = 0.0
        self._worker = None
        self._status = {"syncing": False, "last_scan": None, "errors": []}

    def start(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(_PaperHandler(self.request_scan), str(self.directory), recursive=True)
        self.observer.start()
        self._worker = threading.Thread(target=self._run, name="paper-library-sync", daemon=True)
        self._worker.start()
        logger.info("文件监听已启动: %s", self.directory)

    def stop(self):
        with self._condition:
            self._stopping = True
            self._condition.notify_all()
        self.observer.stop()
        self.observer.join()
        if self._worker:
            self._worker.join()

    def request_scan(self):
        with self._condition:
            self._deadline = time.monotonic() + self.debounce
            self._condition.notify_all()

    def status(self):
        with self._condition:
            return {"running": self.observer.is_alive() and not self._stopping,
                    "directory": str(self.directory.resolve()), **self._status}

    def _run(self):
        while True:
            with self._condition:
                while not self._stopping and self._deadline > time.monotonic():
                    self._condition.wait(self._deadline - time.monotonic())
                if self._stopping:
                    return
                self._deadline = time.monotonic() + self.rescan_interval
                self._status = {**self._status, "syncing": True}
            try:
                result = self.callback()
                errors = result.get("errors", [])
            except Exception as exc:
                logger.exception("论文目录同步失败")
                errors = [str(exc)]
            with self._condition:
                self._status = {"syncing": False, "last_scan": datetime.now().isoformat(timespec="seconds"), "errors": errors}
                if errors:
                    self._deadline = min(self._deadline, time.monotonic() + 3.0)


class _PaperHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_any_event(self, event):
        if event.event_type not in {"created", "modified", "deleted", "moved", "closed"}:
            return
        paths = (event.src_path, getattr(event, "dest_path", ""))
        if event.is_directory or any(str(p).lower().endswith(".pdf") for p in paths):
            self.callback()
