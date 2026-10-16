from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .analysis import build_analysis, enrich_item, peas_evaluation
from .collectors import SourceResult, collect_source
from .config import ConfigError, load_config, summarize_config
from .db import Store
from .landing import render_landing_html, screenshot_plan
from .reporting import write_reports
from .util import atomic_write, iso_utc


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config" / "monitor.toml"
DEFAULT_DB = ROOT / "work" / "monitor.db"
DEFAULT_RUNS = ROOT / "work" / "runs"
SAMPLE_REPORT = ROOT / "assets" / "example-report-2026-10-05_11.html"


def _run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")


def setup(args) -> int:
    config = load_config(args.config)
    Store(args.db).close()
    Path(args.runs).mkdir(parents=True, exist_ok=True)
    print(json.dumps({"status": "READY", "config": str(Path(args.config).resolve()), "database": str(Path(args.db).resolve()), **summarize_config(config)}, ensure_ascii=False, indent=2))
    return 0


def preview(args) -> int:
    print(json.dumps({"sample_html": str(SAMPLE_REPORT.resolve()), "period": "05–11/10/2026", "note": "Mẫu lịch sử có 5 ảnh chụp nguồn nhúng trong HTML; không phải báo cáo mới."}, ensure_ascii=False))
    return 0


def plan_screenshots(args) -> int:
    run_json = Path(args.run_json).resolve()
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    plan = screenshot_plan(payload)
    manifest = run_json.parent / "screenshots" / "manifest.json"
    status = "READY" if len(plan["screenshots"]) == 5 else "INCOMPLETE"
    if not manifest.exists():
        atomic_write(manifest, json.dumps(plan, ensure_ascii=False, indent=2) + "\n")
    else:
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        expected = [(row["topic"], row["source_url"]) for row in plan["screenshots"]]
        actual = [(row.get("topic"), row.get("source_url")) for row in existing.get("screenshots", [])]
        if actual != expected:
            status = "OUTDATED_MANIFEST"
    print(json.dumps({"status": status,
                      "manifest": str(manifest), "topics": len(plan["screenshots"]),
                      "note": "Agent tự chụp đúng URL nguồn cho từng chủ đề; điền path, captured_at và method, rồi chạy finalize-report. Nếu manifest cũ, đối chiếu và sửa thay vì ghi đè ảnh đã chụp. Không dùng ảnh minh họa thay ảnh chụp nguồn."}, ensure_ascii=False))
    return 0


def finalize_report(args) -> int:
    run_json = Path(args.run_json).resolve()
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    manifest = Path(args.manifest).resolve() if args.manifest else run_json.parent / "screenshots" / "manifest.json"
    payload["topic_screenshots"] = json.loads(manifest.read_text(encoding="utf-8"))
    final_html = render_landing_html(payload, screenshot_root=run_json.parent, require_screenshots=True)
    target = run_json.with_name(run_json.stem + "-final.html")
    atomic_write(target, final_html)
    print(json.dumps({"status": "FINAL", "html": str(target), "screenshots": 5}, ensure_ascii=False))
    return 0


def validate(args) -> int:
    config = load_config(args.config)
    print(json.dumps({"status": "VALID", **summarize_config(config)}, ensure_ascii=False, indent=2))
    return 0


def status(args) -> int:
    store = Store(args.db)
    try:
        print(json.dumps({"database": str(Path(args.db).resolve()), "runs": store.latest_runs(args.limit)}, ensure_ascii=False, indent=2))
    finally:
        store.close()
    return 0


def schedule_info(args) -> int:
    config = load_config(args.config)
    schedule = config.get("schedule") or {}
    print(json.dumps({
        "enabled": bool(schedule.get("enabled", False)),
        "frequency": str(schedule.get("frequency", "daily")),
        "time": str(schedule.get("time", "07:30")),
        "weekday": str(schedule.get("weekday", "MON")),
    }, ensure_ascii=False))
    return 0


