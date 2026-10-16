"""Render the compact, social-first executive report with the bundled sample design."""
from __future__ import annotations

import html
import base64
import hashlib
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


STYLE = (Path(__file__).resolve().parent.parent / "assets" / "report-style.css").read_text(encoding="utf-8")
SOCIAL = {"facebook", "tiktok", "youtube"}


def _h(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _short(value: object, limit: int = 180) -> str:
    words = str(value or "").split()
    result = " ".join(words)
    return result if len(result) <= limit else result[:limit].rsplit(" ", 1)[0] + "…"


def _date(value: object) -> str:
    return str(value or "")[:10] or "Chưa xác minh ngày"


def _method(item: dict) -> str:
    evidence = item.get("evidence") or {}
    return str(evidence.get("collection_method") or evidence.get("collection_tier") or "Chưa rõ")


def _is_index(item: dict) -> bool:
    evidence = item.get("evidence") or {}
    return "SEARCH_INDEX_ONLY" in str(evidence.get("collection_tier", "")) or "search_index" in _method(item).lower()


def _priority(item: dict) -> int:
    channel = str(item.get("source_type", "")).lower()
    social = channel in SOCIAL
    return 0 if social and not _is_index(item) else 1 if social else 2 if not _is_index(item) else 3


def _item_link(item: dict, label: str) -> str:
    url = str(item.get("canonical_url") or "")
    if not url.startswith(("https://", "http://")):
        return _h(label)
    return f'<a href="{_h(url)}" target="_blank" rel="noopener noreferrer">{_h(label)}</a>'


def _number_link(item: dict, number: int) -> str:
    return _item_link(item, f"{number:02d}").replace("<a ", '<a class="topic-no" ', 1)


def selected_topics(payload: dict) -> list[tuple[str, dict]]:
    """Choose the same evidence rows for the report and its screenshot plan."""
    items = [item for item in payload.get("items", []) if item.get("canonical_url")
             and (urlsplit(item["canonical_url"]).hostname or "") not in {"news.google.com", "www.google.com", "google.com"}
             and not (item.get("source_type") == "website" and urlsplit(item["canonical_url"]).path in {"", "/"})]
    items.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    items.sort(key=_priority)
    topics = []
    used_urls = set()
    for topic in (payload.get("analysis") or {}).get("topic_activity") or []:
        candidate = next((item for item in items if topic["name"] in (item.get("topics") or [])
                          and item["canonical_url"] not in used_urls), None)
        if candidate:
            topics.append((topic["name"], candidate))
            used_urls.add(candidate["canonical_url"])
        if len(topics) == 5:
            break
    return topics


def screenshot_plan(payload: dict) -> dict:
    return {
        "screenshots": [
            {"topic": name, "source_url": item["canonical_url"], "path": f"screenshots/topic-{index:02d}.png",
             "captured_at": "", "method": ""}
            for index, (name, item) in enumerate(selected_topics(payload), 1)
        ]
    }


def _screenshot_data(row: dict, root: Path, topic: str, source_url: str) -> tuple[str, str, str]:
    if row.get("topic") != topic or row.get("source_url") != source_url:
        raise ValueError(f"Ảnh chụp không khớp chủ đề/URL nguồn: {topic}")
    relative = Path(str(row.get("path") or ""))
    if relative.is_absolute() or relative.parts[:1] != ("screenshots",) or ".." in relative.parts:
        raise ValueError(f"Đường dẫn ảnh không hợp lệ: {relative}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f"Không tìm thấy ảnh chụp trong thư mục lượt chạy: {relative}")
    data = target.read_bytes()
    if not 30 <= len(data) <= 8_000_000:
        raise ValueError(f"Kích thước ảnh không hợp lệ: {relative}")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError(f"Tệp không phải ảnh PNG/JPEG/WebP: {relative}")
    if not row.get("captured_at") or not row.get("method"):
        raise ValueError(f"Thiếu thời điểm hoặc phương thức chụp: {topic}")
    try:
        captured = datetime.fromisoformat(str(row["captured_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Thời điểm chụp không đúng ISO 8601: {topic}") from exc
    if captured.tzinfo is None:
        raise ValueError(f"Thời điểm chụp phải có múi giờ: {topic}")
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}", str(row["captured_at"]), hashlib.sha256(data).hexdigest()


def render_landing_html(payload: dict, *, screenshot_root: Path | None = None, require_screenshots: bool = False) -> str:
    meta = payload["meta"]
    items = [item for item in payload.get("items", []) if item.get("canonical_url")]
    items.sort(key=lambda item: str(item.get("published_at") or ""), reverse=True)
    items.sort(key=_priority)
    analysis = payload.get("analysis") or {}
    checks = payload.get("source_checks") or []
    tz_name = meta.get("timezone") or "Asia/Ho_Chi_Minh"
    try:
        local_tz = ZoneInfo(tz_name)
    except (KeyError, ValueError):
        local_tz = timezone.utc
    produced = datetime.fromisoformat(meta["produced_at"].replace("Z", "+00:00")).astimezone(local_tz)
    start = produced - timedelta(hours=int(meta.get("lookback_hours", 0)))
    period = f'{start:%d/%m/%Y}–{produced:%d/%m/%Y}'
    companies = list(dict.fromkeys(meta.get("competitor_names") or [name for item in items for name in item.get("competitors") or []]))
    own_company = meta.get("company") or {}
    if not isinstance(own_company, dict):
        own_company = {}
    intro = ", ".join(companies) if companies else "các đối thủ được cấu hình"
    coverage_note = f"Đã ghi nhận {len(items)} mục mới trong kỳ từ {len(checks)} nguồn được cấu hình."
    social_count = sum(item.get("source_type", "").lower() in SOCIAL for item in items)
    coverage_note += f" {social_count} mục thuộc kênh xã hội; mục chỉ từ chỉ mục tìm kiếm chưa được xem là bài gốc đã kiểm chứng."

    topic_rows = selected_topics(payload)
    screenshot_rows = (payload.get("topic_screenshots") or {}).get("screenshots") or []
    if require_screenshots and (len(topic_rows) != 5 or len(screenshot_rows) != 5 or screenshot_root is None):
        raise ValueError("Báo cáo cuối cần đúng 5 chủ đề và 5 ảnh chụp nguồn tương ứng")
    if require_screenshots and len({row.get("path") for row in screenshot_rows}) != 5:
        raise ValueError("Năm chủ đề phải dùng năm ảnh chụp khác nhau")
    topic_cards = []
    attached = 0
    screenshot_hashes = set()
    for i, (name, item) in enumerate(topic_rows, 1):
        media = '<div class="topic-shot-missing">Chưa có ảnh chụp nguồn — bản nháp</div>'
        if i <= len(screenshot_rows) and screenshot_root is not None:
            try:
                uri, captured_at, digest = _screenshot_data(screenshot_rows[i - 1], screenshot_root, name, item["canonical_url"])
                if digest in screenshot_hashes:
                    raise ValueError("Không được dùng cùng một ảnh chụp cho nhiều chủ đề")
                screenshot_hashes.add(digest)
                media = (f'<figure class="topic-shot"><img src="{uri}" alt="Ảnh chụp nguồn cho chủ đề {_h(name)}" loading="lazy">'
                         f'<figcaption>Ảnh chụp nguồn · {_h(captured_at)} · {_h(screenshot_rows[i - 1]["method"])}'
                         f'{" · chỉ mục, chưa xác minh bài gốc" if _is_index(item) else ""}</figcaption></figure>')
                attached += 1
            except ValueError:
                if require_screenshots:
                    raise
        topic_cards.append(
            f'<article class="topic">{_number_link(item, i)}<div class="topic-body"><h3>{_h(name)}</h3>'
            f'<p>{_h(_short(item.get("summary") or item.get("title")))} · {_h(_date(item.get("published_at")))}'
            f' · {_h(item.get("source_name"))} · {_h(_method(item))}{" · chỉ mục, chưa đọc bài gốc" if _is_index(item) else ""}</p>'
            f'{media}</div></article>'
        )
    if require_screenshots and attached != 5:
        raise ValueError("Không đủ năm ảnh chụp hợp lệ để xuất báo cáo cuối")
    topic_html = "".join(topic_cards) or '<p class="insight">Chưa có chủ đề đủ bằng chứng trong lượt chạy này.</p>'

    competitor_html = ""
    for name in companies:
        matches = [item for item in items if name in (item.get("competitors") or [])]
        if matches:
            item = matches[0]
            activity = f'{_h(_short(item.get("summary") or item.get("title")))} · {_h(_date(item.get("published_at")))} · {_h(item.get("source_type", "").title())} · {_h(_method(item))}.'
            activity += f' {_item_link(item, "Mở nguồn")}'
            state = '<span class="state">Chỉ mục</span>' if _is_index(item) else ""
        else:
            activity = "Chưa xác minh được bài mới trong kỳ từ các nguồn hiện có."
            state = '<span class="state">Thiếu dữ liệu</span>'
        competitor_html += f'<article class="competitor"><span class="initial">{_h(name[:1].upper())}</span><h3>{_h(name)}</h3><p>{activity}</p>{state}</article>'
    if not competitor_html:
        competitor_html = '<p class="insight">Chưa có danh sách đối thủ. Hãy cấu hình trước khi chạy.</p>'

    # Suggestions are hypotheses, not claims that competitors have never covered them.
    topic_names = [row["name"] for row in (analysis.get("topic_activity") or [])]
    focus = topic_names[0] if topic_names else meta.get("industry", "ngành này")
    customer = own_company.get("target_customers") or "khách hàng mục tiêu"
    offer = own_company.get("product") or meta.get("industry", "sản phẩm/dịch vụ này")
    gaps = [
        ("Chi phí và giá trị thực tế", f"Thử so sánh ngân sách, công sức và lợi ích khi chọn {offer} cho {customer}."),
        ("Trải nghiệm trước–sau có số đo", "Tìm một khách hàng đồng ý công bố kết quả trước và sau; nêu cách đo và giới hạn của kết quả."),
        ("Hướng dẫn bắt đầu từng bước", f"Biến chủ đề {focus} thành hướng dẫn thực hành, lỗi thường gặp và cách tự kiểm tra kết quả."),
    ]
    gaps_html = "".join(f'<div class="insight"><h3>{i:02d} · {_h(title)}</h3><p>{_h(body)}</p></div>' for i, (title, body) in enumerate(gaps, 1))
    ideas = [
        (f"Video 60 giây: {focus} hoạt động ra sao?", "Minh họa một quy trình thật, nêu rõ dữ liệu ví dụ."),
        ("Checklist trước khi lựa chọn", f"Giúp {customer} tự đánh giá lựa chọn phù hợp."),
        ("Bảng tính ngân sách và giá trị nhận được", "Công khai giả định và chỉ dùng mức giá đã xác minh."),
        ("Một câu chuyện khách hàng có chỉ số trước–sau", "Xin phép khách hàng và đối soát số liệu trước khi công bố."),
        (f"Hỏi đáp về {focus}", "Trả lời 5 câu hỏi từ khách hàng hoặc đội bán hàng, phân biệt ý kiến và bằng chứng."),
    ]
    ideas_html = "".join(f'<article class="idea"><span class="number">{i:02d}</span><div><h3>{_h(title)}</h3><p>{_h(body)}</p></div></article>' for i, (title, body) in enumerate(ideas, 1))

    sources_html = "".join(
        f'<li id="s{i:02d}"><span class="id">[{i:02d}]</span><span class="platform">{_h(item.get("source_type", "Nguồn"))}</span>'
        f'<span>{_item_link(item, _short(item.get("title"), 110))} · {_h(_date(item.get("published_at")))} · {_h(_method(item))}'
        f'{" · chỉ mục" if _is_index(item) else ""}</span></li>'
        for i, item in enumerate(items[:30], 1)
    ) or '<li>Chưa có nguồn bài viết đủ điều kiện.</li>'
    limited = [row for row in checks if row.get("status") not in {"HEALTHY", "DISABLED"}]
    limits = "; ".join(f'{row.get("source_name", "Nguồn")}: {row.get("status", "?")}' for row in limited[:8])
    if len(limited) > 8:
        limits += f"; và {len(limited) - 8} nguồn khác"
    method = "Nguồn xếp xã hội trước website; từng mục ghi phương thức thu thập. Chỉ mục tìm kiếm không chứng minh đã đọc bài gốc hoặc đo tương tác."
    if limits:
        method += " Chưa lấy trực tiếp: " + limits + ". Xem bảng trạng thái trong Excel để biết lỗi và cách khắc phục."
    if own_company.get("name"):
        method += f' Ý tưởng là gợi ý cho {own_company["name"]} và cần xác minh với khách hàng.'
    font_link = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=K2D:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
    draft = not require_screenshots
    draft_label = '<span>Bản nháp · cần 5 ảnh chụp nguồn</span>' if draft else '<span>5 ảnh chụp nguồn đã kiểm</span>'
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Báo cáo phân tích đối thủ | {_h(period)}</title>{font_link}<style>{STYLE}</style></head><body>
<div class="topline"></div><main class="shell"><div class="mast"><div class="brandmark"><span class="mark" aria-hidden="true"></span> Market intelligence</div><div class="edition">Bản phân tích · {produced:%d.%m.%Y}</div></div>
<header class="hero"><div class="kicker"><span class="dot"></span> {_h(meta.get("industry"))}</div><h1>Báo cáo phân tích đối thủ</h1><p class="lede">Theo dõi { _h(intro) } trong kỳ { _h(period) }.</p><div class="hero-meta"><span>{_h(period)}</span><span>{len(companies)} đối thủ</span>{draft_label}<span>Đọc khoảng 3 phút</span></div></header>
<nav class="jump" aria-label="Đi tới nội dung"><a href="#summary">Tóm tắt</a><a href="#topics">Chủ đề</a><a href="#competitors">Đối thủ</a><a href="#gaps">Góc bỏ trống</a><a href="#ideas">Ý tưởng</a><a href="#sources">Nguồn</a></nav>
<section class="summary" id="summary"><span class="eyebrow">Tóm tắt nhanh</span><h2>Bức tranh trong một phút</h2><p>{_h(coverage_note)}</p></section>
<section class="report-section" id="topics"><div class="section-header"><div><span class="eyebrow">Tín hiệu thị trường</span><h2>{len(topic_rows) if topic_rows else "Chưa có"} chủ đề nổi bật</h2></div><span class="section-index" aria-hidden="true">01</span></div><div class="topic-list">{topic_html}</div></section>
<section class="report-section" id="competitors"><div class="section-header"><div><span class="eyebrow">Bản đồ hoạt động</span><h2>Đối thủ đang làm gì?</h2></div><span class="section-index" aria-hidden="true">02</span></div><div class="competitor-list">{competitor_html}</div></section>
<section class="report-section" id="gaps"><div class="section-header"><div><span class="eyebrow">Giả thuyết cần kiểm chứng</span><h2>3 góc nội dung còn bỏ trống</h2></div><span class="section-index" aria-hidden="true">03</span></div>{gaps_html}</section>
<section class="report-section" id="ideas"><div class="section-header"><div><span class="eyebrow">Kế hoạch nội dung</span><h2>5 ý tưởng cho tuần tới</h2></div><span class="section-index" aria-hidden="true">04</span></div><div class="dark-panel">{ideas_html}</div></section>
<section class="sources" id="sources"><div class="section-header"><div><span class="eyebrow">Minh bạch dữ liệu</span><h2>Nguồn thu thập thông tin</h2></div><span class="section-index" aria-hidden="true">05</span></div><ol class="source-list">{sources_html}</ol><p class="method">{_h(method)}</p></section>
<footer class="foot">Báo cáo phân tích đối thủ · Cập nhật {produced:%d/%m/%Y}</footer></main></body></html>'''
