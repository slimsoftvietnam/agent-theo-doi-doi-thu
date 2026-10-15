from __future__ import annotations

import html
import json
from pathlib import Path

from .util import atomic_write
from .xlsx_writer import write_xlsx


def _join(values) -> str:
    return ", ".join(values or []) or "—"


def _engagement(value: dict) -> str:
    if not value:
        return "Không khả dụng"
    return ", ".join(f"{key}: {number:,}" for key, number in value.items())


def _access_diagnosis(row: dict) -> tuple[str, str]:
    status = row.get("status", "")
    kind = row.get("source_type", "")
    error = row.get("error", "")
    if status == "HEALTHY" and row.get("item_count", 0) == 0:
        return (
            "Truy cập được, chưa ghi nhận mục mới trong cửa sổ theo dõi.",
            "Kiểm tra trang tin, RSS/sitemap và tăng lookback_hours nếu cần xem kỳ dài hơn.",
        )
    if status == "HEALTHY":
        return ("Đã lấy dữ liệu từ nguồn được phép.", "Không cần xử lý.")
    if status == "SEARCH_INDEX_ONLY":
        reason = "Chỉ tìm được qua chỉ mục web; chưa lấy trực tiếp bài đăng hoặc chỉ số tương tác. Kết quả có thể là nội dung nhắc đến thương hiệu từ tài khoản khác."
        if kind == "youtube":
            if "CHANNEL_ID_REQUIRED" in error:
                reason += " Chưa xác nhận channel ID."
            return reason, "Xác nhận URL/channel ID chính thức và đặt YOUTUBE_API_KEY để dùng YouTube Data API; kiểm tra lại RSS."
        if kind == "facebook":
            if "PAGE_ID_OR_TOKEN_REQUIRED" in error:
                reason += " Thiếu Page ID hoặc Page Access Token hợp lệ."
            return reason, "Xác nhận fanpage chính thức và cấp quyền Graph API phù hợp; nếu không có quyền, tiếp tục dùng chỉ mục web."
        if kind == "tiktok":
            return reason, "Xác nhận tài khoản; dùng Display API khi chủ tài khoản cấp quyền, Research API khi được TikTok phê duyệt, hoặc feed được phép."
        return reason, "Cấu hình Brave Search API hoặc Google Custom Search để tăng phạm vi; vẫn cần xác minh trang gốc."
    if "ROBOTS_DISALLOWED" in error:
        return "Website từ chối crawler qua robots.txt.", "Dùng RSS/API công khai hoặc đề nghị chủ website cấp feed/quyền phù hợp."
    if error.startswith("HTTP_") or "NETWORK_" in error:
        return f"Yêu cầu nguồn gặp lỗi {error}.", "Kiểm tra URL, kết nối và tình trạng nguồn; thử lại hoặc thêm RSS/API thay thế."
    if status == "DISABLED":
        return "Nguồn đang tắt và chưa được kiểm thử.", "Đặt enabled=true nếu cần theo dõi."
    return f"Chưa lấy được nguồn: {error or status}.", "Kiểm tra cấu hình URL, quyền API hoặc feed được phép."


