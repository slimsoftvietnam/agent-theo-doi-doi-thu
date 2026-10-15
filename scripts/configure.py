from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "monitor.toml"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    print("CẤU HÌNH AI AGENT THEO DÕI ĐỐI THỦ")
    print(f"File cấu hình: {CONFIG}")
    backup = CONFIG.with_suffix(".toml.bak")
    if CONFIG.exists():
        shutil.copy2(CONFIG, backup)
        print(f"Đã tạo bản sao an toàn: {backup.name}")
    print("\nChỉnh các mục [agent], keywords, [[competitors]], [[topics]] và [[sources]].")
    try:
        subprocess.run(["notepad.exe", str(CONFIG)], check=False)
    except FileNotFoundError:
        print("Không mở được Notepad. Hãy mở file bằng trình soạn thảo văn bản.")
        return 1
    result = subprocess.run(["python", str(ROOT / "monitor.py"), "validate-config"], check=False)
    if result.returncode:
        print("Cấu hình chưa hợp lệ. Có thể khôi phục từ monitor.toml.bak.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
