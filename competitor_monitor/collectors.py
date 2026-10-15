from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

from .util import canonical_url, iso_utc, parse_datetime, plain_text, stable_hash


USER_AGENT = "Competitor-News-Monitor/2.0 (+local research agent; respects robots.txt)"
MAX_BYTES = 5 * 1024 * 1024
ARTICLE_TYPES = {"article", "newsarticle", "blogposting", "report", "analysisnewsarticle"}


@dataclass
class SourceResult:
    source_id: str
    source_name: str
    source_type: str
    status: str = "HEALTHY"
    method: str = ""
    error: str = ""
    items: list[dict] = field(default_factory=list)


def _request_full(
    url: str,
    timeout: int,
    headers: dict | None = None,
    *,
    method: str = "GET",
    data: bytes | None = None,
) -> tuple[bytes, str, dict[str, str]]:
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/json, text/html;q=0.8",
    }
    request_headers.update(headers or {})
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_BYTES + 1)
        content_type = response.headers.get_content_type()
        response_headers = {key.lower(): value for key, value in response.headers.items()}
    if len(payload) > MAX_BYTES:
        raise ValueError("RESPONSE_EXCEEDS_5MB")
    return payload, content_type, response_headers


def _request(
    url: str,
    timeout: int,
    headers: dict | None = None,
    *,
    method: str = "GET",
    data: bytes | None = None,
) -> tuple[bytes, str]:
    payload, content_type, _ = _request_full(url, timeout, headers, method=method, data=data)
    return payload, content_type


