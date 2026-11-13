"""Remove expired local previews and recovery snapshots."""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tracked = subprocess.check_output(
        ["git", "ls-files", "--", "local_previews", "snapshots"], cwd=root
    )
    if tracked.strip():
        raise RuntimeError("Local artifact directories contain tracked files. Review before cleaning.")
    now = datetime.now().timestamp()
    removed = 0
    reclaimed = 0
    for name, days in (("local_previews", 7), ("snapshots", 14)):
        folder = root / name
        if not folder.exists():
            continue
        if folder.is_symlink() or not folder.resolve().is_relative_to(root):
            raise RuntimeError(f"Unexpected artifact directory: {folder}")
        files = []
        for path in folder.rglob("*"):
            if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
                raise RuntimeError(f"Unexpected artifact path: {path}")
            if path.is_file():
                files.append(path)
        keep = set()
        if name == "snapshots":
            archives = sorted(
                (path for path in files if path.suffix == ".zip"),
                key=lambda path: path.stat().st_mtime, reverse=True,
            )
            keep = {path.with_suffix("") for path in archives[:2]}
        cutoff = now - timedelta(days=days).total_seconds()
        for path in files:
            expired = path.stat().st_mtime < cutoff
            excess = name == "snapshots" and path.with_suffix("") not in keep
            if expired or excess:
                reclaimed += path.stat().st_size
                removed += 1
                if not args.dry_run:
                    path.unlink()
        if not args.dry_run:
            for path in sorted(folder.rglob("*"), key=lambda path: len(path.parts), reverse=True):
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
    print(f"{'Would remove' if args.dry_run else 'Removed'} {removed} files, {reclaimed / 1024**2:.1f} MiB")


if __name__ == "__main__":
    main()
