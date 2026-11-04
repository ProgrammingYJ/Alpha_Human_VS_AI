"""Post-check recorded real-model predictions against HTTP viewer witnesses."""
import json
from pathlib import Path

folder = Path("runs/continuous-booth-local-v1")
record = json.loads((folder / "verification.json").read_text(encoding="utf-8"))
checks = {}
for lane, number in (("A", 1), ("A", 2), ("B", 1)):
    model = json.loads((folder / f"lane-{lane}-game-{number}.json").read_text(encoding="utf-8"))
    result_states = [row for row in record["observations"][lane + str(number)] if row["phase"] == "result"]
    checks[lane + str(number)] = result_states[-1]["indices"] == model["selected_indices"]
report = {"passed": all(checks.values()), "viewer_matches_model": checks,
          "limits": "Rechecks existing recorded actual model and HTTP observations; no new inference"}
(folder / "viewer-match.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
raise SystemExit(0 if report["passed"] else 1)
