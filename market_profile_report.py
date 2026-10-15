"""Curate a market snapshot from a monitor run and render an evidence-led HTML report.

Usage: python market_profile_report.py input.json output-directory
The JSON companion file is intentionally suitable for the Artifact Tool Excel builder.
"""
from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit


BRANDS = ["Base.vn", "MISA AMIS", "1Office", "ECOUNT", "FastWork", "CloudGO", "Odoo"]
TOPICS = {
    "AI và tự động hóa": [r"\bai\b", r"agent", r"tự động", r"automation", r"no.code", r"low.code", r"thông minh"],
    "ERP, quy trình và vận hành": [r"\berp\b", r"quy trình", r"công việc", r"dự án", r"vận hành", r"sản xuất", r"tồn kho", r"dms", r"kho vận", r"inventory"],
    "CRM, bán hàng và khách hàng": [r"\bcrm\b", r"bán hàng", r"khách hàng", r"\blead\b", r"sales", r"phân phối", r"chăm sóc"],
    "Nhân sự, kế toán và tuân thủ": [r"nhân sự", r"hrm", r"hrms", r"chấm công", r"tiền lương", r"kế toán", r"thuế", r"hóa đơn", r"tài chính", r"chữ ký"],
    "Triển khai và hiệu quả": [r"triển khai", r"chi phí", r"hiệu quả", r"chuyển đổi số", r"tích hợp", r"case study", r"thực hành", r"hướng dẫn", r"implementation"],
}

MANUAL_OFFICIAL = [
    {
        "brand": "1Office", "date": "2026-10-13", "title": "Hệ thống quản lý nhân sự (HRMS) là gì? Chức năng và cách lựa chọn",
        "url": "https://1office.vn/he-thong-quan-ly-nhan-su", "note": "Trang chính thức; ngày đăng hiển thị trên bài",
    },
    {
        "brand": "Odoo", "date": "2026-10-06", "title": "From Operational Chaos to Complete Clarity: How UV Engineering Mastered Inventory and Production Flow",
        "url": "https://www.odoo.com/id_ID/blog/customer-reviews-6/from-operational-chaos-to-complete-clarity-how-uv-engineering-mastered-inventory-and-production-flow-2466",
        "note": "Trang chính thức; ví dụ quốc tế, không đại diện thị trường Việt Nam",
    },
    {
        "brand": "Odoo", "date": "2026-10-02", "title": "Automating 6 Months of Inventory Backlog in 2.5 Months with Odoo",
        "url": "https://www.odoo.com/blog/customer-reviews-6/automating-6-months-of-inventory-backlog-in-2-5-months-with-odoo-2419",
        "note": "Trang chính thức; ví dụ Nhật Bản, không đại diện thị trường Việt Nam",
    },
]


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def brand_for(item: dict) -> str:
    sid = item.get("source_id", "")
    for code, brand in (("base", "Base.vn"), ("misa", "MISA AMIS"), ("1office", "1Office"), ("ecount", "ECOUNT"), ("fastwork", "FastWork"), ("cloudgo", "CloudGO"), ("odoo", "Odoo")):
        if sid.endswith(code):
            return brand
    return "Ngành"


def is_acceptable(item: dict) -> bool:
    sid = item.get("source_id", "")
    title = norm(item.get("title", ""))
    url = item.get("canonical_url", "")
    host = (urlsplit(url).hostname or "").lower()
    if sid.startswith("site-"):
        return host in {"base.vn", "amis.misa.vn", "1office.vn", "www.ecount.com", "fastwork.vn", "cloudgo.vn", "www.odoo.com"} and urlsplit(url).path not in {"/", "/vn/", "/blog"}
    if sid.startswith("news-"):
        if sid == "news-industry":
            return any(re.search(pat, title) for pat in (r"\berp\b", r"\bcrm\b", r"quan tri", r"\bai\b"))
        brand = brand_for(item)
        aliases = {
            "Base.vn": ["base.vn", "base vietnam"], "MISA AMIS": ["misa amis", "amis"],
            "1Office": ["1office"], "ECOUNT": ["ecount"], "FastWork": ["fastwork.vn", "fastwork"],
            "CloudGO": ["cloudgo"], "Odoo": ["odoo"],
        }
        return any(alias in title for alias in aliases.get(brand, []))
    # Search-index social results are only retained from identified channels. They
    # remain leads, never direct platform observations or engagement measurements.
    if sid in {"fb-base", "fb-1office", "fb-misa", "fb-odoo"}:
        return True
    if sid in {"yt-misa", "yt-1office"}:
        return "misa" in title or "1office" in title
    return False


