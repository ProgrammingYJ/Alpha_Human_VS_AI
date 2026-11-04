"""Read-only public desktop-copy smoke check, no rooms or answer access."""
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=Path(__file__).with_name("desktop-release-http.json"))
args = parser.parse_args()
checks = []
for host in ("human.marulee.dev", "bot.marulee.dev"):
    request = Request(f"https://{host}/?lane=A", headers={"User-Agent": "AlphaCaptchaDesktopRelease/1.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
        checks.append({"host": host, "status": response.status,
                       "desktop_display_explanation": "AI 표시 화면은 PC의 선택만 보여주며 브라우저를 대신 클릭하지 않습니다" in html,
                       "lane_picker_present": "이 화면의 구역을 선택하세요" in html,
                       "pad_only_copy_absent": "패드" not in html})
report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
          "passed": all(row["status"] == 200 and row["desktop_display_explanation"] and row["lane_picker_present"] and row["pad_only_copy_absent"] for row in checks),
          "limits": "SSR HTML only; liveness and browser rendering verified separately"}
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if report["passed"] else 1)
