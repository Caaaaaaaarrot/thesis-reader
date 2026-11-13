"""AI 速读管道 — 文本提取 → 页面评分 → LLM 调用 → 结果持久化"""

import json
import asyncio
from pathlib import Path
from ..database import get_db
from ..config import settings
from ..utils.pdf_utils import extract_page_texts, render_page_base64, extract_pdf_metadata
from .indexer import infer_metadata
from .page_scorer import select_pages

SPEEDREAD_PROMPT = """你是一位资深的学术论文审稿人。请仔细阅读以下论文内容，给出结构化的深度解读。

## 输出格式要求
请严格用 JSON 格式输出，不要添加任何额外的解释文字。JSON 结构如下：

```json
{
  "one_sentence": "一句话概括（中文，不超过80字）",
  "quick_takeaways": ["关键发现1", "关键发现2", "关键发现3"],
  "problem_and_motivation": "论文要解决什么问题？为什么这个问题重要？（中文，150字以内）",
  "method_overview": "核心方法是什么？用通俗语言解释（中文，200字以内）",
  "method_steps": ["步骤1：...", "步骤2：...", "步骤3：..."],
  "core_figures": [
    {
      "page_number": 0,
      "caption": "图表标题（根据上下文推测）",
      "what_to_look": "这张图中应该关注什么",
      "what_it_tells": "这张图说明了什么结论",
      "why_important": "为什么这张图对理解论文很重要"
    }
  ],
  "experiment_read": "实验设计和结果如何？结论可信度怎样？（中文，150字以内）",
  "contributions": ["贡献1", "贡献2"],
  "limitations": ["局限性1", "局限性2"],
  "deep_read_suggestions": ["如果你想深入理解这篇论文，建议关注：1. ..."]
}
```

## 注意事项
1. 基于论文实际内容作答，不要编造
2. 如果某个信息论文中没有明确提及，用"论文中未明确说明"标注
3. 所有中文输出使用学术化但易读的语言风格
4. 对于 core_figures，请根据上下文判断每张图最可能的标题和含义
5. page_number 从 0 开始计数，对应我提供的图片顺序

---

以下是论文的前几页关键内容和部分图表："""


async def run_speedread(paper_id: str, force: bool = False,
                        max_images: int = 4, ai_config: dict | None = None):
    """
    执行速读管道，用 async generator 逐项 yield SSE 事件。

    Yields:
        dict: {"event": "status"|"field"|"figure"|"done"|"error", "data": {...}}
    """
    # Step 0: 检查缓存
    if not force:
        cached = _get_cached(paper_id)
        if cached:
            yield {"event": "done", "data": {"cached": True, "result": cached}}
            return

    _set_status(paper_id, "running")

    try:
        # 获取论文信息
        conn = get_db()
        paper = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,)).fetchone()
        conn.close()
        if not paper:
            yield {"event": "error", "data": {"message": "论文不存在"}}
            return

        file_path = settings.workspace_root / paper["file_path"]
        if not file_path.exists():
            yield {"event": "error", "data": {"message": f"文件不存在: {file_path}"}}
            return

        # Step 1: 提取全文
        yield {"event": "status", "data": {"phase": "extracting"}}
        pages = await asyncio.to_thread(extract_page_texts, str(file_path))
        full_text = "\n\n".join(pages)
        if not full_text.strip():
            yield {"event": "error", "data": {"message": "无法提取 PDF 文本"}}
            return

        total_pages = len(pages)

        # Step 2: 页面评分 + 选择
        yield {"event": "status", "data": {"phase": "scoring", "total_pages": total_pages}}
        selected = select_pages(pages, max_pages=max_images)

        # Step 3: 渲染选中页面为 base64
        yield {"event": "status", "data": {"phase": "rendering", "pages": len(selected)}}
        images = []
        for s in selected:
            pn = s["page_num"]
            b64 = await asyncio.to_thread(render_page_base64, str(file_path), pn)
            if b64:
                images.append({"page_num": pn, "base64": b64})

        # Step 4: 构建上下文文本（标准章节 + 评分页）
        source_text = _build_context(pages, selected, max_chars=settings.max_source_chars)

        # Step 5: 调用 LLM
        yield {"event": "status", "data": {"phase": "calling_llm"}}

        endpoint = (ai_config or {}).get("endpoint", "") or settings.ai_endpoint
        api_key = (ai_config or {}).get("api_key", "") or settings.ai_api_key
        model = (ai_config or {}).get("model", "") or settings.ai_model

        if not api_key:
            yield {"event": "error", "data": {"message": "未配置 AI API Key，请在设置中填写"}}
            return

        result = await _call_llm(endpoint, api_key, model, source_text, images)
        if "error" in result:
            yield {"event": "error", "data": {"message": result["error"]}}
            return

        # Step 6: 持久化
        _save_result(paper_id, result, model)
        _mark_read(paper_id)
        _refresh_metadata(paper_id, file_path, full_text)

        yield {"event": "done", "data": {"cached": False, "result": result}}

    except Exception as e:
        _set_status(paper_id, "error", str(e))
        yield {"event": "error", "data": {"message": str(e)}}


