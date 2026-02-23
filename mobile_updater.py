#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

PRESERVE_FILES = {"midgame_save.json", "ui_settings.json"}
SKIP_TOP_LEVEL = {".git", "__pycache__", ".pytest_cache"}


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True)


def update_with_git(project_dir: Path, branch: str | None) -> tuple[bool, str]:
    if not command_exists("git"):
        return False, "git is not available on this device"
    if not (project_dir / ".git").exists():
        return False, f"{project_dir} is not a git clone"

    if branch:
        checkout = run(["git", "checkout", branch], cwd=project_dir)
        if checkout.returncode != 0:
            return False, checkout.stderr.strip() or checkout.stdout.strip() or "git checkout failed"

    pull = run(["git", "pull", "--ff-only"], cwd=project_dir)
    if pull.returncode != 0:
        return False, pull.stderr.strip() or pull.stdout.strip() or "git pull failed"
    return True, pull.stdout.strip() or "Already up to date"


def normalize_repo_url(repo_url: str) -> str:
    parsed = urlparse(repo_url)
    if "github.com" not in parsed.netloc:
        raise ValueError("zip mode currently supports GitHub URLs only")
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return f"https://github.com{path}"


def download_and_extract_zip(repo_url: str, branch: str, temp_dir: Path) -> Path:
    base = normalize_repo_url(repo_url)
    zip_url = f"{base}/archive/refs/heads/{branch}.zip"
    zip_path = temp_dir / "repo.zip"

    with urlopen(zip_url, timeout=30) as response:  # nosec B310
        zip_path.write_bytes(response.read())

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(temp_dir)

    extracted_roots = [p for p in temp_dir.iterdir() if p.is_dir() and p.name != "__pycache__"]
    if not extracted_roots:
        raise RuntimeError("Zip extract succeeded but no repository folder was found")
    return extracted_roots[0]


def sync_tree(src_root: Path, dest_root: Path) -> None:
    for item in src_root.iterdir():
        if item.name in SKIP_TOP_LEVEL:
            continue
        if item.name in PRESERVE_FILES:
            continue

        dest = dest_root / item.name
        if item.is_dir():
            if dest.exists() and not dest.is_dir():
                dest.unlink()
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)


def update_with_zip(project_dir: Path, repo_url: str, branch: str) -> tuple[bool, str]:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            extracted = download_and_extract_zip(repo_url, branch, Path(tmp))
            sync_tree(extracted, project_dir)
        return True, f"Updated from zip ({branch})"
    except Exception as exc:
        return False, f"zip update failed: {exc}"


def required_runtime_modules(headless: bool) -> list[str]:
    modules = []
    if not headless:
        modules.append("pygame")
    return modules


def check_requirements(headless: bool) -> tuple[bool, list[str]]:
    missing = []
    for module in required_runtime_modules(headless=headless):
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(module)
    return len(missing) == 0, missing


def launch_game(project_dir: Path, headless: bool, passthrough: list[str]) -> int:
    cmd = [sys.executable, "main.py"]
    if headless:
        cmd.append("--headless")
    cmd.extend(passthrough)
    process = subprocess.run(cmd, cwd=project_dir)
    return process.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update Pizzatorio then launch main.py safely (ideal for Pydroid workflows)."
    )
    parser.add_argument("--project-dir", default=".", help="Path containing main.py")
    parser.add_argument("--mode", choices=["auto", "git", "zip"], default="auto")
    parser.add_argument("--repo-url", help="GitHub repo URL (required for zip mode)")
    parser.add_argument("--branch", default="main", help="Branch to pull/download from")
    parser.add_argument("--skip-update", action="store_true", help="Skip update and only launch")
    parser.add_argument("--check-only", action="store_true", help="Check update + dependencies and exit")
    parser.add_argument("--headless", action="store_true", help="Launch with --headless")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Extra args passed to main.py")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()

    if not (project_dir / "main.py").exists():
        print(f"Error: main.py not found in {project_dir}")
        return 2

    if not args.skip_update:
        success = False
        message = ""

        if args.mode in {"auto", "git"}:
            success, message = update_with_git(project_dir, args.branch)
            if args.mode == "git":
                print(("[OK] " if success else "[WARN] ") + message)

        if args.mode in {"auto", "zip"} and not success:
            if not args.repo_url:
                if args.mode == "zip":
                    print("[WARN] --repo-url is required for zip mode")
                else:
                    print(f"[WARN] Git update unavailable ({message}). Provide --repo-url for zip fallback.")
            else:
                success, message = update_with_zip(project_dir, args.repo_url, args.branch)
                print(("[OK] " if success else "[WARN] ") + message)

    deps_ok, missing = check_requirements(headless=args.headless)
    if not deps_ok:
        print(f"[WARN] Missing runtime modules: {', '.join(missing)}")
        print("Install them in Pydroid pip, then run this launcher again.")
        return 3

    if args.check_only:
        print("[OK] Update/dependency check complete")
        return 0

    passthrough = [a for a in args.args if a != "--"]
    return launch_game(project_dir, headless=args.headless, passthrough=passthrough)


if __name__ == "__main__":
    raise SystemExit(main())
