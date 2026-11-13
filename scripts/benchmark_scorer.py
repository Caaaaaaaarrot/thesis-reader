"""Compare the same page-scoring workload with and without the native module."""

from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.services.native_scorer import native_status
from backend.services.page_scorer import score_pages
from backend.utils.pdf_utils import extract_page_texts

if native_status()["engine"] != "cpp":
    raise SystemExit("Build the native module first: npm run native:build")
paper = next((Path(__file__).resolve().parent.parent / "papers").rglob("*.pdf"), None)
if paper:
    pages = extract_page_texts(str(paper))
else:
    pages = [("Framework architecture training experiment ablation 图 表 分析\n" * 100)]
pages = (pages * (100 // len(pages) + 1))[:100]

def measure():
    timings = []
    for _ in range(7):
        start = time.perf_counter()
        score_pages(pages)
        timings.append(time.perf_counter() - start)
    return statistics.median(timings)

native_result = score_pages(pages)
native = measure()
with patch('backend.services.page_scorer.count_keywords', return_value=None):
    assert native_result == score_pages(pages), "Scoring results differ"
    python = measure()
print(f"100 pages, {sum(len(p) for p in pages):,} characters, median of 7 runs")
print(f"Python: {python * 1000:.2f} ms | C++: {native * 1000:.2f} ms | Ratio: {python / native:.2f}x")
print("This measures page scoring only, excluding PDF extraction, rendering, and model latency.")