def build_markdown(payload: dict) -> str:
    meta, items, analysis, checks, peas = payload["meta"], payload["items"], payload["analysis"], payload["source_checks"], payload["peas"]
    lines = [
        f"# Bản tin thị trường: {meta['industry']}", "",
        f"- Lượt chạy: `{meta['run_id']}`",
        f"- Thời điểm tạo: {meta['produced_at']}",
        f"- Kỳ theo dõi: {meta['lookback_hours']} giờ; tần suất {meta['frequency']}",
        f"- Thu thập thô: **{meta['raw_items_received']}**; loại không liên quan: **{meta['filtered_out']}**; tin mới đạt ngưỡng: **{len(items)}**; trùng đã loại: **{meta['duplicates']}**", "",
        "## Tin nổi bật", "",
    ]
    if not items:
        lines.append("Không có tin mới đạt ngưỡng liên quan trong lượt chạy này.")
    for item in items[:12]:
        evidence = item.get("evidence") or {}
        lines.extend([
            f"### [{item['kind']}] {item['title']}", "",
            f"- Nguồn/ngày: {item['source_name']} · {item.get('published_at') or 'Không có ngày'}",
            f"- Đối thủ: {_join(item.get('competitors'))}; chủ đề: {_join(item.get('topics'))}",
            f"- Tương tác: {_engagement(item.get('engagement', {}))}",
            f"- Bằng chứng: {evidence.get('collection_tier', 'UNKNOWN')} · {evidence.get('collection_method', 'không rõ')}",
            f"- Tóm tắt từ nguồn: {item.get('summary') or 'Nguồn không cung cấp mô tả.'}",
            f"- [Mở nguồn gốc]({item['canonical_url']})", "",
        ])
    lines.extend(["## Đối thủ đang làm gì", ""])
    if analysis["competitor_activity"]:
        lines.extend(f"- **{row['name']}**: {row['count']} mục mới." for row in analysis["competitor_activity"])
    else:
        lines.append("- Chưa có hoạt động mới khớp danh sách đối thủ.")
    lines.extend(["", "## Xu hướng mới — nhận định từ dữ liệu", "", f"> {analysis['comparison_note']}", ""])
    if analysis["trends"]:
        for row in analysis["trends"][:10]:
            pct = "mới xuất hiện" if row["change_pct"] is None else f"{row['change_pct']:+.1f}%"
            lines.append(f"- **{row['topic']}**: {row['current']} so với {row['previous']} kỳ trước, {row['direction']} ({pct}).")
    else:
        lines.append("- Chưa đủ dữ liệu để so sánh xu hướng.")
    for title, key in (("Cơ hội", "opportunities"), ("Rủi ro", "risks"), ("Đề xuất hành động", "actions")):
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {value}" for value in analysis[key])
    lines.extend(["", "## Đánh giá PEAS", "", "| Thành phần | Kết quả |", "|---|---|"])
    for key in ("P", "E", "A", "S"):
        lines.append(f"| {key} | {json.dumps(peas[key], ensure_ascii=False)} |")
    lines.extend(["", "## Trạng thái nguồn", "", "| Nguồn | Loại | Trạng thái | Số mục | Phương thức | Ghi chú |", "|---|---|---:|---:|---|---|"])
    for row in checks:
        lines.append(f"| {row['source_name']} | {row['source_type']} | {row['status']} | {row['item_count']} | {row['method'] or '—'} | {row['error'] or '—'} |")
    lines.extend(["", "## Nguồn chưa lấy trực tiếp và cách khắc phục", ""])
    for row in checks:
        if row["status"] != "HEALTHY":
            reason, remedy = _access_diagnosis(row)
            lines.append(f"- **{row['source_name']}** ({row['status']}, {row['item_count']} mục): {reason} Cách khắc phục: {remedy}")
    lines.extend(["", "## Phạm vi và giới hạn", "", "- Chỉ số tương tác chỉ xuất hiện khi API/feed cung cấp hợp lệ; giá trị thiếu không được ước đoán.", "- `SEARCH_INDEX_ONLY` chỉ chứng minh URL đã xuất hiện trong chỉ mục tìm kiếm, không chứng minh đã quét trực tiếp nền tảng và không bảo đảm đầy đủ.", "- `SỰ KIỆN` là phân loại heuristic từ câu chữ nguồn. `NHẬN ĐỊNH` và mục xu hướng cần được con người kiểm chứng trước quyết định lớn.", "- Nguồn `LIMITED`, `MANUAL_REVIEW` hoặc `ERROR` chưa được coi là đã quét thành công.", ""])
    return "\n".join(lines)