def doctor(args) -> int:
    config = load_config(args.config)
    discovery = config.get("discovery") or {}
    env_names = {
        "youtube_data_api": "YOUTUBE_API_KEY",
        "facebook_graph_api": "FACEBOOK_PAGE_ACCESS_TOKEN",
        "tiktok_display_api": "TIKTOK_ACCESS_TOKEN",
        "tiktok_research_api": "TIKTOK_RESEARCH_ACCESS_TOKEN",
        "brave_search_api": str(discovery.get("brave_api_key_env", "BRAVE_SEARCH_API_KEY")),
        "google_custom_search_api": str(discovery.get("google_api_key_env", "GOOGLE_SEARCH_API_KEY")),
        "google_custom_search_cx": str(discovery.get("google_cx_env", "GOOGLE_SEARCH_CX")),
    }
    for source in config.get("sources") or []:
        if source.get("type") == "youtube":
            env_names["youtube_data_api"] = str(source.get("api_key_env", env_names["youtube_data_api"]))
        elif source.get("type") == "facebook":
            env_names["facebook_graph_api"] = str(source.get("token_env", env_names["facebook_graph_api"]))
        elif source.get("type") == "tiktok":
            env_names["tiktok_display_api"] = str(source.get("display_token_env", env_names["tiktok_display_api"]))
            env_names["tiktok_research_api"] = str(source.get("research_token_env", env_names["tiktok_research_api"]))
    checks = {name: {"env": env_name, "configured": bool(os.environ.get(env_name))} for name, env_name in env_names.items()}
    checks["google_news_rss_free_fallback"] = {"configured": True}
    checks["website_robots_sitemap_crawler"] = {"configured": any(source.get("type") == "website" and source.get("enabled", True) for source in config.get("sources") or [])}
    print(json.dumps({"status": "READY_WITH_LIMITS" if not all(row.get("configured") for row in checks.values()) else "READY", "capabilities": checks}, ensure_ascii=False, indent=2))
    return 0