async def _call_llm(endpoint: str, api_key: str, model: str,
                    text: str, images: list[dict]) -> dict:
    """调用 LLM，自动多模态/纯文本回退"""
    import urllib.request
    import ssl

    url = endpoint.rstrip("/") + "/chat/completions"

    # 构建基础消息
    user_content = [{"type": "text", "text": SPEEDREAD_PROMPT + "\n\n" + text}]
    if images:
        for img in images:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img['base64']}"},
            })

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一位严谨的学术论文审稿人。请严格按照 JSON 格式输出。"},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
    }

    # 尝试多模态
    last_error = None
    try:
        result = await _do_request(url, api_key, payload, model)
        if "error" not in result:
            return result
        last_error = result.get("error", "未知错误")
    except Exception as e:
        last_error = str(e)

    # 如果多模态失败，且错误看起来是模型不支持图片（非认证错误），则回退纯文本
    if "认证" in last_error or "401" in last_error or "Key" in last_error:
        return {"error": last_error}

    # 纯文本回退
    payload["messages"][1]["content"] = SPEEDREAD_PROMPT + "\n\n" + text
    try:
        result = await _do_request(url, api_key, payload, model)
        return result
    except Exception as e:
        return {"error": str(e)}


async def _do_request(url: str, api_key: str, payload: dict, model: str) -> dict:
    """发送 HTTP 请求到 LLM"""
    import urllib.request
    import urllib.error
    import ssl

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")

    ctx = ssl.create_default_context()
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ctx))

    try:
        response = await asyncio.to_thread(opener.open, req, timeout=120)
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        code = e.code
        if code == 401:
            raise Exception(f"AI 服务认证失败 (401)：API Key 无效或已过期，请检查设置。"
                          f"\n服务商返回：{detail[:200]}")
        elif code == 400:
            raise Exception(f"AI 服务拒绝请求 (400)：可能是模型名称 '{model}' 不支持，或请求格式有误。"
                          f"\n服务商返回：{detail[:200]}")
        elif code == 429:
            raise Exception(f"AI 服务限流 (429)：请求过于频繁，请稍后重试。"
                          f"\n服务商返回：{detail[:200]}")
        else:
            raise Exception(f"AI 服务返回错误 ({code})：{detail[:200]}")
    except urllib.error.URLError as e:
        raise Exception(f"无法连接到 AI 服务：{e.reason}\n请检查 API 地址是否正确：{url}")

    body = response.read().decode("utf-8")
    resp = json.loads(body)

    content = resp["choices"][0]["message"]["content"]
    tokens = resp.get("usage", {}).get("total_tokens", 0)

    parsed = _parse_json_response(content)
    parsed["model_used"] = model
    parsed["tokens_used"] = tokens
    return parsed


def _parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    # 去除 markdown 代码块
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # 找第一个 { 到最后一个 }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return {"error_parse": "无法解析 LLM 返回的 JSON", "raw": text[:500]}


def _build_context(pages: list[str], selected: list[dict],
                   max_chars: int = 24000) -> str:
    """构建发给 LLM 的上下文文本"""
    n = len(pages)
    # 标准章节：前3页 + 倒数2页 + 最后一页
    index_set = {0, 1, 2, max(0, n - 2), max(0, n - 1)}
    # 加上评分选出的页
    for s in selected:
        index_set.add(s["page_num"])

    indices = sorted(index_set)
    parts = []
    total = 0
    for i in indices:
        if i < n:
            chunk = f"[第{i+1}页]\n{pages[i]}"
            if total + len(chunk) > max_chars:
                remaining = max_chars - total
                if remaining > 100:
                    parts.append(chunk[:remaining])
                break
            parts.append(chunk)
            total += len(chunk)

    return "\n\n".join(parts)


