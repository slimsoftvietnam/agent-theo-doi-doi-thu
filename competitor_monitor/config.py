from __future__ import annotations

import tomllib
from pathlib import Path


SUPPORTED_SOURCE_TYPES = {"rss", "website", "google_news", "web_search", "youtube", "facebook", "tiktok"}
SUPPORTED_SEARCH_PROVIDERS = {"auto", "brave", "google_cse", "google_news"}


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        raise ConfigError(f"Không tìm thấy cấu hình: {target}")
    with target.open("rb") as handle:
        data = tomllib.load(handle)
    validate_config(data)
    return data


def validate_config(data: dict) -> None:
    agent = data.get("agent") or {}
    if not str(agent.get("industry", "")).strip():
        raise ConfigError("agent.industry là bắt buộc")
    lookback = int(agent.get("lookback_hours", 0))
    if lookback < 1 or lookback > 24 * 90:
        raise ConfigError("agent.lookback_hours phải trong khoảng 1..2160")
    discovery = data.get("discovery") or {}
    provider = str(discovery.get("provider", "auto")).casefold()
    if provider not in SUPPORTED_SEARCH_PROVIDERS:
        raise ConfigError(f"discovery.provider không hỗ trợ: {provider}")
    source_ids: set[str] = set()
    for index, source in enumerate(data.get("sources") or []):
        source_id = str(source.get("id", "")).strip()
        source_type = str(source.get("type", "")).strip()
        if not source_id or source_id in source_ids:
            raise ConfigError(f"sources[{index}].id thiếu hoặc bị trùng")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise ConfigError(f"Nguồn {source_id}: type không hỗ trợ: {source_type}")
        source_provider = str(source.get("search_provider", "auto")).casefold()
        if source_provider not in SUPPORTED_SEARCH_PROVIDERS:
            raise ConfigError(f"Nguồn {source_id}: search_provider không hỗ trợ: {source_provider}")
        source_ids.add(source_id)
    if not source_ids:
        raise ConfigError("Cần ít nhất một nguồn tin")
    names: set[str] = set()
    for item in data.get("competitors") or []:
        name = str(item.get("name", "")).strip()
        if not name or name.casefold() in names:
            raise ConfigError("Tên đối thủ thiếu hoặc bị trùng")
        names.add(name.casefold())


def summarize_config(data: dict) -> dict:
    return {
        "industry": data["agent"]["industry"],
        "competitors": len(data.get("competitors") or []),
        "topics": len(data.get("topics") or []),
        "sources": len(data.get("sources") or []),
        "enabled_sources": sum(bool(x.get("enabled", True)) for x in data.get("sources") or []),
        "lookback_hours": int(data["agent"].get("lookback_hours", 72)),
        "source_types": sorted({str(source.get("type", "")) for source in data.get("sources") or []}),
        "search_provider": str((data.get("discovery") or {}).get("provider", "auto")),
    }