def _cached_request(
    url: str,
    timeout: int,
    cache_dir: str | Path | None,
    headers: dict | None = None,
) -> tuple[bytes, str]:
    """GET with ETag/Last-Modified validators and a small on-disk body cache."""
    if not cache_dir:
        return _request(url, timeout, headers)
    folder = Path(cache_dir)
    folder.mkdir(parents=True, exist_ok=True)
    key = stable_hash(url)
    meta_path = folder / f"{key}.json"
    body_path = folder / f"{key}.bin"
    meta: dict = {}
    try:
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        meta = {}
    request_headers = dict(headers or {})
    if meta.get("etag"):
        request_headers["If-None-Match"] = str(meta["etag"])
    if meta.get("last_modified"):
        request_headers["If-Modified-Since"] = str(meta["last_modified"])
    try:
        payload, content_type, response_headers = _request_full(url, timeout, request_headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and body_path.exists():
            return body_path.read_bytes(), str(meta.get("content_type", "application/octet-stream"))
        raise
    body_tmp = body_path.with_suffix(".bin.tmp")
    meta_tmp = meta_path.with_suffix(".json.tmp")
    body_tmp.write_bytes(payload)
    meta_tmp.write_text(
        json.dumps(
            {
                "url": url,
                "etag": response_headers.get("etag", ""),
                "last_modified": response_headers.get("last-modified", ""),
                "content_type": content_type,
                "content_hash": stable_hash(payload),
                "checked_at": iso_utc(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    body_tmp.replace(body_path)
    meta_tmp.replace(meta_path)
    return payload, content_type


def _node_text(node: ET.Element, names: set[str]) -> str:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1].lower() in names and child.text:
            return plain_text(child.text)
    return ""


def _node_link(node: ET.Element) -> str:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1].lower() == "link":
            link = child.attrib.get("href") or (child.text or "")
            if link:
                return canonical_url(link)
    return ""


def _node_author(node: ET.Element) -> str:
    author = _node_text(node, {"author", "creator"})
    if author:
        return author
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1].lower() == "name" and child.text:
            return plain_text(child.text)
    return ""


def _node_image(node: ET.Element) -> str:
    for child in node.iter():
        local = child.tag.rsplit("}", 1)[-1].lower()
        url = child.attrib.get("url", "")
        mime = child.attrib.get("type", "").lower()
        medium = child.attrib.get("medium", "").lower()
        if url and (local in {"thumbnail", "content", "enclosure"}) and (
            local == "thumbnail" or mime.startswith("image/") or medium == "image"
        ):
            return canonical_url(url)
    return ""


def parse_feed(payload: bytes, source: dict, cutoff: datetime, limit: int) -> list[dict]:
    root = ET.fromstring(payload)
    output: list[dict] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].lower() not in {"item", "entry"}:
            continue
        title = _node_text(node, {"title"})
        published = parse_datetime(_node_text(node, {"pubdate", "published", "updated", "date"}))
        url = _node_link(node)
        if not title or not url or not published or published < cutoff:
            continue
        summary = _node_text(node, {"summary", "description", "content", "encoded"})[:2000]
        output.append(
            {
                "source_id": source["id"],
                "source_name": source.get("name", source["id"]),
                "source_type": source["type"],
                "title": title,
                "summary": summary,
                "published_at": iso_utc(published),
                "canonical_url": url,
                "author": _node_author(node),
                "image_url": _node_image(node),
                "engagement": {},
            }
        )
        if len(output) >= limit:
            break
    return output


class FeedDiscoveryParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.feeds: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() != "link":
            return
        values = {key.lower(): value for key, value in attrs}
        rel = values.get("rel", "").lower()
        mime = values.get("type", "").lower()
        if "alternate" in rel and mime in {"application/rss+xml", "application/atom+xml"} and values.get("href"):
            self.feeds.append(values["href"])


class ArticleHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.article_links: list[str] = []
        self.canonical = ""
        self.title_parts: list[str] = []
        self.json_ld: list[str] = []
        self._in_title = False
        self._in_json_ld = False
        self._script_parts: list[str] = []
        self._article_depth = 0

    def handle_starttag(self, tag: str, attrs):
        values = {str(key).lower(): str(value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "article":
            self._article_depth += 1
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key and values.get("content"):
                self.meta[key] = values["content"]
        elif tag == "link":
            rel = values.get("rel", "").lower()
            href = values.get("href", "")
            if "canonical" in rel and href:
                self.canonical = href
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])
            if self._article_depth:
                self.article_links.append(values["href"])
        elif tag == "title":
            self._in_title = True
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._script_parts = []

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag == "article":
            self._article_depth = max(0, self._article_depth - 1)
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            if self._script_parts:
                self.json_ld.append("".join(self._script_parts))
            self._script_parts = []

    def handle_data(self, data: str):
        if self._in_title:
            self.title_parts.append(data)
        if self._in_json_ld:
            self._script_parts.append(data)


def _iter_json_objects(value):
    if isinstance(value, list):
        for row in value:
            yield from _iter_json_objects(row)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from _iter_json_objects(value["@graph"])


def _author_name(value) -> str:
    if isinstance(value, str):
        return plain_text(value)
    if isinstance(value, dict):
        return plain_text(value.get("name"))
    if isinstance(value, list):
        return ", ".join(filter(None, (_author_name(row) for row in value)))
    return ""


def parse_article_html(
    payload: bytes,
    url: str,
    source: dict,
    cutoff: datetime,
    fallback_date: str | None = None,
) -> dict | None:
    parser = ArticleHTMLParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    candidates: list[dict] = []
    for raw in parser.json_ld:
        try:
            decoded = json.loads(raw.strip())
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in _iter_json_objects(decoded):
            raw_type = obj.get("@type", "")
            types = raw_type if isinstance(raw_type, list) else [raw_type]
            if any(str(value).casefold() in ARTICLE_TYPES for value in types):
                candidates.append(obj)
    article = candidates[0] if candidates else {}
    published_raw = (
        article.get("datePublished")
        or parser.meta.get("article:published_time")
        or parser.meta.get("date")
        or fallback_date
    )
    published = parse_datetime(str(published_raw or ""))
    if published and published < cutoff:
        return None
    title = plain_text(
        article.get("headline")
        or parser.meta.get("og:title")
        or parser.meta.get("twitter:title")
        or "".join(parser.title_parts)
    )
    canonical = canonical_url(urllib.parse.urljoin(url, parser.canonical or url))
    if not title or not canonical or not published:
        return None
    image = article.get("image") or parser.meta.get("og:image") or ""
    if isinstance(image, list):
        image = image[0] if image else ""
    if isinstance(image, dict):
        image = image.get("url", "")
    return {
        "source_id": source["id"],
        "source_name": source.get("name", source["id"]),
        "source_type": source["type"],
        "title": title,
        "summary": plain_text(
            article.get("description")
            or parser.meta.get("description")
            or parser.meta.get("og:description")
        )[:2000],
        "published_at": iso_utc(published),
        "canonical_url": canonical,
        "author": _author_name(article.get("author")) or plain_text(parser.meta.get("author")),
        "image_url": canonical_url(str(image)),
        "engagement": {},
    }


def parse_sitemap(payload: bytes) -> tuple[list[tuple[str, str]], list[str]]:
    root = ET.fromstring(payload)
    root_type = root.tag.rsplit("}", 1)[-1].lower()
    urls: list[tuple[str, str]] = []
    indexes: list[str] = []
    for node in root:
        local = node.tag.rsplit("}", 1)[-1].lower()
        loc = _node_text(node, {"loc"})
        lastmod = _node_text(node, {"lastmod"})
        if root_type == "sitemapindex" and local == "sitemap" and loc:
            indexes.append(loc)
        elif root_type == "urlset" and local == "url" and loc:
            urls.append((loc, lastmod))
    return urls, indexes


def _fetch_feed(
    source: dict,
    feed_url: str,
    cutoff: datetime,
    timeout: int,
    limit: int,
    method: str,
    context: dict | None = None,
) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], method=method)
    try:
        cache_dir = (context or {}).get("cache_dir")
        payload, _ = _cached_request(feed_url, timeout, cache_dir)
        result.items = parse_feed(payload, source, cutoff, limit)
    except urllib.error.HTTPError as exc:
        result.status, result.error = "ERROR", f"HTTP_{exc.code}"
    except urllib.error.URLError as exc:
        result.status, result.error = "ERROR", f"NETWORK_{type(exc.reason).__name__}"
    except Exception as exc:
        result.status, result.error = "ERROR", type(exc).__name__
    return result