def _mark_read(paper_id: str):
    conn = get_db()
    try:
        conn.execute("UPDATE papers SET read = 1 WHERE id = ?", (paper_id,))
        conn.commit()
    finally:
        conn.close()


def _refresh_metadata(paper_id: str, file_path, full_text: str = ""):
    """用 PDF 内部元数据和提取的文本更新论文的 venue/year/title"""
    conn = get_db()
    try:
        paper = conn.execute(
            "SELECT venue, year, title, file_path FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
        if not paper:
            return

        filename = Path(paper["file_path"]).name

        # 提取 PDF 元数据
        pdf_meta = {}
        try:
            pdf_meta = extract_pdf_metadata(str(file_path))
        except Exception:
            pass

        meta = infer_metadata(filename, pdf_meta)

        # 仅在当前为空或推断出更好信息时更新
        updates = {}
        if meta["venue"] and not paper["venue"]:
            updates["venue"] = meta["venue"]
        if meta["year"] and not paper["year"]:
            updates["year"] = meta["year"]
        if meta["title"] and meta["title"] != paper["title"] and (
            not paper["title"] or len(meta["title"]) > len(paper["title"])
        ):
            updates["title"] = meta["title"]

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE papers SET {set_clause} WHERE id = ?",
                (*updates.values(), paper_id)
            )
            conn.commit()
    finally:
        conn.close()


def _get_cached(paper_id: str) -> dict | None:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM speed_reads WHERE paper_id = ? AND status = 'success'",
            (paper_id,)
        ).fetchone()
        if row:
            return _row_to_dict(row)
    finally:
        conn.close()
    return None


def _set_status(paper_id: str, status: str, error_msg: str = ""):
    conn = get_db()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO speed_reads (paper_id, status, error_message)
               VALUES (?, ?, ?)""",
            (paper_id, status, error_msg)
        )
        conn.commit()
    finally:
        conn.close()


def _save_result(paper_id: str, result: dict, model: str):
    conn = get_db()
    try:
        # 排查 speed_reads 表所有字段
        fields = [
            "status", "one_sentence", "quick_takeaways",
            "problem_and_motivation", "method_overview", "method_steps",
            "core_figures", "experiment_read", "contributions", "limitations",
            "deep_read_suggestions", "model_used", "tokens_used", "error_message",
            "generated_at",
        ]
        values = {
            "status": "success",
            "one_sentence": result.get("one_sentence", ""),
            "quick_takeaways": json.dumps(result.get("quick_takeaways", []), ensure_ascii=False),
            "problem_and_motivation": result.get("problem_and_motivation", ""),
            "method_overview": result.get("method_overview", ""),
            "method_steps": json.dumps(result.get("method_steps", []), ensure_ascii=False),
            "core_figures": json.dumps(result.get("core_figures", []), ensure_ascii=False),
            "experiment_read": result.get("experiment_read", ""),
            "contributions": json.dumps(result.get("contributions", []), ensure_ascii=False),
            "limitations": json.dumps(result.get("limitations", []), ensure_ascii=False),
            "deep_read_suggestions": json.dumps(result.get("deep_read_suggestions", []), ensure_ascii=False),
            "model_used": model,
            "tokens_used": result.get("tokens_used", 0),
            "error_message": "",
            "generated_at": "datetime('now', 'localtime')",
        }
        placeholders = ", ".join(f"{k} = ?" for k in values)
        conn.execute(
            f"INSERT OR REPLACE INTO speed_reads (paper_id, {', '.join(values)}) VALUES (?, {', '.join('?' * len(values))})",
            (paper_id, *values.values())
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row) -> dict:
    def _list(v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return []
        return v if v else []

    return {
        "status": row["status"],
        "one_sentence": row["one_sentence"] or "",
        "quick_takeaways": _list(row["quick_takeaways"]),
        "problem_and_motivation": row["problem_and_motivation"] or "",
        "method_overview": row["method_overview"] or "",
        "method_steps": _list(row["method_steps"]),
        "core_figures": _list(row["core_figures"]),
        "experiment_read": row["experiment_read"] or "",
        "contributions": _list(row["contributions"]),
        "limitations": _list(row["limitations"]),
        "deep_read_suggestions": _list(row["deep_read_suggestions"]),
        "model_used": row["model_used"] or "",
        "tokens_used": row["tokens_used"] or 0,
    }