def run(args) -> int:
    config = load_config(args.config)
    agent = config["agent"]
    run_id = args.run_id or _run_id()
    lookback = int(args.lookback_hours or agent.get("lookback_hours", 72))
    timeout = int(agent.get("request_timeout_seconds", 20))
    limit = int(agent.get("max_items_per_source", 30))
    workers = max(1, min(int(agent.get("workers", 6)), 10))
    minimum_relevance = int(agent.get("minimum_relevance", 1))
    type_priorities = agent.get("source_type_priority") or {}
    enabled_sources = [source for source in config.get("sources", []) if source.get("enabled", True)]
    disabled_sources = [source for source in config.get("sources", []) if not source.get("enabled", True)]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback)
    store = Store(args.db)
    summary = {"received": 0, "relevant_received": 0, "filtered_out": 0, "new_items": 0, "duplicates": 0, "source_healthy": 0, "source_search_only": 0, "source_limited": 0, "source_errors": 0}
    collector_context = {
        "discovery": config.get("discovery") or {},
        "cache_dir": str(Path(args.db).resolve().parent / "http-cache"),
    }
    try:
        store.begin_run(run_id, agent.get("report_frequency", "manual"), lookback)
        results = []
        with ThreadPoolExecutor(max_workers=min(workers, max(1, len(enabled_sources)))) as pool:
            futures = [pool.submit(collect_source, source, cutoff, timeout, limit, collector_context) for source in enabled_sources]
            for future in as_completed(futures):
                results.append(future.result())
        results.extend(
            SourceResult(source["id"], source.get("name", source["id"]), source["type"], "DISABLED", "", "NOT_TESTED_DISABLED")
            for source in disabled_sources
        )
        results.sort(key=lambda result: result.source_id)
        for result in results:
            store.add_source_check(run_id, result)
            summary["received"] += len(result.items)
            if result.status == "HEALTHY":
                summary["source_healthy"] += 1
            elif result.status == "SEARCH_INDEX_ONLY":
                summary["source_search_only"] += 1
            elif result.status in {"LIMITED", "MANUAL_REVIEW"}:
                summary["source_limited"] += 1
            elif result.status == "ERROR":
                summary["source_errors"] += 1
            source = next(row for row in config.get("sources", []) if row["id"] == result.source_id)
            for item in result.items:
                item["source_priority"] = int(type_priorities.get(source["type"], source.get("priority", 3)))
                enrich_item(item, config)
                if item["relevance_score"] < minimum_relevance:
                    summary["filtered_out"] += 1
                    continue
                summary["relevant_received"] += 1
                if store.save_item(run_id, item):
                    summary["new_items"] += 1
                else:
                    summary["duplicates"] += 1
        store.commit()
        new_items = store.items_for_run(run_id, only_new=True)
        source_checks = store.source_checks(run_id)
        analysis = build_analysis(store, new_items, config, lookback)
        peas = peas_evaluation(summary, new_items, source_checks)
        payload = {
            "meta": {
                "run_id": run_id,
                "produced_at": iso_utc(),
                "industry": agent["industry"],
                "timezone": agent.get("timezone", "Asia/Ho_Chi_Minh"),
                "competitor_names": [row["name"] for row in config.get("competitors") or []],
                "company": config.get("company") or {},
                "frequency": agent.get("report_frequency", "manual"),
                "lookback_hours": lookback,
                "duplicates": summary["duplicates"],
                "raw_items_received": summary["received"],
                "filtered_out": summary["filtered_out"],
                "reference_architecture": "slimai-content-engine: standard-library Python, SQLite, collector registry, canonical URL, explicit access status",
            },
            "summary": summary,
            "items": new_items,
            "analysis": analysis,
            "source_checks": source_checks,
            "peas": peas,
        }
        output_dir = Path(args.runs) / run_id
        paths = write_reports(output_dir, payload)
        store.finish_run(run_id, "COMPLETED", summary)
        print(json.dumps({"status": "COMPLETED", "run_id": run_id, "summary": summary, "reports": paths}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        try:
            store.finish_run(run_id, "FAILED", summary, type(exc).__name__)
        except Exception:
            pass
        raise
    finally:
        store.close()


def run_tests(args) -> int:
    import unittest

    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="AI Agent theo dõi đối thủ và tin tức ngành")
    cli.add_argument("--config", default=str(DEFAULT_CONFIG))
    cli.add_argument("--db", default=str(DEFAULT_DB))
    cli.add_argument("--runs", default=str(DEFAULT_RUNS))
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("setup").set_defaults(func=setup)
    commands.add_parser("preview").set_defaults(func=preview)
    screenshots_parser = commands.add_parser("screenshot-plan")
    screenshots_parser.add_argument("run_json")
    screenshots_parser.set_defaults(func=plan_screenshots)
    final_parser = commands.add_parser("finalize-report")
    final_parser.add_argument("run_json")
    final_parser.add_argument("--manifest")
    final_parser.set_defaults(func=finalize_report)
    commands.add_parser("validate-config").set_defaults(func=validate)
    run_parser = commands.add_parser("run")
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--lookback-hours", type=int)
    run_parser.set_defaults(func=run)
    status_parser = commands.add_parser("status")
    status_parser.add_argument("--limit", type=int, default=10)
    status_parser.set_defaults(func=status)
    commands.add_parser("schedule-info").set_defaults(func=schedule_info)
    commands.add_parser("doctor").set_defaults(func=doctor)
    commands.add_parser("test").set_defaults(func=run_tests)
    return cli


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        args = parser().parse_args(argv)
        return int(args.func(args))
    except ConfigError as exc:
        print(json.dumps({"status": "CONFIG_ERROR", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Đã dừng theo yêu cầu người dùng.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