def _collect_rss(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    url = str(source.get("url", "")).strip()
    if not url:
        return SourceResult(source["id"], source.get("name", source["id"]), source["type"], "LIMITED", "official_feed", "RSS_URL_REQUIRED")
    return _fetch_feed(source, url, cutoff, timeout, limit, "official_feed", context)


def _robot_policy(homepage: str, timeout: int, cache_dir: str | Path | None) -> tuple[urllib.robotparser.RobotFileParser, list[str], float]:
    parts = urllib.parse.urlsplit(homepage)
    robots_url = urllib.parse.urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    lines: list[str] = []
    try:
        payload, _ = _cached_request(robots_url, timeout, cache_dir, {"Accept": "text/plain"})
        lines = payload.decode("utf-8", errors="replace").splitlines()
        parser.parse(lines)
    except urllib.error.HTTPError as exc:
        if exc.code not in {401, 403, 404}:
            raise
        parser.parse([] if exc.code == 404 else ["User-agent: *", "Disallow: /"])
    sitemap_urls = []
    for line in lines:
        if line.casefold().startswith("sitemap:"):
            sitemap_urls.append(line.split(":", 1)[1].strip())
    delay = parser.crawl_delay("Competitor-News-Monitor") or parser.crawl_delay("*") or 0.0
    return parser, sitemap_urls, float(delay)


def _same_host(base: str, candidate: str) -> bool:
    return urllib.parse.urlsplit(base).hostname == urllib.parse.urlsplit(candidate).hostname


def _likely_article_url(url: str) -> bool:
    path = urllib.parse.urlsplit(url).path.casefold()
    return bool(
        re.search(r"/(20\d{2})[/_-](0?[1-9]|1[0-2])[/_-]", path)
        or any(token in path for token in ("/blog/", "/news/", "/tin-", "/bai-viet/", "/article/", "/insights/"))
    )


def _collect_website(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    explicit_feed = str(source.get("rss_url", "")).strip()
    if explicit_feed:
        feed_result = _fetch_feed(source, explicit_feed, cutoff, timeout, limit, "official_feed", context)
        if feed_result.status == "HEALTHY" and feed_result.items:
            return feed_result
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], method="web_crawl_allowed")
    homepage = str(source.get("url", "")).strip()
    if not homepage:
        result.status, result.error = "LIMITED", "WEBSITE_URL_REQUIRED"
        return result
    cache_dir = (context or {}).get("cache_dir")
    try:
        robots, robot_sitemaps, robots_delay = _robot_policy(homepage, timeout, cache_dir)
        if not robots.can_fetch(USER_AGENT, homepage):
            result.status, result.error = "LIMITED", "ROBOTS_DISALLOWED"
            return result
        payload, content_type = _cached_request(homepage, timeout, cache_dir, {"Accept": "text/html"})
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError("HTML_REQUIRED")
        feed_parser = FeedDiscoveryParser()
        decoded_home = payload.decode("utf-8", errors="replace")
        feed_parser.feed(decoded_home)
        if feed_parser.feeds:
            feed_url = urllib.parse.urljoin(homepage, feed_parser.feeds[0])
            if robots.can_fetch(USER_AGENT, feed_url):
                feed_result = _fetch_feed(source, feed_url, cutoff, timeout, limit, "discovered_official_feed", context)
                if feed_result.status == "HEALTHY" and feed_result.items:
                    return feed_result

        article_parser = ArticleHTMLParser()
        article_parser.feed(decoded_home)
        sitemap_urls = []
        configured_sitemap = str(source.get("sitemap_url", "")).strip()
        if configured_sitemap:
            sitemap_urls.append(configured_sitemap)
        sitemap_urls.extend(robot_sitemaps)
        if not sitemap_urls:
            sitemap_urls.append(urllib.parse.urljoin(homepage, "/sitemap.xml"))
        candidate_rows: list[tuple[str, str]] = []
        # Listing cards are usually ordered newest first and may use flat slugs
        # (e.g. 1Office); place them before broad sitemaps so the crawl budget
        # reaches recent posts instead of old navigation/product URLs.
        for href in article_parser.article_links:
            candidate = canonical_url(urllib.parse.urljoin(homepage, href))
            if candidate and _same_host(homepage, candidate):
                candidate_rows.append((candidate, ""))
        for sitemap_url in dict.fromkeys(sitemap_urls):
            if not robots.can_fetch(USER_AGENT, sitemap_url):
                continue
            try:
                sitemap_payload, _ = _cached_request(sitemap_url, timeout, cache_dir, {"Accept": "application/xml,text/xml"})
                urls, indexes = parse_sitemap(sitemap_payload)
                candidate_rows.extend(urls)
                for child_url in indexes[: int(source.get("max_sitemap_files", 5))]:
                    if not robots.can_fetch(USER_AGENT, child_url):
                        continue
                    child_payload, _ = _cached_request(child_url, timeout, cache_dir, {"Accept": "application/xml,text/xml"})
                    child_urls, _ = parse_sitemap(child_payload)
                    candidate_rows.extend(child_urls)
            except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError, ValueError):
                continue
        if not candidate_rows:
            for href in article_parser.links:
                candidate = canonical_url(urllib.parse.urljoin(homepage, href))
                if candidate and _same_host(homepage, candidate) and _likely_article_url(candidate):
                    candidate_rows.append((candidate, ""))
        recent_candidates = []
        for candidate, lastmod in candidate_rows:
            candidate = canonical_url(candidate)
            if not candidate or not _same_host(homepage, candidate) or not robots.can_fetch(USER_AGENT, candidate):
                continue
            parsed_lastmod = parse_datetime(lastmod)
            if parsed_lastmod and parsed_lastmod < cutoff:
                continue
            recent_candidates.append((candidate, lastmod))
        seen: set[str] = set()
        article_failures: list[str] = []
        delay = max(float(source.get("request_delay_seconds", 0.25)), robots_delay)
        max_pages = min(int(source.get("max_crawl_pages", limit)), limit)
        for candidate, lastmod in recent_candidates:
            if candidate in seen or len(seen) >= max_pages:
                continue
            seen.add(candidate)
            if delay:
                time.sleep(min(delay, 5.0))
            try:
                page, page_type = _cached_request(candidate, timeout, cache_dir, {"Accept": "text/html"})
                if page_type not in {"text/html", "application/xhtml+xml"}:
                    continue
                item = parse_article_html(page, candidate, source, cutoff, lastmod)
                if item:
                    result.items.append(item)
                    if len(result.items) >= limit:
                        break
            except urllib.error.HTTPError as exc:
                article_failures.append(f"HTTP_{exc.code}")
                continue
            except urllib.error.URLError as exc:
                article_failures.append(f"NETWORK_{type(exc.reason).__name__}")
                continue
            except ValueError as exc:
                article_failures.append(type(exc).__name__)
                continue
        if not result.items and article_failures:
            result.status = "LIMITED"
            result.error = "ARTICLE_FETCH_FAILED:" + ",".join(sorted(set(article_failures)))
        if not candidate_rows:
            result.error = "NO_DISCOVERABLE_FEED_OR_SITEMAP_ARTICLES"
        return result
    except urllib.error.HTTPError as exc:
        result.status, result.error = "ERROR", f"HTTP_{exc.code}"
    except urllib.error.URLError as exc:
        result.status, result.error = "ERROR", f"NETWORK_{type(exc.reason).__name__}"
    except Exception as exc:
        result.status = "MANUAL_REVIEW" if isinstance(exc, ValueError) else "ERROR"
        result.error = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    return result


