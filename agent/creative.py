"""Deterministic AIGC creative brief and review rubric.

The demo never calls an image model by default. `MockCreativeProvider` returns
asset metadata so the brief -> provider -> rubric contract is exercised end to
end without network access or cost. To plug in a real generator, implement
`CreativeProvider.generate` and register it in `PROVIDERS`; the graph node, API
snapshot and UI stay unchanged.

Briefs are built from real review pain points, positive themes, SKU attributes
and the existing compliance rules. The rubric reuses those rules so prohibited
claims in overlay copy are blocked before any asset is published.
"""
from __future__ import annotations

from typing import Any, Protocol

from agent.nodes.compliance import check_rules

SLOTS = (
    ("hero", "主图", "1:1", "搜索结果首图；纯白背景，只展示产品本体"),
    ("lifestyle", "场景图", "1:1", "展示日常使用场景与目标人群"),
    ("detail", "细节图", "1:1", "回应评论痛点，展示材质与结构"),
    ("comparison", "套装图", "1:1", "展示套件内容与尺寸参照，不贬低竞品"),
    ("aplus", "A+ 横幅", "16:9", "品牌故事与购买理由，文字保持可读"),
)

DIMENSIONS = (
    ("policy", "合规政策", 0.30),
    ("grounding", "评论证据", 0.25),
    ("fidelity", "产品还原", 0.20),
    ("legibility", "文案可读", 0.15),
    ("coverage", "素材覆盖", 0.10),
)

CLAIM_CATEGORY_LABELS = {
    "prohibited_claim": "排名/促销类宣称",
    "prohibited_claims": "排名/促销类宣称",
    "medical_claim": "医疗/疗效类宣称",
    "certification": "未证实认证",
    "guarantee": "保证承诺",
    "origin": "产地宣称",
    "promotion": "促销/免运文案",
}

EXTRA_AVOID = (
    "前后对比 / before-after 效果暗示",
    "手术或医疗效果暗示（如 cosmetic surgery results）",
)

THEME_ZH = {
    "value": "性价比",
    "adhesion": "粘性",
    "hard to clean": "难清洁",
    "blending power": "效果与力度",
    "no results": "效果",
    "irritation": "刺激",
    "smell": "气味",
    "durability": "耐用性",
    "size/fit": "尺寸与贴合",
    "quality": "质量",
    "performance": "性能",
    "ease of use": "易用",
    "portability": "便携",
    "results": "使用效果",
}

HERO_SLOT = "hero"
MAX_OVERLAY_CHARS = 40
MAX_OVERLAY_WORDS = 6


def _finding(
    dimension: str,
    severity: str,
    asset_id: str | None,
    message: str,
    suggestion: str = "",
) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "severity": severity,
        "asset_id": asset_id or "brief",
        "message": message,
        "suggestion": suggestion,
    }


def _safe_attributes(sku: dict[str, Any]) -> list[str]:
    return [
        str(item).strip()
        for item in sku.get("attributes") or []
        if str(item).strip() and str(item).strip().lower() != "adult"
    ][:4]


def _pain_evidence(
    insights: dict[str, Any], reviews: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for pain in (insights.get("pain_points") or [])[:3]:
        quotes = pain.get("quotes") or []
        quote = str(quotes[0]).strip() if quotes else ""
        match: dict[str, Any] | None = None
        for review in reviews:
            text = str(review.get("text") or "").strip()
            if quote and text and text in quote:
                match = review
                break
        evidence.append(
            {
                "type": "pain",
                "theme": str(pain.get("theme") or ""),
                "frequency": int(pain.get("frequency") or 0),
                "quote": quote[:220],
                "review_id": match.get("review_id") if match else None,
                "rating": match.get("rating") if match else None,
                "date": match.get("date") if match else None,
            }
        )
    return evidence


def _positive_evidence(insights: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "positive_theme",
            "theme": str(item.get("theme") or ""),
            "mentions": int(item.get("mentions") or 0),
        }
        for item in (insights.get("positive_themes") or [])[:2]
    ]


