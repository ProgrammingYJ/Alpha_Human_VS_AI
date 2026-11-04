"""Read-only production HTML smoke check; no room or answer access."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

checks = []
for host in ("human.marulee.dev", "bot.marulee.dev"):
    request = Request(f"https://{host}/?lane=A", headers={"User-Agent": "AlphaCaptchaReleaseCheck/1.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
        checks.append({"host": host, "status": response.status,
                       "remote_pad_explanation": "패드 화면을 실제로 누르는 방식은 아닙니다" in html,
                       "lane_picker_present": "이 패드의 구역을 선택하세요" in html})
report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
          "passed": all(row["status"] == 200 and row["remote_pad_explanation"] and row["lane_picker_present"] for row in checks),
          "limits": "HTTP SSR HTML only; browser hydration and actual ML verified separately"}
Path(__file__).with_name("remote-release-http.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False))
raise SystemExit(0 if report["passed"] else 1)
