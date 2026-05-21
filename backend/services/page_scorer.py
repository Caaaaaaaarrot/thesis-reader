"""页面角色评分 — 按关键词打分选出最有信息量的页面"""

# 四种角色的关键词权重
ROLE_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "method_figure": {
        "keywords": [
            "framework", "architecture", "overview", "pipeline",
            "schematic", "diagram", "flow", "component", "module",
            "我们的方法", "方法框架", "系统架构", "整体框架", "模型结构",
            "proposed method", "our approach", "system overview",
        ],
        "weight": 2.0,
    },
    "core_method": {
        "keywords": [
            "algorithm", "training", "optimization", "loss function",
            "objective", "equation", "formula", "derivation",
            "训练", "优化", "损失函数", "目标函数", "公式",
            "procedure", "implementation", "pseudo", "code",
        ],
        "weight": 1.5,
    },
    "experiment_results": {
        "keywords": [
            "experiment", "result", "performance", "comparison",
            "baseline", "state-of-the-art", "table", "accuracy",
            "实验结果", "对比实验", "性能比较", "消融", "ablation",
            "dataset", "benchmark", "evaluation", "metric",
        ],
        "weight": 1.8,
    },
    "ablation_analysis": {
        "keywords": [
            "ablation", "analysis", "impact", "contribution",
            "component analysis", "sensitivity", "hyperparameter",
            "消融实验", "分析", "参数敏感性", "模块贡献",
            "visualization", "case study", "qualitative",
        ],
        "weight": 1.3,
    },
}

# 通用信息密度加分词
BOOST_KEYWORDS = [
    "figure", "fig.", "table", "shown in", "illustrated",
    "图", "表", "如图", "所示", "见表",
]


def score_page(text: str) -> dict:
    """对一页文本打分，返回总分和角色分类"""
    text_lower = text.lower()
    scores = {}
    details = {}

    for role, config in ROLE_KEYWORDS.items():
        role_score = 0.0
        matched = []
        for kw in config["keywords"]:
            count = text_lower.count(kw.lower())
            if count > 0:
                role_score += count * config["weight"]
                matched.append(kw)
        scores[role] = role_score
        details[role] = matched

    # 通用信息密度加分
    boost = sum(1 for kw in BOOST_KEYWORDS if kw.lower() in text_lower)

    total = sum(scores.values()) + boost
    return {"total": total, "roles": scores, "boost": boost, "details": details}


def select_pages(
    page_texts: list[str],
    max_pages: int = 4,
) -> list[dict]:
    """
    从所有页面中选出 top-N 页。
    返回 [{page_num, total_score, role_scores, ...}]
    """
    page_scores = []
    for i, text in enumerate(page_texts):
        if not text.strip():
            continue
        s = score_page(text)
        page_scores.append({
            "page_num": i,
            "total_score": s["total"],
            "roles": s["roles"],
            "boost": s["boost"],
        })

    # 按总分排序
    page_scores.sort(key=lambda x: -x["total_score"])
    return page_scores[:max_pages]
