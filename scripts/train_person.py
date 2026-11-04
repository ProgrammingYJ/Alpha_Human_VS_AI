"""Fit a fixed-budget person detector; evaluate val by default, test explicitly."""

import argparse
import json
from pathlib import Path

from alpha_captcha.person_model import PersonTrainingProfile, train_person


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/coco-person-reviewed-split.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("runs/person-baseline-v1"))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--evaluate-test", action="store_true", help="explicit fixed-model audit only; omit while selecting budgets")
    args = parser.parse_args()
    root = args.root.resolve()
    report = train_person(root / args.manifest, root, root / args.output, PersonTrainingProfile(),
                          device=args.device, evaluate_test=args.evaluate_test)
    print(json.dumps({"checkpoint": str(args.output / "person.pt"),
                      "fit_seconds": report["metadata"]["fit_seconds"],
                      "evaluation": {split: {k: v for k, v in metrics.items() if k != "predictions"}
                                     for split, metrics in report["evaluation"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
