"""Read-only HTTPS release check; no rooms, answers, models, or GUI access."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

checks = []
warning = "이 화면만 열어서는 AI가 클릭하지 않습니다. PC에서 로컬 봇 프로그램을 실행하세요."
for host in ("human.marulee.dev", "bot.marulee.dev"):
    request = Request(f"https://{host}/", headers={"User-Agent": "AlphaCaptchaReleaseCheck/1.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
        checks.append({"host": host, "status": response.status,
                       "local_bot_warning_present": warning in html,
                       "bot_screen_ready_label_present": "봇 화면 준비" in html})
report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
          "checks": checks,
          "passed": all(row["status"] == 200 and row["local_bot_warning_present"] for row in checks),
          "limits": "HTTP HTML only; no browser rendering, calibration, ML, clicks, or submissions"}
Path(__file__).with_name("release-http.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if report["passed"] else 1)
