from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "dist" / "competitor-news-monitor.zip"
EXCLUDED_PARTS = {"work", "dist", ".git", "__pycache__"}


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT)
            if not path.is_file() or EXCLUDED_PARTS.intersection(relative.parts):
                continue
            if path.suffix in {".pyc", ".bak"}:
                continue
            archive.write(path, Path("competitor-news-monitor") / relative)
    temporary.replace(OUTPUT)
    print(OUTPUT.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