def build_html(markdown_payload: dict) -> str:
    meta, items, analysis, checks, peas = markdown_payload["meta"], markdown_payload["items"], markdown_payload["analysis"], markdown_payload["source_checks"], markdown_payload["peas"]
    cards = "".join(f'<div class="card"><span>{html.escape(label)}</span><strong>{value}</strong></div>' for label, value in (("Tin mới", len(items)), ("Trùng đã loại", meta["duplicates"]), ("Nguồn truy cập", f"{peas['P']['source_access_rate_pct']}%"), ("Bằng chứng đủ", f"{peas['P']['evidence_complete_pct']}%")))
    item_html = "".join(f'''<article><div class="badge">{html.escape(item['kind'])}</div><h3>{html.escape(item['title'])}</h3><p class="meta">{html.escape(item['source_name'])} · {html.escape(item.get('published_at') or 'Không có ngày')}</p><p>{html.escape(item.get('summary') or 'Nguồn không cung cấp mô tả.')}</p><p><b>Đối thủ:</b> {html.escape(_join(item.get('competitors')))} · <b>Chủ đề:</b> {html.escape(_join(item.get('topics')))}</p><p><b>Bằng chứng:</b> {html.escape((item.get('evidence') or {}).get('collection_tier', 'UNKNOWN'))} · {html.escape((item.get('evidence') or {}).get('collection_method', 'không rõ'))}</p><a href="{html.escape(item['canonical_url'], quote=True)}">Mở nguồn gốc</a></article>''' for item in items[:20]) or "<p>Không có tin mới đạt ngưỡng liên quan.</p>"
    trends = "".join(f"<li><b>{html.escape(row['topic'])}</b>: {row['current']} so với {row['previous']} kỳ trước ({html.escape(row['direction'])}).</li>" for row in analysis["trends"][:10]) or "<li>Chưa đủ dữ liệu so sánh.</li>"
    source_rows = "".join(f"<tr><td>{html.escape(row['source_name'])}</td><td>{html.escape(row['source_type'])}</td><td class='{row['status'].lower()}'>{html.escape(row['status'])}</td><td>{row['item_count']}</td><td>{html.escape(row['method'] or '—')}</td><td>{html.escape(row['error'] or '—')}</td></tr>" for row in checks)
    diagnosis_rows = "".join(f"<tr><td>{html.escape(row['source_name'])}</td><td>{html.escape(_access_diagnosis(row)[0])}</td><td>{html.escape(_access_diagnosis(row)[1])}</td></tr>" for row in checks if row["status"] != "HEALTHY")
    lists = lambda values: "".join(f"<li>{html.escape(value)}</li>" for value in values)
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bản tin thị trường</title><style>
body{{font-family:Arial,sans-serif;margin:0;background:#f5f7fb;color:#172033}}main{{max-width:1080px;margin:auto;padding:32px}}h1{{font-size:30px;margin-bottom:8px}}h2{{margin-top:38px;border-bottom:2px solid #dbe4f0;padding-bottom:8px}}.muted,.meta{{color:#667085}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:24px 0}}.card,article{{background:white;border:1px solid #e4e7ec;border-radius:12px;padding:18px}}.card span{{display:block;color:#667085}}.card strong{{font-size:24px}}article{{margin:12px 0}}.badge{{display:inline-block;background:#e8f1fb;color:#1f4e78;padding:4px 8px;border-radius:99px;font-size:12px;font-weight:bold}}a{{color:#0563c1}}table{{width:100%;border-collapse:collapse;background:#fff}}th,td{{padding:10px;border-bottom:1px solid #e4e7ec;text-align:left}}th{{background:#1f4e78;color:white}}.healthy{{color:#067647}}.search_index_only,.limited,.manual_review{{color:#b54708}}.error{{color:#b42318}}@media(max-width:700px){{main{{padding:18px}}table{{font-size:12px}}}}
</style></head><body><main><h1>Bản tin thị trường: {html.escape(meta['industry'])}</h1><p class="muted">{html.escape(meta['produced_at'])} · kỳ {meta['lookback_hours']} giờ · run {html.escape(meta['run_id'])}</p><section class="grid">{cards}</section><h2>Tin nổi bật</h2>{item_html}<h2>Xu hướng mới — nhận định từ dữ liệu</h2><p class="muted">{html.escape(analysis['comparison_note'])}</p><ul>{trends}</ul><h2>Cơ hội</h2><ul>{lists(analysis['opportunities'])}</ul><h2>Rủi ro</h2><ul>{lists(analysis['risks'])}</ul><h2>Đề xuất hành động</h2><ul>{lists(analysis['actions'])}</ul><h2>Trạng thái nguồn</h2><table><thead><tr><th>Nguồn</th><th>Loại</th><th>Trạng thái</th><th>Mục</th><th>Phương thức</th><th>Ghi chú</th></tr></thead><tbody>{source_rows}</tbody></table><h2>Nguồn chưa lấy trực tiếp và cách khắc phục</h2><table><thead><tr><th>Nguồn</th><th>Lý do</th><th>Cách khắc phục</th></tr></thead><tbody>{diagnosis_rows}</tbody></table><h2>Đánh giá PEAS</h2><pre>{html.escape(json.dumps(peas, ensure_ascii=False, indent=2))}</pre></main></body></html>'''


def write_reports(output_dir: str | Path, payload: dict) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    base = f"ban-tin-thi-truong-{payload['meta']['run_id']}"
    markdown = build_markdown(payload)
    md_path = atomic_write(output / f"{base}.md", markdown)
    html_path = atomic_write(output / f"{base}.html", build_html(payload))

    summary_rows = [["Chỉ số", "Giá trị"], ["Ngành", payload["meta"]["industry"]], ["Run ID", payload["meta"]["run_id"]], ["Thời điểm", payload["meta"]["produced_at"]], ["Tin mới", len(payload["items"])], ["Trùng đã loại", payload["meta"]["duplicates"]], ["Tỷ lệ truy cập nguồn", payload["peas"]["P"]["source_access_rate_pct"] / 100], ["Tỷ lệ bằng chứng đủ", payload["peas"]["P"]["evidence_complete_pct"] / 100]]
    summary_rows += [["Đối thủ: " + row["name"], row["count"]] for row in payload["analysis"]["competitor_activity"]]
    data_rows = [["Ngày đăng", "Loại", "Tiêu đề", "Nguồn", "Đối thủ", "Chủ đề", "Điểm liên quan", "Tương tác", "Mức bằng chứng", "Phương thức", "Liên kết nguồn"]]
    for item in payload["items"]:
        evidence = item.get("evidence") or {}
        data_rows.append([item.get("published_at"), item["kind"], item["title"], item["source_name"], _join(item.get("competitors")), _join(item.get("topics")), item["relevance_score"], _engagement(item.get("engagement", {})), evidence.get("collection_tier", "UNKNOWN"), evidence.get("collection_method", ""), item["canonical_url"]])
    source_rows = [["Nguồn", "Loại", "Trạng thái", "Số mục", "Phương thức", "Ghi chú", "Lý do", "Cách khắc phục"]] + [[row["source_name"], row["source_type"], row["status"], row["item_count"], row["method"], row["error"], *_access_diagnosis(row)] for row in payload["source_checks"]]
    xlsx_path = write_xlsx(output / f"{base}.xlsx", [
        {"name": "Tổng quan", "rows": summary_rows, "widths": [34, 42], "cell_styles": {"B7": 5, "B8": 5}},
        {"name": "Dữ liệu", "rows": data_rows, "widths": [20, 16, 55, 26, 28, 30, 14, 28, 22, 28, 55], "hyperlink_columns": [11]},
        {"name": "Nguồn", "rows": source_rows, "widths": [32, 18, 18, 12, 28, 42, 56, 72]},
    ])
    json_path = output / f"{base}.json"
    atomic_write(json_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return {"markdown": str(md_path.resolve()), "html": str(html_path.resolve()), "xlsx": str(xlsx_path.resolve()), "json": str(json_path.resolve())}