def _collect_google_news(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    query = str(source.get("query", "")).strip()
    if not query:
        return SourceResult(source["id"], source.get("name", source["id"]), source["type"], "LIMITED", "google_news_index_rss", "QUERY_REQUIRED")
    params = urllib.parse.urlencode(
        {"q": query, "hl": source.get("language", "vi"), "gl": source.get("country", "VN"), "ceid": source.get("ceid", "VN:vi")}
    )
    feed_url = f"https://news.google.com/rss/search?{params}"
    result = _fetch_feed(source, feed_url, cutoff, timeout, limit, "google_news_index_rss", context)
    if result.status == "HEALTHY":
        result.status = "SEARCH_INDEX_ONLY"
        for item in result.items:
            item["evidence_level"] = "SEARCH_INDEX_ONLY"
    return result


def _search_query(source: dict) -> str:
    explicit = str(source.get("search_query", "")).strip()
    if explicit:
        return explicit
    site = str(source.get("search_site", "")).strip()
    name = str(source.get("name", source.get("id", ""))).strip()
    return f"site:{site} {name}".strip() if site else name


def _search_brave(source: dict, query: str, cutoff: datetime, timeout: int, limit: int, api_key: str) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], "SEARCH_INDEX_ONLY", "search_index_brave")
    params = urllib.parse.urlencode({"q": query, "count": min(limit, 20), "search_lang": source.get("search_language", "vi")})
    payload, _ = _request(
        f"https://api.search.brave.com/res/v1/web/search?{params}", timeout,
        {"Accept": "application/json", "X-Subscription-Token": api_key},
    )
    for row in (json.loads(payload).get("web") or {}).get("results", [])[:limit]:
        url = canonical_url(row.get("url"))
        title = plain_text(row.get("title"))
        published = parse_datetime(row.get("page_age") or row.get("age"))
        if not url or not title or (published and published < cutoff):
            continue
        result.items.append(
            {
                "source_id": source["id"], "source_name": result.source_name, "source_type": source["type"],
                "title": title, "summary": plain_text(row.get("description"))[:2000],
                "published_at": iso_utc(published) if published else None, "canonical_url": url,
                "author": "", "image_url": "", "engagement": {}, "evidence_level": "SEARCH_INDEX_ONLY",
            }
        )
    return result


