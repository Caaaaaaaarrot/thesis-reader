import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import tempfile
import time
import unittest

import fitz
from fastapi.testclient import TestClient

from backend.config import settings
from backend.database import SCHEMA, get_db, init_db
from backend.main import app
from backend.services.file_watcher import PaperWatcher
from backend.services.indexer import import_paper
from backend.services.library_index import sync_library


class LibraryTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parent.parent / "data" / "test-workspaces"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="thesis-reader-test-", dir=scratch)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.saved = {k: getattr(settings, k) for k in ("workspace_root", "papers_dir", "database_path", "cache_dir", "recycle_dir")}
        self.addCleanup(self.restore_settings)
        settings.workspace_root = self.root
        settings.papers_dir = self.root / "papers"
        settings.database_path = self.root / "data" / "test.db"
        settings.cache_dir = self.root / "data" / "cache"
        settings.recycle_dir = self.root / "data" / "recycle"
        settings.ensure_dirs()
        init_db()

    def restore_settings(self):
        for key, value in self.saved.items():
            setattr(settings, key, value)

    def pdf(self, name="paper.pdf", text="framework experiment", internal=True):
        path = (settings.papers_dir if internal else self.root / "external") / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((72, 72), text)
            doc.set_metadata({"title": "Original title", "author": "Author"})
            doc.save(path)
        return path

    def rows(self, active=False):
        conn = get_db()
        try:
            return [dict(r) for r in conn.execute("SELECT * FROM papers" + (" WHERE file_missing = 0" if active else ""))]
        finally:
            conn.close()

    def annotate(self, paper_id):
        conn = get_db()
        try:
            conn.execute("UPDATE papers SET title = 'My title', note = 'Keep my note', tags = ? WHERE id = ?", (json.dumps(["my-tag"]), paper_id))
            conn.execute("INSERT INTO speed_reads (paper_id, status, one_sentence) VALUES (?, 'success', 'Cached summary')", (paper_id,))
            conn.commit()
        finally:
            conn.close()

    def test_initial_scan_and_repeated_scan_are_idempotent(self):
        self.pdf("nested/test.PDF")
        self.assertEqual(sync_library()["added"], 1)
        row = self.rows()[0]
        self.assertEqual(row["page_count"], 1)
        self.assertEqual(len(row["content_hash"]), 64)
        self.annotate(row["id"])
        self.assertEqual(sync_library()["added"], 0)
        self.assertEqual(self.rows()[0]["note"], "Keep my note")

    def test_manual_import_does_not_duplicate_watched_file(self):
        path = self.pdf()
        paper = import_paper(str(path))
        sync_library()
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["id"], paper.id)
        self.assertEqual(len(list(settings.papers_dir.glob("*.pdf"))), 1)

    def test_external_import_is_atomic_and_deduplicated(self):
        path = self.pdf(internal=False)
        paper = import_paper(str(path))
        self.annotate(paper.id)
        second = path.with_name("same-content.pdf")
        shutil.copy2(path, second)
        self.assertEqual(import_paper(str(second)).id, paper.id)
        sync_library()
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0]["note"], "Keep my note")

    def test_different_content_with_same_name_coexists(self):
        self.pdf()
        sync_library()
        external = self.pdf(text="different paper", internal=False)
        import_paper(str(external))
        sync_library()
        self.assertEqual(len(self.rows(active=True)), 2)

    def test_rename_keeps_id_notes_and_speedread(self):
        path = self.pdf()
        sync_library()
        paper_id = self.rows()[0]["id"]
        self.annotate(paper_id)
        folder = settings.papers_dir / "renamed-folder"
        folder.mkdir()
        path.rename(folder / "renamed.pdf")
        self.assertEqual(sync_library()["moved"], 1)
        row = self.rows()[0]
        self.assertEqual(row["id"], paper_id)
        self.assertEqual(row["title"], "My title")
        self.assertEqual(row["note"], "Keep my note")
        conn = get_db()
        try:
            self.assertEqual(conn.execute("SELECT one_sentence FROM speed_reads").fetchone()[0], "Cached summary")
        finally:
            conn.close()

    def test_external_removal_and_return_preserve_metadata(self):
        path = self.pdf()
        payload = path.read_bytes()
        sync_library()
        paper_id = self.rows()[0]["id"]
        self.annotate(paper_id)
        path.unlink()
        self.assertEqual(sync_library()["removed"], 1)
        self.assertEqual(self.rows(active=True), [])
        (settings.papers_dir / "returned.pdf").write_bytes(payload)
        sync_library()
        self.assertEqual(self.rows(active=True)[0]["id"], paper_id)
        self.assertEqual(self.rows(active=True)[0]["note"], "Keep my note")

    def test_content_change_invalidates_only_cached_speedread(self):
        path = self.pdf()
        sync_library()
        self.annotate(self.rows()[0]["id"])
        path.unlink()
        self.pdf(text="new content and results")
        sync_library()
        self.assertEqual(self.rows()[0]["title"], "My title")
        self.assertEqual(self.rows()[0]["note"], "Keep my note")
        conn = get_db()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM speed_reads").fetchone()[0], 0)
        finally:
            conn.close()

    def test_partial_file_is_retried_without_ghost_row(self):
        path = settings.papers_dir / "paper.pdf"
        path.write_bytes(b"%PDF-1.7 incomplete")
        self.assertTrue(sync_library()["errors"])
        self.assertEqual(self.rows(), [])
        path.unlink()
        self.pdf()
        self.assertFalse(sync_library()["errors"])
        self.assertEqual(len(self.rows()), 1)

    def test_concurrent_scanners_do_not_create_duplicates(self):
        self.pdf()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: sync_library(), range(2)))
        self.assertEqual(len(self.rows()), 1)

    def test_migration_preserves_existing_ids(self):
        settings.database_path = self.root / "data" / "legacy.db"
        conn = get_db()
        try:
            conn.executescript(SCHEMA)
            conn.execute("INSERT INTO papers (id, file_path, note) VALUES ('legacy', 'papers/paper.pdf', 'Old note')")
            conn.commit()
        finally:
            conn.close()
        self.pdf()
        init_db()
        sync_library()
        self.assertEqual(self.rows()[0]["id"], "legacy")
        self.assertEqual(self.rows()[0]["note"], "Old note")

    def test_delete_does_not_get_reimported_by_scanner(self):
        self.pdf()
        sync_library()
        with TestClient(app) as client:
            paper_id = self.rows()[0]["id"]
            client.delete(f"/api/papers/{paper_id}").raise_for_status()
            sync_library()
            self.assertEqual(self.rows(), [])
            recycled = client.get('/api/recycle').json()
            self.assertEqual(len(recycled), 1)
            client.post(f"/api/recycle/{recycled[0]['id']}/restore").raise_for_status()
            sync_library()
            self.assertEqual(len(self.rows(active=True)), 1)
            self.assertEqual(self.rows()[0]["id"], paper_id)

    def test_real_watchdog_burst_rename_delete_and_shutdown(self):
        watcher = PaperWatcher(sync_library, debounce=0.1, rescan_interval=0.4)
        watcher.start()
        try:
            for i in range(4):
                self.pdf(f"subfolder/paper-{i}.pdf", text=f"paper number {i}")
            self.wait_until(lambda: len(self.rows(active=True)) == 4)
            original = self.rows(active=True)[0]
            path = settings.workspace_root / original["file_path"]
            dest = path.with_name("changed-name.pdf")
            path.rename(dest)
            self.wait_until(lambda: any(r["id"] == original["id"] and r["file_path"].endswith("changed-name.pdf") for r in self.rows()))
            dest.unlink()
            self.wait_until(lambda: len(self.rows(active=True)) == 3)
            self.assertTrue(watcher.status()["running"])
        finally:
            watcher.stop()
        self.assertFalse(watcher.status()["running"])

    def test_api_status_revision_and_removed_files(self):
        self.pdf()
        with TestClient(app) as client:
            self.wait_until(lambda: len(self.rows(active=True)) == 1)
            first = client.get("/api/library/status").json()
            self.assertTrue(first["running"])
            self.assertEqual(first["paper_count"], 1)
            row = self.rows()[0]
            client.put(f"/api/papers/{row['id']}", json={"note": "Changed"}).raise_for_status()
            second = client.get("/api/library/status").json()
            self.assertGreater(second["revision"], first["revision"])
            self.assertEqual(client.post("/api/library/rescan").status_code, 200)
            (settings.workspace_root / row["file_path"]).unlink()
            self.wait_until(lambda: not self.rows(active=True))
            self.assertEqual(client.get("/api/papers").json(), [])
            self.assertEqual(client.get("/api/venues").json(), [])

    def wait_until(self, predicate):
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.04)
        self.fail("等待目录同步超时")
