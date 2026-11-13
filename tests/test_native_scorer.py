from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import fitz

from backend.services import native_scorer
from backend.services.page_scorer import BOOST_KEYWORDS, ROLE_KEYWORDS, score_pages, select_pages
from backend.utils.pdf_utils import extract_page_texts


class NativeScorerTests(unittest.TestCase):
    def test_native_counts_match_python_for_unicode_and_overlap(self):
        if not native_scorer.native_status()["available"]:
            self.skipTest("Run npm run native:build to validate the C++ implementation")
        rng = random.Random(42)
        patterns = ["a", "aa", "aaa", "分析", "消融", "图", "图表", "framework", "\x00a", "é", "😀"]
        texts = ["", "aaaaaa", "分析分析图表消融", "framework\x00a framework", "é😀é"]
        texts += [''.join(rng.choices(patterns + [' ', '\n', 'other'], k=200)) for _ in range(100)]
        expected = [[text.count(pattern) for pattern in patterns] for text in texts]
        self.assertEqual(native_scorer.count_keywords(texts, patterns), expected)

    def test_role_scores_and_selection_match_python_fallback(self):
        if not native_scorer.native_status()["available"]:
            self.skipTest("C++ module not built")
        texts = ["", "   ", "Framework architecture 图表", "Experiment result ablation table", "算法 训练 损失函数 分析 消融实验", "Training optimization algorithm"]
        native = score_pages(texts)
        selected = select_pages(texts)
        with patch('backend.services.page_scorer.count_keywords', return_value=None):
            self.assertEqual(native, score_pages(texts))
            self.assertEqual(selected, select_pages(texts))
        # 独立核对权重、重复次数和 boost，而非只比较两个调用结果。
        for text, result in zip(texts, native):
            for role, config in ROLE_KEYWORDS.items():
                expected = sum(text.lower().count(kw.lower()) * config["weight"] for kw in config["keywords"])
                self.assertAlmostEqual(result["roles"][role], expected)
            self.assertEqual(result["boost"], sum(kw.lower() in text.lower() for kw in BOOST_KEYWORDS))

    def test_native_matcher_is_thread_safe(self):
        if not native_scorer.native_status()["available"]:
            self.skipTest("C++ module not built")
        def count(i):
            return native_scorer.count_keywords(["分析 " * i], ["分析"])
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(count, range(1, 20))), [[[i]] for i in range(1, 20)])

    def test_missing_library_falls_back(self):
        native_scorer._load.cache_clear()
        try:
            with patch('backend.services.native_scorer.ctypes.CDLL', side_effect=OSError("test missing library")):
                self.assertEqual(native_scorer.native_status()["engine"], "python")
                self.assertEqual(select_pages(["experiment", "framework"])[0]["page_num"], 1)
        finally:
            native_scorer._load.cache_clear()

    def test_pdf_page_boundaries_survive_blank_lines(self):
        scratch = Path(__file__).resolve().parent.parent / "data" / "test-workspaces"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="thesis-page-test-", dir=scratch) as directory:
            path = Path(directory) / "pages.pdf"
            with fitz.open() as doc:
                first = doc.new_page()
                first.insert_text((72, 72), "First paragraph")
                first.insert_text((72, 180), "Second paragraph")
                doc.new_page().insert_text((72, 72), "Second page experiments")
                doc.save(path)
            pages = extract_page_texts(str(path))
            self.assertEqual(len(pages), 2)
            self.assertIn("Second paragraph", pages[0])
            self.assertIn("Second page", pages[1])
        self.assertEqual(select_pages(["", "  "]), [])
        self.assertEqual(select_pages(["framework"], max_pages=0), [])