def primary_topic(title: str) -> str:
    value = title.casefold()
    for topic, patterns in TOPICS.items():
        if any(re.search(pattern, value) for pattern in patterns):
            return topic
    return "Khác"


def row(item: dict) -> dict:
    sid = item.get("source_id", "")
    if sid.startswith("site-"):
        tier, channel = "Nguồn chính thức", "Website"
    elif sid.startswith("news-"):
        tier, channel = "Chỉ mục tin tức", "Tin ngành"
    else:
        tier, channel = "Tín hiệu chỉ mục; chưa xác minh bài gốc", {"fb": "Facebook", "yt": "YouTube"}.get(sid[:2], "TikTok")
    date = (item.get("published_at") or "")[:10]
    return {
        "brand": brand_for(item), "date": date, "title": item.get("title", ""),
        "url": item.get("canonical_url", ""), "topic": primary_topic(item.get("title", "")),
        "channel": channel, "tier": tier, "source": item.get("source_name", ""),
        "note": "Ngày RSS/chỉ mục; cần kiểm tra bài gốc" if tier != "Nguồn chính thức" else "Ngày từ feed hoặc metadata trang; một số trang có thể cập nhật bài cũ",
    }


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def build(input_path: Path, output_dir: Path) -> tuple[Path, Path]:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    produced = datetime.fromisoformat(raw["meta"]["produced_at"].replace("Z", "+00:00"))
    cutoff = (produced - timedelta(hours=int(raw["meta"]["lookback_hours"]))).date().isoformat()
    evidence = [row(item) for item in raw["items"] if is_acceptable(item)]
    known = {(norm(x["brand"]), norm(x["title"])) for x in evidence}
    for item in MANUAL_OFFICIAL:
        if item["date"] < cutoff or item["date"] > produced.date().isoformat():
            continue
        key = (norm(item["brand"]), norm(item["title"]))
        if key in known:
            continue
        known.add(key)
        evidence.append({**item, "topic": primary_topic(item["title"]), "channel": "Website", "tier": "Nguồn chính thức; xác minh thủ công", "source": item["brand"], "note": item["note"]})
    # Google News can issue distinct index URLs for the same page/post.
    evidence.sort(key=lambda x: x["date"], reverse=True)
    deduped, seen = [], set()
    for item in evidence:
        key = (item["brand"], item["channel"], norm(re.sub(r"[^\w ]", "", item["title"]))[:130])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    evidence = deduped
    core = [x for x in evidence if x["channel"] in {"Website", "Tin ngành"}]
    social = [x for x in evidence if x["channel"] in {"Facebook", "YouTube", "TikTok"}]
    topic_counts = Counter(x["topic"] for x in core)
    brand_counts = Counter(x["brand"] for x in core if x["brand"] != "Ngành")
    coverage = []
    for check in raw["source_checks"]:
        sid = check["source_id"]
        platform = "Website" if sid.startswith("site-") else "Tin ngành" if sid.startswith("news-") else "YouTube" if sid.startswith("yt-") else "Facebook" if sid.startswith("fb-") else "TikTok"
        brand = brand_for(check)
        reason = check.get("error", "") or ("Không thấy mục mới đủ ngày/điều kiện" if not check.get("item_count") else "")
        if platform == "Facebook":
            remedy = "Cần quyền Graph API phù hợp hoặc rà soát thủ công bài công khai trên fanpage; chỉ mục không cấp số tương tác."
        elif platform == "TikTok":
            remedy = "Xác nhận tài khoản chính thức; dùng Research API khi được duyệt hoặc kiểm tra thủ công. Display API chỉ áp dụng tài khoản ủy quyền."
        elif platform == "YouTube":
            remedy = "Xác minh channel ID và thử lại RSS uploads/Data API key; hiện chỉ có tín hiệu chỉ mục."
        elif platform == "Website" and "HTTP_403" in reason:
            remedy = "Bài gốc chặn collector (403). Dùng RSS/API được cấp phép hoặc kiểm chứng thủ công; không vượt cơ chế chặn."
        elif platform == "Website" and not check.get("item_count"):
            remedy = "Kiểm tra RSS/sitemap hoặc mục blog cụ thể; trang có thể không có bài mới đủ ngày hay thiếu metadata ngày đăng."
        else:
            remedy = "Đối chiếu URL gốc khi trích dẫn; cấu hình thêm API/RSS nếu có."
        coverage.append({"brand": brand, "platform": platform, "status": check["status"], "method": check.get("method", ""), "raw_count": int(check.get("item_count") or 0), "reason": reason, "remedy": remedy})
    gaps = [
        {"angle": "So sánh chi phí sở hữu và công sức triển khai theo quy mô 20/100/500 người", "why": "Mẫu quan sát có nhiều bài danh sách tính năng và bảng giá riêng lẻ; thiếu phép so sánh cùng giả định về phí triển khai, tích hợp, đào tạo và vận hành.", "format": "Bảng tính tương tác + bài giải thích phương pháp", "caveat": "Giả thuyết từ mẫu 30 ngày; cần rà soát SEO và dữ liệu báo giá trước khi xuất bản."},
        {"angle": "Nhật ký triển khai tại SME Việt Nam: trước/sau 90 ngày với số đo quy trình", "why": "Odoo có case study định lượng quốc tế; các tin Việt Nam quan sát được thiên về tính năng, hội thảo và hướng dẫn. Cơ hội nằm ở số liệu thực tế bản địa.", "format": "Case study 3 phần + video 60 giây", "caveat": "Chỉ làm khi khách hàng đồng ý công bố và có số liệu đối soát."},
        {"angle": "Playbook nối CRM–ERP–kế toán và làm sạch dữ liệu trước khi bật AI Agent", "why": "CloudGO đã nói về tích hợp; khoảng trống hẹp hơn là quy trình thực thi có sơ đồ dữ liệu, lỗi thường gặp, phân quyền và kiểm thử đầu-cuối.", "format": "Checklist tải về + demo quy trình", "caveat": "Không khẳng định đối thủ chưa có nội dung ngoài các nguồn đã tiếp cận."},
    ]
    model = {
        "as_of": produced.strftime("%Y-%m-%d %H:%M UTC"), "from": cutoff, "to": produced.date().isoformat(),
        "raw_count": raw["summary"]["received"], "curated_count": len(evidence), "core_count": len(core), "social_index_count": len(social),
        "topics": [{"name": k, "count": v} for k, v in topic_counts.most_common()],
        "brands": [{"name": b, "count": brand_counts.get(b, 0)} for b in BRANDS],
        "evidence": evidence, "coverage": coverage, "gaps": gaps,
        "method_note": "Chỉ đếm mục mới của lượt chạy trong cửa sổ tìm kiếm 30 ngày; lượt sau loại nội dung đã lưu lịch sử. Tần suất bài không phải thước đo nhu cầu thị trường. Facebook/YouTube/TikTok chưa được quét trực tiếp; tín hiệu chỉ mục không có số tương tác.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "market-brief-data.json"
    html_path = output_dir / f"ban-tin-thi-truong-erp-crm-{produced.date().isoformat()}.html"
    json_path.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(render_html(model), encoding="utf-8")
    return json_path, html_path


def render_html(model: dict) -> str:
    def item_link(x: dict) -> str:
        return f'<a href="{esc(x["url"])}" target="_blank" rel="noopener">{esc(x["title"])}</a>'

    top = [x for x in model["evidence"] if x["channel"] == "Website"][:8]
    social_rank = {"Facebook": 0, "TikTok": 1, "YouTube": 2, "Website": 3, "Tin ngành": 4}
    social_top = sorted(
        (x for x in model["evidence"] if x["channel"] in {"Facebook", "TikTok", "YouTube"}),
        key=lambda x: x["date"], reverse=True,
    )[:8]
    topics_html = "".join(f'<div class="barrow"><span>{esc(x["name"])}</span><div class="bar"><i style="width:{min(100, x["count"] * 100 / max(1, model["topics"][0]["count"])):.0f}%"></i></div><strong>{x["count"]}</strong></div>' for x in model["topics"])
    brands_html = "".join(f'<div class="brand"><b>{esc(x["name"])}</b><span>{x["count"]} bài cốt lõi</span></div>' for x in model["brands"])
    top_html = "".join(f'<article class="story"><small>{esc(x["date"])} · {esc(x["brand"])} · {esc(x["topic"])}</small><h3>{item_link(x)}</h3></article>' for x in top)
    social_html = "".join(f'<article class="story"><small>{esc(x["date"])} · {esc(x["brand"])} · {esc(x["channel"])} · {esc(x["tier"])}</small><h3>{item_link(x)}</h3></article>' for x in social_top)
    gaps_html = "".join(f'<article class="gap"><div class="gap-no">0{i+1}</div><div><h3>{esc(x["angle"])}</h3><p>{esc(x["why"])}</p><small>Định dạng: {esc(x["format"])}. {esc(x["caveat"])}</small></div></article>' for i, x in enumerate(model["gaps"]))
    coverage_html = "".join(f'<tr><td>{esc(x["brand"])}</td><td>{esc(x["platform"])}</td><td><span class="status {"ok" if x["status"] == "HEALTHY" else "index"}">{esc(x["status"])}</span></td><td>{esc(x["method"])}</td><td>{x["raw_count"]}</td><td>{esc(x["reason"])}</td><td>{esc(x["remedy"])}</td></tr>' for x in sorted(model["coverage"], key=lambda x: (social_rank.get(x["platform"], 5), x["brand"])))
    evidence_html = "".join(f'<tr data-brand="{esc(x["brand"])}" data-channel="{esc(x["channel"])}"><td>{esc(x["date"])}</td><td>{esc(x["brand"])}</td><td>{esc(x["channel"])}</td><td>{item_link(x)}</td><td>{esc(x["topic"])}</td><td>{esc(x["tier"])}</td></tr>' for x in sorted(sorted(model["evidence"], key=lambda x: x["date"], reverse=True), key=lambda x: social_rank.get(x["channel"], 5)))
    social_note = "Trong lần chạy này không có bài TikTok/Facebook/YouTube nào được xác nhận bằng API/feed trực tiếp. Một số kết quả được phát hiện qua chỉ mục tìm kiếm; không dùng chúng để tính chủ đề cốt lõi."
    return f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bản tin thị trường ERP & CRM</title><style>
    :root{{--ink:#152039;--muted:#64748b;--paper:#f6f8fc;--line:#e4eaf3;--purple:#6748d8;--blue:#24a7cc;--navy:#101a34;--mint:#d7f6ed}}
    *{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 'Segoe UI',Arial,sans-serif}}a{{color:#3f35ad;text-decoration:none}}a:hover{{text-decoration:underline}}.hero{{background:radial-gradient(circle at 85% 15%,#493c9c 0,transparent 32%),linear-gradient(125deg,#101a34,#1d2b53);color:#fff;padding:54px max(30px,calc((100vw - 1180px)/2)) 48px}}.eyebrow{{letter-spacing:.16em;text-transform:uppercase;font-size:12px;color:#b5c6ff;font-weight:700}}h1{{font-size:clamp(32px,4vw,52px);line-height:1.12;max-width:850px;margin:12px 0}}.hero p{{color:#d3dcf5;max-width:780px;margin:0}}.hero-meta{{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}}.pill{{border:1px solid #7180af;border-radius:999px;padding:6px 12px;font-size:12px;color:#e2e9ff}}main{{max-width:1180px;margin:auto;padding:28px 24px 70px}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:-62px;position:relative}}.kpi{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 12px 35px #1d2b5310}}.kpi strong{{display:block;font-size:32px;line-height:1.2;color:#282060}}.kpi span{{color:var(--muted);font-size:13px}}section{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:26px;margin-top:22px;box-shadow:0 6px 24px #1d2b5308}}h2{{font-size:23px;margin:0 0 8px}}.sub{{color:var(--muted);margin:0 0 20px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}.lead{{font-size:18px;line-height:1.65;margin:0}}.insight{{background:#eef0ff;border-left:4px solid var(--purple);padding:15px 18px;border-radius:10px;margin-top:18px}}.barrow{{display:grid;grid-template-columns:190px 1fr 30px;gap:12px;align-items:center;margin:13px 0;font-size:13px}}.bar{{height:10px;background:#edf1f8;border-radius:20px;overflow:hidden}}.bar i{{display:block;height:100%;border-radius:20px;background:linear-gradient(90deg,var(--purple),var(--blue))}}.brandgrid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.brand{{background:#f8f9fd;border:1px solid var(--line);border-radius:12px;padding:13px}}.brand b,.brand span{{display:block}}.brand span{{font-size:12px;color:var(--muted)}}.storygrid{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.story{{border:1px solid var(--line);border-radius:12px;padding:16px}}.story small,.gap small{{color:var(--muted)}}.story h3,.gap h3{{font-size:16px;margin:7px 0 0}}.gap{{display:flex;gap:18px;padding:18px 0;border-top:1px solid var(--line)}}.gap:first-of-type{{border-top:0}}.gap-no{{font-size:28px;font-weight:800;color:#c7baf8;line-height:1}}.gap p{{margin:7px 0}}.warning{{border-radius:12px;background:#fff7e8;border:1px solid #f4ddb1;padding:16px 18px;color:#664c1c}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th{{background:var(--navy);color:#fff;text-align:left;white-space:nowrap}}th,td{{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}}tbody tr:nth-child(even){{background:#fafbfe}}.status{{font-size:11px;font-weight:700;border-radius:999px;padding:4px 7px;white-space:nowrap}}.status.ok{{background:#dff5e9;color:#126d45}}.status.index{{background:#fff0d8;color:#966000}}.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:15px 0}}select,input{{background:#fff;border:1px solid #cbd5e1;border-radius:8px;padding:9px 12px;font:inherit}}input{{min-width:250px;flex:1}}footer{{font-size:12px;color:var(--muted);margin-top:26px}}@media(max-width:800px){{.kpis,.grid,.storygrid{{grid-template-columns:1fr 1fr}}.brandgrid{{grid-template-columns:1fr 1fr}}}}@media(max-width:580px){{.kpis,.grid,.storygrid{{grid-template-columns:1fr}}.kpis{{margin-top:0}}.hero{{padding:36px 22px}}main{{padding:20px 14px}}.barrow{{grid-template-columns:130px 1fr 25px}}}}
    </style></head><body><header class="hero"><div class="eyebrow">Social-first / ERP · CRM · Business software</div><h1>Radar mạng xã hội đối thủ</h1><p>Theo dõi Base.vn, MISA AMIS, 1Office, ECOUNT, FastWork, CloudGO và Odoo. Facebook, TikTok, YouTube được trình bày trước; website và tin ngành là tầng đối chiếu. Tín hiệu chỉ mục không đồng nghĩa đã xem bài gốc.</p><div class="hero-meta"><span class="pill">{esc(model["from"])} → {esc(model["to"])}</span><span class="pill">Cập nhật {esc(model["as_of"])}</span><span class="pill">Ưu tiên xã hội · 7 đối thủ</span></div></header><main>
    <div class="kpis"><div class="kpi"><strong>{model["social_index_count"]}</strong><span>tín hiệu xã hội qua chỉ mục, chưa xác minh</span></div><div class="kpi"><strong>{model["core_count"]}</strong><span>bài website/tin ngành để đối chiếu</span></div><div class="kpi"><strong>{len(model["coverage"])}</strong><span>nguồn được thử truy cập</span></div><div class="kpi"><strong>{model["raw_count"]}</strong><span>mục thô trước lọc</span></div></div>
    <section><h2>Tín hiệu Facebook · TikTok · YouTube</h2><p class="sub">Ưu tiên xem trước khi mở website. Đây là manh mối từ chỉ mục tìm kiếm, không phải bài đăng/video đã được xác minh trên nền tảng; ngày và tương tác cần đối chiếu tại bài gốc.</p><div class="storygrid">{social_html or '<p>Chưa có tín hiệu xã hội đủ điều kiện trong lượt chạy này.</p>'}</div></section>
    <section><h2>Đối chiếu từ website và tin ngành</h2><p class="sub">Bổ sung bối cảnh khi dữ liệu mạng xã hội chưa xác minh được; không phải khảo sát nhu cầu người mua.</p><div class="grid"><div><p class="lead">Trong nguồn website/tin ngành, các nhà cung cấp nhấn mạnh <b>quản trị trên một nền tảng</b>, <b>AI/tự động hóa trong quy trình</b> và <b>giảm ma sát ở nghiệp vụ hàng ngày</b>. MISA AMIS có nội dung kế toán, hóa đơn và bán hàng; Base và 1Office nói về quy trình/nhân sự; CloudGO tập trung CRM–DMS; FastWork đi sâu vận hành công trình. Odoo có case ERP quốc tế.</p><div class="insight"><b>Hàm ý:</b> Nên chứng minh kết quả triển khai và chi phí vận hành bằng tình huống có số liệu, thay vì thêm một bài “top phần mềm” chung chung.</div></div><div><h3>Chủ đề trong mẫu website</h3>{topics_html}<p class="sub">Đếm theo tiêu đề bài website/tin ngành; không được suy ra mức quan tâm trên mạng xã hội hoặc nhu cầu người mua.</p></div></div></section>
    <section><h2>Hoạt động theo đối thủ</h2><p class="sub">Số lượng bài cốt lõi tìm được, không dùng để so năng suất nội dung tuyệt đối vì độ phủ nguồn khác nhau.</p><div class="brandgrid">{brands_html}</div></section>
    <section><h2>Điểm tin từ nguồn chính thức</h2><p class="sub">Liên kết mở bài gốc. Các bài có thể là nội dung cũ vừa được cập nhật; kiểm tra ngày hiển thị trên trang trước khi sử dụng.</p><div class="storygrid">{top_html}</div></section>
    <section><h2>Góc nội dung còn ít được chứng minh</h2><p class="sub">Ba giả thuyết để thử, không phải tuyên bố toàn thị trường đang bỏ trống.</p>{gaps_html}</section>
    <section><h2>Độ phủ và giới hạn truy cập</h2><div class="warning"><b>Quan trọng:</b> {esc(social_note)} Chỉ mục Google News có thể trả kết quả sai thương hiệu và liên kết trung gian. Cần API/quyền kênh hoặc kiểm chứng thủ công URL gốc để báo cáo mức tương tác hay xác nhận hoạt động đăng bài.</div><div class="scroll"><table><thead><tr><th>Đối thủ</th><th>Kênh</th><th>Trạng thái</th><th>Phương thức</th><th>Mục thô</th><th>Lý do / giới hạn</th><th>Cách khắc phục</th></tr></thead><tbody>{coverage_html}</tbody></table></div></section>
    <section><h2>Dữ liệu nguồn đã kiểm duyệt</h2><p class="sub">Bảng xếp Facebook → TikTok → YouTube trước website/tin ngành. Lọc theo đối thủ, kênh hoặc tiêu đề; URL gốc nằm trong dữ liệu Excel.</p><div class="controls"><select id="brand"><option value="">Tất cả đối thủ</option>{''.join(f'<option>{esc(b)}</option>' for b in BRANDS)}<option>Ngành</option></select><select id="channel"><option value="">Tất cả kênh</option><option>Facebook</option><option>TikTok</option><option>YouTube</option><option>Website</option><option>Tin ngành</option></select><input id="q" placeholder="Tìm trong tiêu đề..."></div><div class="scroll"><table id="evidence"><thead><tr><th>Ngày</th><th>Đối thủ</th><th>Kênh</th><th>Tiêu đề và nguồn</th><th>Chủ đề</th><th>Mức chứng cứ</th></tr></thead><tbody>{evidence_html}</tbody></table></div></section><footer>Phương pháp: {esc(model["method_note"])} Báo cáo tạo từ dữ liệu công khai; liên kết chỉ mục cần đối chiếu tại nguồn gốc trước khi trích dẫn ngoài nội bộ.</footer></main><script>const b=document.querySelector('#brand'),c=document.querySelector('#channel'),q=document.querySelector('#q');function f(){{for(const r of document.querySelectorAll('#evidence tbody tr'))r.hidden=(b.value&&r.dataset.brand!==b.value)||(c.value&&r.dataset.channel!==c.value)||(q.value&&!r.innerText.toLowerCase().includes(q.value.toLowerCase()))}}[b,c,q].forEach(x=>x.addEventListener('input',f));</script></body></html>'''


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python market_profile_report.py input.json output-directory")
    paths = build(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps({"data": str(paths[0]), "html": str(paths[1])}, ensure_ascii=False))
