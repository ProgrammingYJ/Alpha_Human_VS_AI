"""Train a fixed-budget Kaggle-only MobileNetV3 Small presence baseline."""

import argparse
import json
from pathlib import Path

from alpha_captcha.presence_model import PresenceTrainingProfile, train_presence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/presence-ml-v1.jsonl"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory; never overwritten")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-train-images", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--threshold", type=float, default=0.5, help="fixed before training; no validation tuning")
    parser.add_argument("--evaluate-test", action="store_true", help="explicit fixed-model audit only; omit while selecting budgets")
    args = parser.parse_args()
    try:
        profile = PresenceTrainingProfile(
            epochs=args.epochs, batch_size=args.batch_size, max_train_images=args.max_train_images,
            seed=args.seed, learning_rate=args.learning_rate, threshold=args.threshold,
        )
        report = train_presence(args.manifest, args.root, args.output_dir, profile=profile,
                                device=args.device, evaluate_test=args.evaluate_test)
        print(json.dumps({"checkpoint": report["checkpoint"], "device": report["device"],
                          "history": report["history"], "evaluations": report["evaluations"],
                          "features_and_bn_unchanged": report["features_and_bn_unchanged"]}, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
