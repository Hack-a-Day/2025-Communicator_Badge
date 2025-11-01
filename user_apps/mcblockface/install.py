#!/usr/bin/env python3
"""Installer for the BlockyBlockMcBlockFace user app."""

# The script auto-detects the repository root by walking upwards until it finds
# both firmware/ and user_apps/. If you adapt it for another project, adjust the
# detection logic below as needed.

APP_DISPLAY_NAME = "BlockyBlockMcBlockFace"

import argparse
import os
import shutil
import sys
from pathlib import Path


class InstallerError(Exception):
    pass


def find_repo_root(start: Path) -> Path:
    current = start
    for _ in range(8):
        if (current / "firmware").is_dir() and (current / "user_apps").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    raise InstallerError("Could not locate repository root containing firmware/ and user_apps/ directories.")


REPO_ROOT = find_repo_root(Path(__file__).resolve().parent)
if Path.cwd() != REPO_ROOT:
    os.chdir(REPO_ROOT)

USER_APPS_ROOT = REPO_ROOT / "user_apps"
FIRMWARE_APPS_ROOT = REPO_ROOT / "firmware" / "badge" / "apps"
APP_NAME = "mcblockface"
APP_ALIAS = APP_DISPLAY_NAME.replace(" ", "") + "App"

USER_SLOT_FILES = {
    "a": FIRMWARE_APPS_ROOT / "userA.py",
    "b": FIRMWARE_APPS_ROOT / "userB.py",
    "c": FIRMWARE_APPS_ROOT / "userC.py",
    "d": FIRMWARE_APPS_ROOT / "userD.py",
}

USER_SLOT_DOCS = {
    "a": "User A",
    "b": "User B",
    "c": "User C",
    "d": "User D",
}

README_TEMPLATE = (
    "\n"
    f"Installing {APP_DISPLAY_NAME} {{version}}\n"
    "Target slot: {slot} ({slot_name})\n"
    "\n"
    "This will:\n"
    "  1. Copy user_apps/{app_name} into firmware/badge/apps/{app_name}\n"
    "  2. Update firmware/badge/apps/user{slot_upper}.py to import the app from firmware/badge/apps/{app_name}\n"
    "  3. Preserve the original user{slot_upper}.py content in user_apps/{app_name}/backups/\n"
)

BACKUP_DIR = USER_APPS_ROOT / APP_NAME / "backups"
TARGET_DIR = FIRMWARE_APPS_ROOT / APP_NAME
SOURCE_DIR = USER_APPS_ROOT / APP_NAME
VERSION_FILE = SOURCE_DIR / "VERSION"


def load_version() -> str:
    if not VERSION_FILE.exists():
        return "unknown"
    return VERSION_FILE.read_text(encoding="utf-8").strip()
def ensure_firmware_tree() -> None:
    if not FIRMWARE_APPS_ROOT.exists():
        raise InstallerError(
            f"Expected firmware/badge/apps at '{FIRMWARE_APPS_ROOT}'. Please run this inside the firmware repo."
        )


def copy_app_tree() -> None:
    target = TARGET_DIR
    source = SOURCE_DIR
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("*.pyc", "__pycache__", "backups"))


def backup_user_slot(slot: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"user{slot.upper()}_backup.py"
    shutil.copy2(USER_SLOT_FILES[slot], backup_path)
    return backup_path


def write_user_slot(slot: str) -> None:
    slot_path = USER_SLOT_FILES[slot]
    slot_path.write_text(
        (
            f'"""{APP_DISPLAY_NAME} redirection."""\n\n'
            f"from apps.{{app}} import App as {APP_ALIAS}\n\n"
            f"class App({APP_ALIAS}):\n"
            f"    \"\"\"Launch {APP_DISPLAY_NAME} from the menu.\"\"\"\n"
            "    def __init__(self, name: str, badge):\n"
            "        super().__init__(name, badge)\n"
        ).format(app=APP_NAME),
        encoding="utf-8",
    )


def prompt_confirmation(message: str) -> bool:
    response = input(f"{message} [y/N]: ").strip().lower()
    return response in ("y", "yes")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=f"Install {APP_DISPLAY_NAME} into the badge app slots.")
    parser.add_argument(
        "slot",
        choices=["a", "b", "c", "d"],
        help="Target user app slot (a, b, c, or d).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts (not recommended).",
    )

    args = parser.parse_args(argv)
    slot = args.slot
    slot_name = USER_SLOT_DOCS[slot]

    try:
        ensure_firmware_tree()
    except InstallerError as exc:
        print(f"Error: {exc}")
        return 1

    version = load_version()
    summary = README_TEMPLATE.format(
        version=version,
        slot=slot,
        slot_name=slot_name,
        slot_upper=slot.upper(),
        app_name=APP_NAME,
    )
    print(summary)

    if not args.force:
        if not prompt_confirmation("Proceed with installation?"):
            print("Aborted.")
            return 0

    try:
        backup_path = backup_user_slot(slot)
        copy_app_tree()
        write_user_slot(slot)
    except (OSError, InstallerError) as exc:
        print(f"Installation failed: {exc}")
        return 1

    print("Installation complete.")
    print(f"- App copied to {TARGET_DIR.relative_to(REPO_ROOT)}")
    print(f"- Original user{slot.upper()}.py backed up at {backup_path.relative_to(REPO_ROOT)}")
    print(f"- user{slot.upper()}.py now points to {APP_DISPLAY_NAME}")
    print("Run 'scripts/update.py --reset push' to flash the updated badge tree.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
