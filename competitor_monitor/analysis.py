from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from .util import normalized_text, title_dedupe_key


EVENT_TERMS = {
    "ra mat", "cong bo", "phat hanh", "trien khai", "hop tac", "ky ket", "dau tu",
    "mua lai", "goi von", "tang", "giam", "launch", "announce", "release", "partnership",
    "acquire", "funding", "introduce", "update", "open source",
}
OPINION_TERMS = {
    "nhan dinh", "du bao", "quan diem", "binh luan", "theo toi", "co the", "nen",
    "opinion", "forecast", "predict", "why", "should", "could",
}


def _matches(text: str, values: list[str]) -> list[str]:
    output = []
    for value in values:
        needle = normalized_text(value)
        if needle and needle in text:
            output.append(value)
    return output


def enrich_item(item: dict, config: dict) -> dict:
    text = normalized_text(f"{item.get('title', '')} {item.get('summary', '')}")
    competitors: list[str] = []
    for competitor in config.get("competitors") or []:
        aliases = [competitor["name"], *(competitor.get("aliases") or [])]
        if _matches(text, aliases):
            competitors.append(competitor["name"])
    topics: list[str] = []
    topic_hits = 0
    for topic in config.get("topics") or []:
        hits = _matches(text, topic.get("keywords") or [])
        if hits:
            topics.append(topic["name"])
            topic_hits += len(hits)
    general_keywords = config.get("keywords") or (config.get("agent") or {}).get("keywords") or []
    general_hits = len(_matches(text, general_keywords))
    event_hits = sum(term in text for term in EVENT_TERMS)
    opinion_hits = sum(term in text for term in OPINION_TERMS)
    if event_hits and event_hits >= opinion_hits:
        kind = "SỰ KIỆN"
    elif opinion_hits:
        kind = "NHẬN ĐỊNH"
    else:
        kind = "PHÂN TÍCH/TIN"
    signal_score = len(competitors) * 3 + topic_hits * 2 + general_hits
    priority = max(1, 4 - int(item.get("source_priority", 3))) if signal_score else 0
    score = min(10, signal_score + priority)
    item.update(
        competitors=sorted(set(competitors)),
        topics=sorted(set(topics)),
        kind=kind,
        relevance_score=score,
        dedupe_key=title_dedupe_key(item["title"], item.get("published_at")),
    )
    return item


def _tag_counts(items: list[dict], field: str) -> Counter:
    counts: Counter = Counter()
    for item in items:
        counts.update(item.get(field) or [])
    return counts