def _search_google_cse(source: dict, query: str, cutoff: datetime, timeout: int, limit: int, api_key: str, cx: str) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], "SEARCH_INDEX_ONLY", "search_index_google_cse")
    params = urllib.parse.urlencode({"q": query, "key": api_key, "cx": cx, "num": min(limit, 10), "dateRestrict": source.get("date_restrict", "m1")})
    payload, _ = _request(f"https://www.googleapis.com/customsearch/v1?{params}", timeout, {"Accept": "application/json"})
    for row in json.loads(payload).get("items", [])[:limit]:
        url = canonical_url(row.get("link"))
        title = plain_text(row.get("title"))
        metatags = (((row.get("pagemap") or {}).get("metatags") or [{}])[0])
        published = parse_datetime(metatags.get("article:published_time") or metatags.get("date"))
        if not url or not title or (published and published < cutoff):
            continue
        result.items.append(
            {
                "source_id": source["id"], "source_name": result.source_name, "source_type": source["type"],
                "title": title, "summary": plain_text(row.get("snippet"))[:2000],
                "published_at": iso_utc(published) if published else None, "canonical_url": url,
                "author": "", "image_url": "", "engagement": {}, "evidence_level": "SEARCH_INDEX_ONLY",
            }
        )
    return result


def _search_google_news_index(source: dict, query: str, cutoff: datetime, timeout: int, limit: int, context: dict | None) -> SourceResult:
    proxy_source = {**source, "query": query}
    feed = _collect_google_news(proxy_source, cutoff, timeout, limit, context)
    feed.status = "SEARCH_INDEX_ONLY" if feed.status == "HEALTHY" else feed.status
    feed.method = "search_index_google_news_rss"
    for item in feed.items:
        item["evidence_level"] = "SEARCH_INDEX_ONLY"
    return feed


