from __future__ import annotations

import tempfile
import unittest
import zipfile
import struct
import zlib
import base64
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

from competitor_monitor.analysis import enrich_item
from competitor_monitor.collectors import ArticleHTMLParser, SourceResult, _evidence_tier, _tiktok_item, parse_article_html, parse_feed, parse_sitemap
from competitor_monitor.db import Store
from competitor_monitor.landing import render_landing_html, screenshot_plan
from competitor_monitor.reporting import build_html
from competitor_monitor.util import canonical_url, title_dedupe_key
from competitor_monitor.xlsx_writer import write_xlsx

ROOT = Path(__file__).resolve().parent.parent
TEST_TMP = ROOT / "work" / "test-tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class MonitorTests(unittest.TestCase):
    def test_canonical_url_removes_tracking(self):
        self.assertEqual(canonical_url("HTTPS://Example.com/a/?utm_source=x&b=2#top"), "https://example.com/a?b=2")

    def test_feed_parses_current_item(self):
        payload = b'''<?xml version="1.0"?><rss><channel><item><title>AI Agent launch</title><link>https://example.com/a?utm_source=x</link><pubDate>Mon, 12 Oct 2026 02:00:00 GMT</pubDate><description>New enterprise AI agent</description></item></channel></rss>'''
        source = {"id": "rss", "name": "RSS", "type": "rss"}
        items = parse_feed(payload, source, datetime(2026, 10, 11, tzinfo=timezone.utc), 10)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["canonical_url"], "https://example.com/a")

    def test_sitemap_and_jsonld_article_are_parsed(self):
        sitemap = b'''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/news/ai</loc><lastmod>2026-10-15T01:00:00Z</lastmod></url></urlset>'''
        urls, indexes = parse_sitemap(sitemap)
        self.assertEqual(indexes, [])
        self.assertEqual(urls[0][0], "https://example.com/news/ai")
        page = b'''<html><head><script type="application/ld+json">{"@type":"NewsArticle","headline":"AI Agent launch","datePublished":"2026-10-15T01:00:00Z","description":"Enterprise automation","author":{"name":"Example"}}</script></head></html>'''
        item = parse_article_html(page, urls[0][0], {"id": "web", "name": "Web", "type": "website"}, datetime(2026, 10, 14, tzinfo=timezone.utc))
        self.assertIsNotNone(item)
        self.assertEqual(item["author"], "Example")

    def test_listing_cards_find_flat_article_slugs(self):
        parser = ArticleHTMLParser()
        parser.feed('<nav><a href="/pricing">Pricing</a></nav><article><a href="/he-thong-quan-ly-nhan-su">HRMS</a></article>')
        self.assertEqual(parser.article_links, ["/he-thong-quan-ly-nhan-su"])

    def test_search_index_evidence_is_explicit(self):
        self.assertEqual(_evidence_tier("search_index_google_news_rss", "SEARCH_INDEX_ONLY"), "SEARCH_INDEX_ONLY")

    def test_tiktok_api_row_keeps_real_metrics(self):
        source = {"id": "tt", "name": "TikTok", "type": "tiktok", "username": "example"}
        result = SourceResult("tt", "TikTok", "tiktok", method="tiktok_research_api")
        row = {"id": "123", "create_time": 1792036800, "video_description": "AI agent demo", "username": "example", "view_count": 50, "like_count": 7}
        item = _tiktok_item(source, result, row, datetime(2026, 10, 14, tzinfo=timezone.utc))
        self.assertIsNotNone(item)
        self.assertEqual(item["engagement"]["view_count"], 50)

    def test_classification_separates_fact_and_tags(self):
        config = {"keywords": ["AI agent"], "competitors": [{"name": "FPT AI", "aliases": ["FPT.AI"]}], "topics": [{"name": "AI Agent", "keywords": ["AI agent"]}]}
        item = {"title": "FPT.AI ra mắt AI Agent", "summary": "Công bố nền tảng mới", "published_at": "2026-10-12T00:00:00Z", "source_priority": 1}
        enrich_item(item, config)
        self.assertEqual(item["kind"], "SỰ KIỆN")
        self.assertEqual(item["competitors"], ["FPT AI"])
        self.assertIn("AI Agent", item["topics"])

    def test_source_priority_does_not_make_unrelated_item_relevant(self):
        config = {"keywords": ["AI agent"], "competitors": [], "topics": []}
        item = {"title": "Máy ảnh du lịch mới", "summary": "Ống kính nhỏ gọn", "published_at": "2026-10-12T00:00:00Z", "source_priority": 1}
        enrich_item(item, config)
        self.assertEqual(item["relevance_score"], 0)

    def test_keywords_can_live_under_agent_table(self):
        config = {"agent": {"keywords": ["generative AI"]}, "competitors": [], "topics": []}
        item = {"title": "Generative AI for business", "summary": "", "published_at": "2026-10-15T00:00:00Z", "source_priority": 1}
        enrich_item(item, config)
        self.assertGreater(item["relevance_score"], 0)

    def test_sqlite_deduplicates_title_across_urls(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            store = Store(Path(folder) / "state.db")
            store.begin_run("r1", "daily", 24)
            base = {"item_id": "a", "dedupe_key": title_dedupe_key("Same title", "2026-10-12T00:00:00Z"), "canonical_url": "https://a.example/1", "source_id": "s", "source_name": "S", "source_type": "rss", "title": "Same title", "summary": "", "published_at": "2026-10-12T00:00:00Z", "author": "", "kind": "SỰ KIỆN", "competitors": [], "topics": [], "relevance_score": 1, "engagement": {}, "evidence": {"url": "https://a.example/1"}}
            self.assertTrue(store.save_item("r1", base))
            store.begin_run("r2", "daily", 24)
            duplicate = {**base, "item_id": "b", "canonical_url": "https://b.example/2"}
            self.assertFalse(store.save_item("r2", duplicate))
            store.close()

    def test_xlsx_is_valid_zip_with_hyperlink(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            target = write_xlsx(Path(folder) / "report.xlsx", [{"name": "Data", "rows": [["Title", "URL"], ["A", "https://example.com"]], "widths": [20, 40], "hyperlink_columns": [2]}])
            with zipfile.ZipFile(target) as archive:
                self.assertIn("xl/workbook.xml", archive.namelist())
                self.assertIn("xl/worksheets/_rels/sheet1.xml.rels", archive.namelist())

    def test_landing_report_uses_sample_design_with_current_evidence(self):
        payload = {
            "meta": {"industry": "Thử nghiệm", "produced_at": "2026-10-15T08:00:00Z", "lookback_hours": 168,
                     "competitor_names": ["Đối thủ <A>"], "timezone": "Asia/Ho_Chi_Minh",
                     "company": {"name": "Công ty B", "target_customers": "SME"}},
            "items": [{"title": "Ra mắt giải pháp mới", "summary": "Thông báo mới", "canonical_url": "https://example.com/post",
                       "published_at": "2026-10-14T03:00:00Z", "source_type": "youtube", "source_name": "Kênh A",
                       "competitors": ["Đối thủ <A>"], "topics": ["AI"],
                       "evidence": {"collection_tier": "DIRECT", "collection_method": "youtube_rss"}}],
            "analysis": {"topic_activity": [{"name": "AI", "count": 1}]},
            "source_checks": [{"source_name": "Facebook", "status": "SEARCH_INDEX_ONLY"}],
        }
        page = build_html(payload)
        self.assertIn('family=K2D', page)
        self.assertIn('Báo cáo phân tích đối thủ', page)
        self.assertIn('https://example.com/post', page)
        self.assertIn('class="topic-no" href="https://example.com/post"', page)
        self.assertIn('youtube_rss', page)
        self.assertIn('Đối thủ &lt;A&gt;', page)
        self.assertNotIn('Base.vn', page)
        self.assertIn('1 chủ đề nổi bật', page)
        self.assertEqual(page.count('class="idea"'), 5)
        with self.assertRaises(ValueError):
            render_landing_html(payload, screenshot_root=TEST_TMP, require_screenshots=True)

    def test_screenshot_plan_skips_search_intermediates(self):
        payload = {"items": [{"canonical_url": "https://news.google.com/rss/articles/abc", "topics": ["AI"],
                              "source_type": "youtube", "evidence": {"collection_tier": "SEARCH_INDEX_ONLY"}}],
                   "analysis": {"topic_activity": [{"name": "AI", "count": 1}]}}
        self.assertEqual(screenshot_plan(payload)["screenshots"], [])

    def test_final_report_embeds_five_distinct_source_screenshots(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            root = Path(folder)
            (root / "screenshots").mkdir()
            def chunk(kind, value):
                return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value))
            def pixel(color):
                return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                        + chunk(b"IDAT", zlib.compress(b"\x00" + bytes([color, 0, 0]))) + chunk(b"IEND", b""))
            payload = {
                "meta": {"industry": "Thử nghiệm", "produced_at": "2026-10-15T08:00:00Z", "lookback_hours": 168},
                "items": [
                    {"title": f"Bài {i}", "summary": f"Nội dung {i}", "canonical_url": f"https://example.com/post-{i}",
                     "published_at": f"2026-10-{i+8:02d}T03:00:00Z", "source_type": "youtube", "source_name": "Kênh",
                     "topics": [f"Chủ đề {i}"], "evidence": {"collection_tier": "DIRECT", "collection_method": "youtube_rss"}}
                    for i in range(1, 6)
                ],
                "analysis": {"topic_activity": [{"name": f"Chủ đề {i}", "count": 1} for i in range(1, 6)]},
                "source_checks": [],
            }
            plan = screenshot_plan(payload)
            self.assertEqual(len(plan["screenshots"]), 5)
            self.assertEqual(len({row["source_url"] for row in plan["screenshots"]}), 5)
            for i, row in enumerate(plan["screenshots"], 1):
                (root / row["path"]).write_bytes(pixel(i * 35))
                row["captured_at"] = "2026-10-15T15:00:00+07:00"
                row["method"] = "CODEX_BROWSER"
            payload["topic_screenshots"] = plan
            page = render_landing_html(payload, screenshot_root=root, require_screenshots=True)
            self.assertEqual(page.count('class="topic-shot"'), 5)
            self.assertEqual(page.count("data:image/png;base64,"), 5)
            self.assertNotIn("bản nháp", page.lower())
            plan["screenshots"][0]["source_url"] = "https://example.com/other"
            with self.assertRaises(ValueError):
                render_landing_html(payload, screenshot_root=root, require_screenshots=True)
            plan["screenshots"][0]["source_url"] = "https://example.com/post-1"
            plan["screenshots"][0]["path"] = "../outside.png"
            with self.assertRaises(ValueError):
                render_landing_html(payload, screenshot_root=root, require_screenshots=True)
            plan["screenshots"][0]["path"] = "screenshots/topic-01.png"
            (root / "screenshots/topic-02.png").write_bytes((root / "screenshots/topic-01.png").read_bytes())
            with self.assertRaises(ValueError):
                render_landing_html(payload, screenshot_root=root, require_screenshots=True)

    def test_historical_preview_bundles_five_distinct_source_screenshots(self):
        page = (ROOT / "assets/example-report-2026-10-05_11.html").read_text(encoding="utf-8")
        screenshots = re.findall(r'<img src="data:image/jpeg;base64,([^"]+)"', page)
        self.assertEqual(len(screenshots), 5)
        decoded = [base64.b64decode(value, validate=True) for value in screenshots]
        self.assertTrue(all(data.startswith(b"\xff\xd8\xff") for data in decoded))
        self.assertEqual(len({hashlib.sha256(data).digest() for data in decoded}), 5)
        self.assertIn("https://www.facebook.com/reel/1906475503665532", page)


if __name__ == "__main__":
    unittest.main()
