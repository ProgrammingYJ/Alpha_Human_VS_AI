"""Check review markers and the Markdown index; humans must review the content."""

import argparse
import os
import re
from pathlib import Path


EXCLUDED_DIRECTORIES = {
    ".venv", "venv", ".git", "node_modules", "data", "datasets", "models",
    "runs", "logs", "build", "dist", "__pycache__", ".pytest_cache",
    # Third-party vendored licences and framework/tool state are external,
    # not authored project documentation. Keep project docs outside these.
    "vendor", ".wrangler", ".vinext", ".sites-runtime", ".next",
}


def find_markdown(root: Path) -> list[Path]:
    found = []
    for directory, folders, files in os.walk(root):
        folders[:] = [name for name in folders if name not in EXCLUDED_DIRECTORIES and not name.endswith(".egg-info")]
        found.extend(Path(directory) / name for name in files if name.lower().endswith(".md"))
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--date", help="require this review date, YYYY-MM-DD")
    args = parser.parse_args()
    root = args.root.resolve()
    markdown = find_markdown(root)
    errors = []
    if not markdown:
        errors.append("No project-owned Markdown files were found.")
    for path in markdown:
        content = path.read_text(encoding="utf-8-sig")
        marker = re.search(r"최종 검토:\s*(\d{4}-\d{2}-\d{2})", content)
        relative = path.relative_to(root).as_posix()
        if not marker:
            errors.append(f"{relative}: missing '최종 검토: YYYY-MM-DD'")
        elif args.date and marker.group(1) != args.date:
            errors.append(f"{relative}: review date {marker.group(1)} differs from {args.date}")
        if not re.search(r"이번 작업 검토:\s*\S", content):
            errors.append(f"{relative}: missing a non-empty '이번 작업 검토:' record")
    index = root / "docs" / "README.md"
    if not index.exists():
        errors.append("docs/README.md: document index is missing")
    else:
        index_text = index.read_text(encoding="utf-8-sig")
        indexed = {index.resolve()}
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", index_text):
            target = target.split("#", 1)[0]
            if target.lower().endswith(".md") and "://" not in target:
                indexed.add((index.parent / target).resolve())
        for path in markdown:
            if path.resolve() not in indexed:
                errors.append(f"docs/README.md: missing Markdown link for {path.relative_to(root).as_posix()}")
    for path in markdown:
        print(path.relative_to(root).as_posix())
    if errors:
        print("\nFAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"\nOK: {len(markdown)} Markdown files have review markers and index links.")
    print("This does not verify whether their content is correct or was actually reviewed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