def _collect_web_search(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    discovery = (context or {}).get("discovery") or {}
    query = _search_query(source)
    if not query:
        return SourceResult(source["id"], source.get("name", source["id"]), source["type"], "LIMITED", "search_index", "SEARCH_QUERY_REQUIRED")
    provider = str(source.get("search_provider") or discovery.get("provider") or "auto").casefold()
    brave_env = str(discovery.get("brave_api_key_env", "BRAVE_SEARCH_API_KEY"))
    google_key_env = str(discovery.get("google_api_key_env", "GOOGLE_SEARCH_API_KEY"))
    google_cx_env = str(discovery.get("google_cx_env", "GOOGLE_SEARCH_CX"))
    attempts: list[str] = []
    providers = [provider] if provider != "auto" else ["brave", "google_cse", "google_news"]
    for candidate in providers:
        try:
            if candidate == "brave":
                key = os.environ.get(brave_env, "")
                if not key:
                    attempts.append("BRAVE_KEY_MISSING")
                    continue
                return _search_brave(source, query, cutoff, timeout, limit, key)
            if candidate == "google_cse":
                key, cx = os.environ.get(google_key_env, ""), os.environ.get(google_cx_env, "")
                if not key or not cx:
                    attempts.append("GOOGLE_CSE_CREDENTIALS_MISSING")
                    continue
                return _search_google_cse(source, query, cutoff, timeout, limit, key, cx)
            if candidate == "google_news":
                result = _search_google_news_index(source, query, cutoff, timeout, limit, context)
                if attempts and result.status == "SEARCH_INDEX_ONLY":
                    result.error = "PRIMARY_UNAVAILABLE:" + ",".join(attempts)
                return result
        except urllib.error.HTTPError as exc:
            attempts.append(f"{candidate.upper()}_HTTP_{exc.code}")
        except urllib.error.URLError as exc:
            attempts.append(f"{candidate.upper()}_NETWORK_{type(exc.reason).__name__}")
        except Exception as exc:
            attempts.append(f"{candidate.upper()}_{type(exc).__name__}")
    return SourceResult(
        source["id"], source.get("name", source["id"]), source["type"], "LIMITED", "search_index",
        ",".join(attempts) or "NO_SEARCH_PROVIDER_AVAILABLE",
    )


def _youtube_feed_url(source: dict) -> str:
    if source.get("rss_url"):
        return str(source["rss_url"])
    channel_id = str(source.get("channel_id", "")).strip()
    if not channel_id:
        match = re.search(r"/channel/([^/?]+)", str(source.get("url", "")))
        channel_id = match.group(1) if match else ""
    return f"https://www.youtube.com/feeds/videos.xml?{urllib.parse.urlencode({'channel_id': channel_id})}" if channel_id else ""


def _enrich_youtube(items: list[dict], api_key: str, timeout: int) -> None:
    ids = []
    for item in items:
        video_id = urllib.parse.parse_qs(urllib.parse.urlsplit(item["canonical_url"]).query).get("v", [""])[0]
        if video_id:
            ids.append(video_id)
    if not ids:
        return
    url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode({"part": "statistics", "id": ",".join(ids), "key": api_key})
    payload, _ = _request(url, timeout, {"Accept": "application/json"})
    stats = {row["id"]: row.get("statistics", {}) for row in json.loads(payload).get("items", [])}
    for item in items:
        video_id = urllib.parse.parse_qs(urllib.parse.urlsplit(item["canonical_url"]).query).get("v", [""])[0]
        values = stats.get(video_id, {})
        if values:
            item["engagement"] = {key: int(values[key]) for key in ("viewCount", "likeCount", "commentCount") if key in values}
            item["engagement_source"] = "youtube_data_api_v3"


def _collect_youtube_api(source: dict, cutoff: datetime, timeout: int, limit: int, api_key: str) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], method="youtube_data_api_v3")
    channel_id = str(source.get("channel_id", "")).strip()
    if not channel_id:
        result.status, result.error = "LIMITED", "YOUTUBE_CHANNEL_ID_REQUIRED"
        return result
    channel_url = "https://www.googleapis.com/youtube/v3/channels?" + urllib.parse.urlencode({"part": "contentDetails", "id": channel_id, "key": api_key})
    channel_payload, _ = _request(channel_url, timeout, {"Accept": "application/json"})
    channels = json.loads(channel_payload).get("items", [])
    if not channels:
        result.status, result.error = "ERROR", "YOUTUBE_CHANNEL_NOT_FOUND"
        return result
    uploads = (((channels[0].get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads"))
    if not uploads:
        result.status, result.error = "ERROR", "YOUTUBE_UPLOADS_PLAYLIST_MISSING"
        return result
    playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode(
        {"part": "snippet,contentDetails", "playlistId": uploads, "maxResults": min(limit, 50), "key": api_key}
    )
    playlist_payload, _ = _request(playlist_url, timeout, {"Accept": "application/json"})
    for row in json.loads(playlist_payload).get("items", []):
        snippet = row.get("snippet") or {}
        details = row.get("contentDetails") or {}
        published = parse_datetime(details.get("videoPublishedAt") or snippet.get("publishedAt"))
        video_id = details.get("videoId") or ((snippet.get("resourceId") or {}).get("videoId"))
        if not video_id or not published or published < cutoff:
            continue
        thumbnails = snippet.get("thumbnails") or {}
        image = ((thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}).get("url", ""))
        result.items.append(
            {
                "source_id": source["id"], "source_name": result.source_name, "source_type": source["type"],
                "title": plain_text(snippet.get("title")), "summary": plain_text(snippet.get("description"))[:2000],
                "published_at": iso_utc(published), "canonical_url": f"https://www.youtube.com/watch?v={video_id}",
                "author": plain_text(snippet.get("videoOwnerChannelTitle") or snippet.get("channelTitle")),
                "image_url": canonical_url(image), "engagement": {},
            }
        )
    _enrich_youtube(result.items, api_key, timeout)
    return result


def _fallback_search(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None, primary_error: str) -> SourceResult:
    if not bool(source.get("fallback_search", True)):
        return SourceResult(source["id"], source.get("name", source["id"]), source["type"], "LIMITED", "", primary_error)
    result = _collect_web_search(source, cutoff, timeout, limit, context)
    if result.status == "SEARCH_INDEX_ONLY":
        result.error = f"PRIMARY_UNAVAILABLE:{primary_error}" + (f";{result.error}" if result.error else "")
    return result


def _collect_youtube(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    api_env = str(source.get("api_key_env", "YOUTUBE_API_KEY"))
    api_key = os.environ.get(api_env, "")
    errors: list[str] = []
    if api_key:
        try:
            api_result = _collect_youtube_api(source, cutoff, timeout, limit, api_key)
            if api_result.status == "HEALTHY":
                return api_result
            errors.append(api_result.error or api_result.status)
        except urllib.error.HTTPError as exc:
            errors.append(f"DATA_API_HTTP_{exc.code}")
        except Exception as exc:
            errors.append(f"DATA_API_{type(exc).__name__}")
    else:
        errors.append(f"{api_env}_MISSING")
    feed_url = _youtube_feed_url(source)
    if feed_url:
        feed_result = _fetch_feed(source, feed_url, cutoff, timeout, limit, "youtube_official_feed", context)
        if feed_result.status == "HEALTHY":
            if api_key and feed_result.items:
                try:
                    _enrich_youtube(feed_result.items, api_key, timeout)
                    feed_result.method = "youtube_official_feed+data_api_v3"
                except Exception as exc:
                    feed_result.error = f"METRICS_UNAVAILABLE:{type(exc).__name__}"
            return feed_result
        errors.append(feed_result.error or feed_result.status)
    else:
        errors.append("YOUTUBE_CHANNEL_ID_REQUIRED")
    return _fallback_search(source, cutoff, timeout, limit, context, ",".join(errors))


def _collect_facebook_api(source: dict, cutoff: datetime, timeout: int, limit: int, token: str) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], method="facebook_graph_api")
    page_id = str(source.get("page_id", "")).strip()
    if not page_id:
        result.status, result.error = "LIMITED", "FACEBOOK_PAGE_ID_REQUIRED"
        return result
    fields = "id,message,created_time,permalink_url,full_picture,shares,comments.limit(0).summary(true),likes.limit(0).summary(true)"
    params = urllib.parse.urlencode({"fields": fields, "since": int(cutoff.timestamp()), "limit": min(limit, 100), "access_token": token})
    version = str(source.get("api_version", "v23.0"))
    url = f"https://graph.facebook.com/{version}/{urllib.parse.quote(page_id)}/posts?{params}"
    payload, _ = _request(url, timeout, {"Accept": "application/json"})
    data = json.loads(payload)
    if data.get("error"):
        raise ValueError("FACEBOOK_API_ERROR")
    for row in data.get("data", [])[:limit]:
        published = parse_datetime(row.get("created_time"))
        link = canonical_url(row.get("permalink_url"))
        message = plain_text(row.get("message"))
        if not published or not link or not message or published < cutoff:
            continue
        result.items.append(
            {
                "source_id": source["id"], "source_name": result.source_name, "source_type": source["type"],
                "title": message[:140], "summary": message[:2000], "published_at": iso_utc(published),
                "canonical_url": link, "author": result.source_name, "image_url": canonical_url(row.get("full_picture")),
                "engagement": {
                    "shares": int((row.get("shares") or {}).get("count", 0)),
                    "comments": int((((row.get("comments") or {}).get("summary") or {}).get("total_count", 0))),
                    "likes": int((((row.get("likes") or {}).get("summary") or {}).get("total_count", 0))),
                },
                "engagement_source": "facebook_graph_api",
            }
        )
    return result


def _collect_facebook(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    page_id = str(source.get("page_id", "")).strip()
    token_env = str(source.get("token_env", "FACEBOOK_PAGE_ACCESS_TOKEN"))
    token = os.environ.get(token_env, "")
    if page_id and token:
        try:
            return _collect_facebook_api(source, cutoff, timeout, limit, token)
        except urllib.error.HTTPError as exc:
            primary_error = f"FACEBOOK_GRAPH_HTTP_{exc.code}"
        except Exception as exc:
            primary_error = f"FACEBOOK_GRAPH_{type(exc).__name__}"
    else:
        primary_error = "FACEBOOK_PAGE_ID_OR_TOKEN_REQUIRED"
    return _fallback_search(source, cutoff, timeout, limit, context, primary_error)


def _timestamp(value) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _tiktok_item(source: dict, result: SourceResult, row: dict, cutoff: datetime) -> dict | None:
    published = _timestamp(row.get("create_time"))
    if not published or published < cutoff:
        return None
    video_id = str(row.get("id", ""))
    username = str(row.get("username") or source.get("username") or "").lstrip("@")
    link = canonical_url(row.get("share_url"))
    if not link and username and video_id:
        link = f"https://www.tiktok.com/@{username}/video/{video_id}"
    title = plain_text(row.get("title") or row.get("video_description"))
    if not link or not title:
        return None
    engagement = {}
    for key in ("view_count", "like_count", "comment_count", "share_count", "favorites_count"):
        if row.get(key) is not None:
            engagement[key] = int(row[key])
    return {
        "source_id": source["id"], "source_name": result.source_name, "source_type": source["type"],
        "title": title[:300], "summary": plain_text(row.get("video_description") or title)[:2000],
        "published_at": iso_utc(published), "canonical_url": link, "author": username,
        "image_url": canonical_url(row.get("cover_image_url")), "engagement": engagement,
        "engagement_source": result.method,
    }


def _collect_tiktok_display(source: dict, cutoff: datetime, timeout: int, limit: int, token: str) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], method="tiktok_display_api")
    fields = "id,create_time,cover_image_url,share_url,video_description,duration,height,width,title,embed_link,like_count,comment_count,share_count,view_count"
    url = "https://open.tiktokapis.com/v2/video/list/?" + urllib.parse.urlencode({"fields": fields})
    body = json.dumps({"max_count": min(limit, 20)}).encode("utf-8")
    payload, _ = _request(
        url, timeout, {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST", data=body,
    )
    decoded = json.loads(payload)
    if (decoded.get("error") or {}).get("code") not in {None, "", "ok"}:
        raise ValueError("TIKTOK_DISPLAY_API_ERROR")
    for row in (decoded.get("data") or {}).get("videos", [])[:limit]:
        item = _tiktok_item(source, result, row, cutoff)
        if item:
            result.items.append(item)
    return result


def _collect_tiktok_research(source: dict, cutoff: datetime, timeout: int, limit: int, token: str) -> SourceResult:
    result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], method="tiktok_research_api")
    username = str(source.get("username", "")).lstrip("@").strip()
    keyword = str(source.get("research_keyword", "")).strip()
    conditions = []
    if username:
        conditions.append({"operation": "EQ", "field_name": "username", "field_values": [username]})
    if keyword:
        conditions.append({"operation": "EQ", "field_name": "keyword", "field_values": [keyword]})
    if not conditions:
        result.status, result.error = "LIMITED", "TIKTOK_RESEARCH_USERNAME_OR_KEYWORD_REQUIRED"
        return result
    now = datetime.now(timezone.utc)
    start = max(cutoff, now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29))
    fields = "id,video_description,create_time,share_count,view_count,like_count,comment_count,username,favorites_count"
    url = "https://open.tiktokapis.com/v2/research/video/query/?" + urllib.parse.urlencode({"fields": fields})
    body = json.dumps(
        {"query": {"and": conditions}, "max_count": min(limit, 100), "start_date": start.strftime("%Y%m%d"), "end_date": now.strftime("%Y%m%d"), "is_random": False}
    ).encode("utf-8")
    payload, _ = _request(
        url, timeout, {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
        method="POST", data=body,
    )
    decoded = json.loads(payload)
    if (decoded.get("error") or {}).get("code") not in {None, "", "ok"}:
        raise ValueError("TIKTOK_RESEARCH_API_ERROR")
    for row in (decoded.get("data") or {}).get("videos", [])[:limit]:
        item = _tiktok_item(source, result, row, cutoff)
        if item:
            result.items.append(item)
    return result


def _collect_tiktok(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    mode = str(source.get("api_mode", "auto")).casefold()
    display_env = str(source.get("display_token_env", "TIKTOK_ACCESS_TOKEN"))
    research_env = str(source.get("research_token_env", "TIKTOK_RESEARCH_ACCESS_TOKEN"))
    display_token = os.environ.get(display_env, "")
    research_token = os.environ.get(research_env, "")
    errors: list[str] = []
    if mode in {"auto", "research"} and research_token:
        try:
            research = _collect_tiktok_research(source, cutoff, timeout, limit, research_token)
            if research.status == "HEALTHY":
                return research
            errors.append(research.error or research.status)
        except urllib.error.HTTPError as exc:
            errors.append(f"RESEARCH_API_HTTP_{exc.code}")
        except Exception as exc:
            errors.append(f"RESEARCH_API_{type(exc).__name__}")
    elif mode == "research":
        errors.append(f"{research_env}_MISSING")
    if mode in {"auto", "display"} and display_token:
        try:
            return _collect_tiktok_display(source, cutoff, timeout, limit, display_token)
        except urllib.error.HTTPError as exc:
            errors.append(f"DISPLAY_API_HTTP_{exc.code}")
        except Exception as exc:
            errors.append(f"DISPLAY_API_{type(exc).__name__}")
    elif mode == "display":
        errors.append(f"{display_env}_MISSING")
    feed_url = str(source.get("feed_url") or source.get("rss_url") or "").strip()
    if feed_url:
        feed_result = _fetch_feed(source, feed_url, cutoff, timeout, limit, "configured_authorized_feed", context)
        if feed_result.status == "HEALTHY":
            return feed_result
        errors.append(feed_result.error or feed_result.status)
    if not errors:
        errors.append("TIKTOK_AUTHORIZED_API_OR_FEED_REQUIRED")
    return _fallback_search(source, cutoff, timeout, limit, context, ",".join(errors))


COLLECTORS = {
    "rss": _collect_rss,
    "website": _collect_website,
    "google_news": _collect_google_news,
    "web_search": _collect_web_search,
    "youtube": _collect_youtube,
    "facebook": _collect_facebook,
    "tiktok": _collect_tiktok,
}


def _evidence_tier(method: str, status: str) -> str:
    if status == "SEARCH_INDEX_ONLY" or method.startswith("search_index") or method == "google_news_index_rss":
        return "SEARCH_INDEX_ONLY"
    if "api" in method:
        return "DIRECT_API"
    if "feed" in method:
        return "OFFICIAL_FEED"
    if method == "web_crawl_allowed":
        return "WEB_CRAWL_ALLOWED"
    return "UNKNOWN"


def collect_source(source: dict, cutoff: datetime, timeout: int, limit: int, context: dict | None = None) -> SourceResult:
    try:
        result = COLLECTORS[source["type"]](source, cutoff, timeout, limit, context)
    except Exception as exc:
        result = SourceResult(source["id"], source.get("name", source["id"]), source["type"], "ERROR", "", type(exc).__name__)
    tier = _evidence_tier(result.method, result.status)
    for item in result.items:
        item["item_id"] = "item-" + stable_hash(item["canonical_url"], length=20)
        item["evidence_level"] = item.get("evidence_level", tier)
        item["evidence"] = {
            "source": item["source_name"],
            "url": item["canonical_url"],
            "published_at": item.get("published_at"),
            "collection_method": result.method,
            "collection_tier": item["evidence_level"],
            "source_status": result.status,
            "collected_at": iso_utc(),
            "engagement_source": item.get("engagement_source", "unavailable"),
        }
    return result