def build_analysis(store, current_items: list[dict], config: dict, lookback_hours: int, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    current_start = now - timedelta(hours=lookback_hours)
    previous_start = current_start - timedelta(hours=lookback_hours)
    current_history = store.items_between(current_start.isoformat().replace("+00:00", "Z"), now.isoformat().replace("+00:00", "Z"))
    previous_history = store.items_between(previous_start.isoformat().replace("+00:00", "Z"), current_start.isoformat().replace("+00:00", "Z"))

    competitor_counts = _tag_counts(current_items, "competitors")
    topic_counts = _tag_counts(current_history, "topics")
    previous_topic_counts = _tag_counts(previous_history, "topics")
    trends = []
    for topic in sorted(set(topic_counts) | set(previous_topic_counts)):
        current = topic_counts[topic]
        previous = previous_topic_counts[topic]
        delta = current - previous
        if previous:
            change_pct = round(delta * 100 / previous, 1)
        elif current:
            change_pct = None
        else:
            change_pct = 0.0
        direction = "tăng" if delta > 0 else "giảm" if delta < 0 else "ổn định"
        trends.append({"topic": topic, "current": current, "previous": previous, "delta": delta, "change_pct": change_pct, "direction": direction})
    trends.sort(key=lambda row: (row["delta"], row["current"]), reverse=True)

    opportunities: list[str] = []
    risks: list[str] = []
    actions: list[str] = []
    if trends and trends[0]["delta"] > 0:
        opportunities.append(f"Chủ đề “{trends[0]['topic']}” đang tăng tín hiệu; cân nhắc nội dung hoặc thử nghiệm sản phẩm bám nhu cầu này.")
        actions.append(f"Trong 7 ngày tới, xác minh nhu cầu khách hàng liên quan “{trends[0]['topic']}” bằng 5 cuộc trao đổi hoặc dữ liệu tìm kiếm nội bộ.")
    if competitor_counts:
        leader, count = competitor_counts.most_common(1)[0]
        if count >= 2:
            risks.append(f"{leader} có {count} hoạt động mới trong kỳ; nguy cơ tăng độ hiện diện nếu doanh nghiệp phản ứng chậm.")
        actions.append(f"Đối chiếu thông điệp, kênh và lời kêu gọi hành động của {leader} trước khi chốt kế hoạch truyền thông tiếp theo.")
    if not current_items:
        risks.append("Không có mục mới đạt ngưỡng liên quan; có thể do kỳ yên ắng hoặc độ bao phủ nguồn còn thiếu.")
        actions.append("Kiểm tra danh sách nguồn có trạng thái LIMITED/MANUAL_REVIEW và bổ sung RSS hoặc API hợp lệ.")
    if not opportunities:
        opportunities.append("Chưa đủ bằng chứng để kết luận cơ hội mới; tiếp tục thu thập qua ít nhất hai kỳ so sánh.")
    if not risks:
        risks.append("Chưa phát hiện rủi ro cạnh tranh nổi bật từ dữ liệu kỳ này; vẫn cần theo dõi các nguồn đang tắt hoặc chưa cấp quyền.")

    return {
        "competitor_activity": [{"name": name, "count": count} for name, count in competitor_counts.most_common()],
        "topic_activity": [{"name": name, "count": count} for name, count in _tag_counts(current_items, "topics").most_common()],
        "trends": trends,
        "opportunities": opportunities,
        "risks": risks,
        "actions": actions,
        "comparison_note": "Xu hướng là nhận định định lượng từ số mục trong hai cửa sổ thời gian liên tiếp, không phải sự kiện độc lập.",
    }


def peas_evaluation(summary: dict, items: list[dict], source_checks: list[dict]) -> dict:
    active_checks = [row for row in source_checks if row["status"] != "DISABLED"]
    accessible = sum(row["status"] == "HEALTHY" for row in active_checks)
    search_only = sum(row["status"] == "SEARCH_INDEX_ONLY" for row in active_checks)
    total_sources = len(active_checks)
    evidence_complete = sum(bool(item.get("canonical_url") and item.get("published_at") and item.get("evidence")) for item in items)
    coverage = round(accessible * 100 / total_sources, 1) if total_sources else 0.0
    evidence_rate = round(evidence_complete * 100 / len(items), 1) if items else 0.0
    return {
        "P": {
            "raw_items_received": summary.get("received", 0),
            "filtered_out_irrelevant": summary.get("filtered_out", 0),
            "new_items": summary.get("new_items", 0),
            "duplicates_removed": summary.get("duplicates", 0),
            "source_access_rate_pct": coverage,
            "search_index_only_sources": search_only,
            "evidence_complete_pct": evidence_rate,
            "result": "ĐẠT" if coverage >= 60 and (not items or evidence_rate == 100.0) else "MỘT PHẦN",
        },
        "E": {"sources_checked": total_sources, "healthy_direct_or_allowed": accessible, "search_index_only": search_only, "limited_or_review": sum(row["status"] in {"LIMITED", "MANUAL_REVIEW"} for row in active_checks), "errors": sum(row["status"] == "ERROR" for row in active_checks), "disabled_not_tested": sum(row["status"] == "DISABLED" for row in source_checks)},
        "A": {"pipeline": "thu thập → lọc → phân loại → xu hướng → so sánh → báo cáo", "completed": True},
        "S": {"items_with_url_and_date": evidence_complete, "items_total": len(items), "engagement_available": sum(bool(item.get("engagement")) for item in items)},
    }
