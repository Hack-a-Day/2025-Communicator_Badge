#!/usr/bin/env python3
"""Cleanup utility for BlockyBlockMcBlockFace installs."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find_repo_root(start: Path) -> Path:
    current = start
    for _ in range(8):
        if (current / "firmware").is_dir() and (current / "user_apps").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise RuntimeError("Could not locate repository root containing firmware/ and user_apps/ directories.")


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
USER_APPS_ROOT = REPO_ROOT / "user_apps"
FIRMWARE_APPS_ROOT = REPO_ROOT / "firmware" / "badge" / "apps"
APP_NAME = "mcblockface"
BACKUP_DIR = USER_APPS_ROOT / APP_NAME / "backups"
BADGE_APP_DIR = FIRMWARE_APPS_ROOT / APP_NAME

USER_SLOT_FILES = {
    "a": FIRMWARE_APPS_ROOT / "userA.py",
    "b": FIRMWARE_APPS_ROOT / "userB.py",
    "c": FIRMWARE_APPS_ROOT / "userC.py",
    "d": FIRMWARE_APPS_ROOT / "userD.py",
}


def detect_slots(target_slot: Optional[str] = None) -> list[str]:
    slots: list[str] = []
    to_check = [target_slot] if target_slot else USER_SLOT_FILES.keys()
    for slot in to_check:
        if slot is None:
            continue
        slot_path = USER_SLOT_FILES[slot]
        if not slot_path.exists():
            continue
        text = slot_path.read_text(encoding="utf-8", errors="ignore")
        if APP_NAME in text:
            slots.append(slot)
    return slots


def restore_slot(slot: str) -> None:
    slot_path = USER_SLOT_FILES[slot]
    backup_path = BACKUP_DIR / f"user{slot.upper()}_backup.py"
    try:
        subprocess.run(
            ["git", "checkout", "--", str(slot_path.relative_to(REPO_ROOT))],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        if backup_path.exists():
            shutil.copy2(backup_path, slot_path)
        else:
            raise


def remove_badge_app() -> None:
    if BADGE_APP_DIR.exists():
        shutil.rmtree(BADGE_APP_DIR)


def prompt_confirmation(message: str) -> bool:
    response = input(f"{message} [y/N]: ").strip().lower()
    return response in {"y", "yes"}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Remove BlockyBlockMcBlockFace from the badge tree.")
    parser.add_argument("slot", nargs="?", choices=["a", "b", "c", "d"], help="Limit cleanup to a specific slot.")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompts.")
    args = parser.parse_args(argv)

    slots = detect_slots(args.slot)
    actions: list[str] = []
    if slots:
        actions.append("Restore user app files: " + ", ".join(f"user{s.upper()}" for s in slots))
    if BADGE_APP_DIR.exists():
        actions.append(f"Delete firmware/badge/apps/{APP_NAME}")

    if not actions:
        print("No menu slots currently reference BlockyBlockMcBlockFace.")
        if BADGE_APP_DIR.exists():
            if args.force or prompt_confirmation("Delete firmware copy anyway?"):
                remove_badge_app()
                print("Removed firmware/badge/apps copy.")
        return 0

    summary = "Planned actions:\n" + "\n".join(f"  - {line}" for line in actions)
    print(summary)

    if not args.force and not prompt_confirmation("Proceed with cleanup?"):
        print("Aborted.")
        return 0

    for slot in slots:
        restore_slot(slot)
        print(f"Restored firmware/badge/apps/user{slot.upper()}.py")
    if BADGE_APP_DIR.exists():
        remove_badge_app()
        print(f"Removed firmware/badge/apps/{APP_NAME}")

    print("Cleanup complete. Use 'git status' to verify the working tree is clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