def _must_avoid(rules: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for rule in rules:
        if rule.get("severity") not in {"block", "warn"}:
            continue
        label = CLAIM_CATEGORY_LABELS.get(str(rule.get("category") or ""))
        if label and label not in labels:
            labels.append(label)
    for item in EXTRA_AVOID:
        if item not in labels:
            labels.append(item)
    return labels


def _overlay(slot: str, attributes: list[str]) -> str | None:
    if slot == HERO_SLOT:
        return None
    if slot == "detail":
        candidate = attributes[1] if len(attributes) > 1 else attributes[0] if attributes else ""
    elif slot == "comparison":
        candidate = attributes[0] if attributes else ""
    elif slot == "aplus":
        candidate = attributes[2] if len(attributes) > 2 else attributes[0] if attributes else ""
    else:
        return None
    text = str(candidate).strip()
    if not text:
        return None
    if len(text) > MAX_OVERLAY_CHARS:
        return text[: MAX_OVERLAY_CHARS - 3].rstrip() + "..."
    return text


def _asset_evidence(
    slot: str,
    pain: list[dict[str, Any]],
    positive: list[dict[str, Any]],
    attributes: list[str],
) -> list[dict[str, Any]]:
    if slot == HERO_SLOT:
        evidence = positive[:1] or pain[:1]
    elif slot == "lifestyle":
        evidence = positive[:2] or pain[:1]
    elif slot == "detail":
        evidence = pain[:2] or positive[:1]
    elif slot == "comparison":
        evidence = pain[1:2] or pain[:1] or positive[:1]
    else:
        evidence = pain[:1] + positive[:1]
    if not evidence:
        evidence = [{"type": "sku_attribute", "value": attributes[0] if attributes else ""}]
    return evidence


def _theme_zh(value: str) -> str:
    return THEME_ZH.get(value, value)


def _scene(
    slot: str,
    sku: dict[str, Any],
    attributes: list[str],
    pain: list[dict[str, Any]],
    positive: list[dict[str, Any]],
    overlay: str | None,
) -> str:
    title = str(sku.get("title") or "")
    subcategory = str(sku.get("subcategory") or "product")
    brand = str(sku.get("brand") or "Brand")
    pain_theme = "、".join(
        _theme_zh(str(item.get("theme") or "")) for item in pain[:2]
    )
    positive_theme = (
        _theme_zh(str(positive[0].get("theme") or "")) if positive else ""
    )
    if slot == HERO_SLOT:
        return (
            f"纯白无缝背景，{title} 与包装内容居中，45° 微俯视，柔和棚拍光；"
            "不添加文字、道具或边框。"
        )
    if slot == "lifestyle":
        focus = positive_theme or "日常使用"
        return (
            f"成年人在日常场景中使用 {subcategory} 产品；自然日光；突出{focus}；"
            "不展示前后对比。"
        )
    if slot == "detail":
        detail = attributes[1] if len(attributes) > 1 else "产品细节"
        return (
            f"微距拍摄「{detail}」；回应评论痛点「{pain_theme or '使用体验'}」；"
            "材质、接缝与使用方式清晰可见。"
        )
    if slot == "comparison":
        content = attributes[0] if attributes else "套件内容"
        return (
            f"平铺展示「{content}」与包装内容；用尺规参照物表达尺寸；"
            "不出现竞品 logo 或贬低性对比。"
        )
    return (
        f"{brand} 的生活方式横幅；左侧产品、右侧使用场景；"
        f"叠加短句「{overlay or '日常使用'}」；四周留安全边距。"
    )


def build_creative_brief(
    sku: dict[str, Any],
    insights: dict[str, Any],
    listing: dict[str, Any],
    reviews: list[dict[str, Any]],
    compliance_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a deterministic 5-slot art brief for one SKU."""
    attributes = _safe_attributes(sku)
    pain = _pain_evidence(insights, reviews)
    positive = _positive_evidence(insights)
    must_avoid = _must_avoid(compliance_rules)
    must_show = attributes or [str(sku.get("title") or "产品本体")]

    assets: list[dict[str, Any]] = []
    for slot, label, ratio, purpose in SLOTS:
        overlay = _overlay(slot, attributes)
        evidence = _asset_evidence(slot, pain, positive, attributes)
        scene = _scene(slot, sku, attributes, pain, positive, overlay)
        prompt = (
            f"{scene} 必须展示：{'；'.join(must_show)}。"
            f"禁止：{'；'.join(must_avoid)}。比例 {ratio}。"
        )
        assets.append(
            {
                "asset_id": f"{sku['sku_id']}:{slot}",
                "slot": slot,
                "label": label,
                "ratio": ratio,
                "purpose": purpose,
                "scene": scene,
                "prompt": prompt,
                "overlay_text": overlay,
                "must_show": list(must_show),
                "must_avoid": list(must_avoid),
                "evidence": evidence,
            }
        )

    return {
        "sku_id": str(sku["sku_id"]),
        "title": str(sku.get("title") or ""),
        "subcategory": str(sku.get("subcategory") or ""),
        "source": "deterministic_brief",
        "simulated": True,
        "listing_title": str(listing.get("title") or ""),
        "global_rules": [
            "主图使用纯白背景，只含产品与必要配件，不加文字、水印、边框或道具。",
            "所有文案只使用 brief 中的 overlay_text，不得自行添加功效或排名宣称。",
            "保留真实产品结构、颜色与包装内容，不生成不存在的配件。",
            "人像必须为成年人；不展示裸肤伤口、不适画面或前后对比。",
        ],
        "must_show": list(must_show),
        "must_avoid": list(must_avoid),
        "assets": assets,
        "assumptions": [
            "brief 由真实评论痛点、SKU 属性与合规规则确定性生成。",
            "默认 mock 提供方不调用图像模型，素材未渲染。",
            "接入真实 AIGC 后需实现 CreativeProvider，并重新运行 rubric。",
        ],
    }


class CreativeProvider(Protocol):
    """Contract for an image/video generator.

    A real provider receives the brief and returns one record per asset. It
    should keep `asset_id`, `slot`, `ratio`, `overlay_text`, `must_show`,
    `must_avoid` and `evidence`, set `rendered=true`, and add an `asset_url`.
    """

    name: str

    def generate(
        self, brief: dict[str, Any], sku: dict[str, Any]
    ) -> list[dict[str, Any]]: ...


class MockCreativeProvider:
    """Deterministic provider that returns metadata only; no network calls."""

    name = "mock"

    def generate(
        self, brief: dict[str, Any], sku: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return [
            {
                "asset_id": asset["asset_id"],
                "slot": asset["slot"],
                "label": asset["label"],
                "ratio": asset["ratio"],
                "provider": self.name,
                "status": "mock",
                "rendered": False,
                "format": "png",
                "prompt": asset["prompt"],
                "overlay_text": asset["overlay_text"],
                "must_show": list(asset["must_show"]),
                "must_avoid": list(asset["must_avoid"]),
                "evidence": [dict(item) for item in asset["evidence"]],
                "asset_url": None,
                "note": "mock 提供方不调用图像模型；接入真实 provider 后写入 rendered 与 asset_url。",
            }
            for asset in brief.get("assets") or []
        ]


PROVIDERS: dict[str, CreativeProvider] = {"mock": MockCreativeProvider()}


def get_provider(name: str | None) -> CreativeProvider:
    return PROVIDERS.get(str(name or "mock"), PROVIDERS["mock"])


def _dimension(
    key: str, label: str, weight: float, score: float
) -> dict[str, Any]:
    return {
        "name": key,
        "label": label,
        "weight": round(weight, 2),
        "score": round(max(0.0, min(100.0, score)), 1),
    }


def _policy_findings(
    assets: list[dict[str, Any]], rules: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], float]:
    findings: list[dict[str, Any]] = []
    score = 100.0
    for asset in assets:
        asset_id = str(asset.get("asset_id") or "")
        overlay = str(asset.get("overlay_text") or "").strip()
        if asset.get("slot") == HERO_SLOT and overlay:
            score -= 30
            findings.append(
                _finding(
                    "policy",
                    "block",
                    asset_id,
                    "主图叠加了文字；Amazon 主图要求纯白背景、只含产品本体。",
                    "移除 hero 的 overlay_text。",
                )
            )
        if not overlay:
            continue
        pseudo = {"title": overlay, "bullets": [], "description": ""}
        for issue in check_rules(pseudo, rules):
            severity = str(issue.get("severity") or "warn")
            if severity not in {"block", "warn"}:
                continue
            score -= 30 if severity == "block" else 8
            findings.append(
                _finding(
                    "policy",
                    severity,
                    asset_id,
                    f"{issue.get('rule_id')} {issue.get('message')}",
                    str(issue.get("suggestion") or ""),
                )
            )
    return findings, score


def _grounding_findings(
    assets: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], float]:
    findings: list[dict[str, Any]] = []
    score = 100.0
    for asset in assets:
        if not asset.get("evidence"):
            score -= 25
            findings.append(
                _finding(
                    "grounding",
                    "warn",
                    str(asset.get("asset_id") or ""),
                    "素材位没有引用评论或 SKU 证据。",
                    "补充对应痛点或正向主题的证据。",
                )
            )
    detail = next((item for item in assets if item.get("slot") == "detail"), None)
    if detail is not None and not any(
        item.get("type") == "pain" for item in detail.get("evidence") or []
    ):
        score -= 15
        findings.append(
            _finding(
                "grounding",
                "warn",
                str(detail.get("asset_id") or ""),
                "细节图没有引用评论痛点。",
                "从 insights.pain_points 选择一条真实评论作为依据。",
            )
        )
    return findings, score


def _fidelity_findings(
    assets: list[dict[str, Any]], brief: dict[str, Any]
) -> tuple[list[dict[str, Any]], float]:
    required = list(brief.get("must_show") or [])
    findings: list[dict[str, Any]] = []
    score = 100.0
    for asset in assets:
        missing = [
            item
            for item in required
            if item not in (asset.get("must_show") or [])
        ]
        if missing:
            score -= min(60, 20 * len(missing))
            findings.append(
                _finding(
                    "fidelity",
                    "warn",
                    str(asset.get("asset_id") or ""),
                    "素材 brief 缺少必须展示的产品属性：" + "、".join(missing),
                    "把 SKU 属性写回 must_show，避免生成不存在的结构。",
                )
            )
    if any(not asset.get("rendered") for asset in assets):
        findings.append(
            _finding(
                "fidelity",
                "info",
                None,
                "mock 提供方未渲染图片，像素级产品还原无法验证。",
                "接入真实 provider 后重新运行 rubric。",
            )
        )
    return findings, score


def _legibility_findings(
    assets: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], float]:
    findings: list[dict[str, Any]] = []
    score = 100.0
    for asset in assets:
        overlay = str(asset.get("overlay_text") or "").strip()
        if not overlay:
            continue
        if len(overlay) > MAX_OVERLAY_CHARS or len(overlay.split()) > MAX_OVERLAY_WORDS:
            score -= 20
            findings.append(
                _finding(
                    "legibility",
                    "warn",
                    str(asset.get("asset_id") or ""),
                    f"叠字「{overlay}」超过 {MAX_OVERLAY_CHARS} 字符或 {MAX_OVERLAY_WORDS} 个词。",
                    "缩短为一条可扫读的短句。",
                )
            )
    return findings, score


def _coverage_findings(
    assets: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], float]:
    expected = [slot for slot, *_ in SLOTS]
    present = [str(asset.get("slot") or "") for asset in assets]
    missing = [slot for slot in expected if slot not in present]
    duplicates = [slot for slot in expected if present.count(slot) > 1]
    findings: list[dict[str, Any]] = []
    score = 100.0 - 25 * len(missing) - 10 * len(duplicates)
    if missing:
        findings.append(
            _finding(
                "coverage",
                "warn",
                None,
                "缺少素材位：" + "、".join(missing),
                "补齐 5 个素材位后再发布。",
            )
        )
    if duplicates:
        findings.append(
            _finding(
                "coverage",
                "info",
                None,
                "重复素材位：" + "、".join(duplicates),
                "每个素材位只保留一个主版本。",
            )
        )
    return findings, score


def review_creative(
    assets: list[dict[str, Any]],
    brief: dict[str, Any],
    rules: list[dict[str, Any]],
    provider_name: str = "mock",
) -> dict[str, Any]:
    """Score generated asset metadata against the creative rubric."""
    findings: list[dict[str, Any]] = []
    raw_scores: dict[str, float] = {}

    for key, func in (
        ("policy", lambda: _policy_findings(assets, rules)),
        ("grounding", lambda: _grounding_findings(assets)),
        ("fidelity", lambda: _fidelity_findings(assets, brief)),
        ("legibility", lambda: _legibility_findings(assets)),
        ("coverage", lambda: _coverage_findings(assets)),
    ):
        dimension_findings, score = func()
        findings.extend(dimension_findings)
        raw_scores[key] = score

    dimensions = [
        _dimension(key, label, weight, raw_scores[key])
        for key, label, weight in DIMENSIONS
    ]
    score = sum(item["score"] * item["weight"] for item in dimensions)
    blocks = sum(1 for item in findings if item["severity"] == "block")
    warns = sum(1 for item in findings if item["severity"] == "warn")
    return {
        "score": round(score, 1),
        "passed": blocks == 0,
        "provider": provider_name,
        "asset_count": len(assets),
        "block_count": blocks,
        "warn_count": warns,
        "dimensions": dimensions,
        "findings": findings,
        "assumptions": [
            "rubric 只审核素材元数据与叠字，不替代人工视觉审核。",
            "mock 资产未渲染，像素级构图与产品还原标为无法验证。",
            "叠字合规复用现有 21 条确定性规则。",
        ],
    }
