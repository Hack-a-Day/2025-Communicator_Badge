#!/bin/env python3

# I've now realized mpremote does everything this script does and more, so it should
# probably be deleted.

import argparse
import binascii
import hashlib
import os
import pathlib
import subprocess


def check_path(path: str, ) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    top_path = pathlib.Path(path)
    for file_path in top_path.iterdir():
        if file_path.is_file():
            with open(file_path, "rb") as file:
                hasher = hashlib.sha256(file.read())
                files[file_path.as_posix()] = hasher.digest()
        else:
            if file_path.name == "__pycache__":
                continue
            files.update(check_path(str(file_path)))
            files[file_path.as_posix()] = b""
    return files

def check_dir(path: str) -> dict[str, str]:
    files_uncleaned = check_path(path)
    files = {fn.replace(path.strip() + "/", "/").replace("\\", "/"): binascii.hexlify(hash).decode() for fn, hash in files_uncleaned.items()}
    return files

def get_badge_files() -> dict[str, str]:
    """Get the files on the badge and their checksums."""
    badge_files_text = subprocess.run(["mpremote", "run", "./scripts/check_filesystem.py"], capture_output=True, text=True).stdout
    badge_files = {}
    for line in badge_files_text.split("\n"):
        if " " in line:
            try:
                name, checksum = line.split(" ")
                badge_files[name] = checksum.strip()[2:-1]
            except ValueError as err:
                print(err)
                print(line)
    return badge_files

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Badge Updater")
    parser.add_argument("action", type=str, nargs="?", default="ls", help="Action to perform: 'ls' to list files (default), 'push' to push files, 'pull' to pull files.")
    parser.add_argument("--reset", action="store_true", default=False, help="Reset the badge after.")
    parser.add_argument("--verbose", "-v", action="store_true", default=False)
    args = parser.parse_args()
    if args.action not in ("ls", "list", "push", "pull"):
        print(f"Unknown action '{args.action}'. Use 'ls', 'push', or 'pull'.")
        exit(1)

    if args.action == "push":
        print("Checking badge/ directory...")
        local_files = check_dir("badge")
        print("Checking files on badge...")
        badge_files = get_badge_files()
        for name in sorted(local_files.keys()):
            hash = local_files[name]
            if name not in badge_files and hash == "":
                print(f"Creating directory {name}...")
                subprocess.run(["mpremote", "mkdir", name], check=True)
            elif name not in badge_files or badge_files[name] != hash:
                if name not in badge_files:
                    print(f"Creating {name}...")
                else:
                    print(f"Updating {name}...")
                subprocess.run(["mpremote", "cp", f"badge{name}", f":{name}"], check=True)
            else:
                if args.verbose:
                    print(f"{name} is up to date.")
        files_to_delete = set(badge_files.keys()) - set(local_files.keys())
        for name in files_to_delete:
            if name.startswith("/data"):  # Don't delete the data/ directory.
                continue
            if badge_files[name] == "":
                print(f"Removing directory {name} from badge...")
                subprocess.run(["mpremote", "rmdir", name], check=True)
            else:
                print(f"Deleting {name} from badge...")
                subprocess.run(["mpremote", "rm", name], check=True)

    if args.action == "pull":
        print("Pulling files from badge...")
        badge_files = get_badge_files()
        if not os.path.exists("badge-backup"):
            os.makedirs("badge-backup")
        file_text = subprocess.run(["mpremote", "cp", "-r", ":", "badge-backup/"], check=True)
        # for name in badge_files.keys():
        #     print(f"Pulling {name}...")
        #     with open(f"badge-backup/{name}", "w") as file:
        #         file.write(file_text)
        print("Files pulled successfully.")

    if args.action in ("ls", "list"):
        local_files = check_dir("badge")
        badge_files = get_badge_files()
        print("Files on badge:")
        print("Status values: * different, + only on local (push will add), - only on badge (push will delete)")
        print(f"Status {'Filename':<40s} SHA256")
        all_files = set(local_files.keys()).union(set(badge_files.keys()))
        for name in sorted(all_files):
            if name in local_files and name in badge_files:
                if local_files[name] == badge_files[name]:
                    status = " "
                else:
                    status = "*"
            elif name in badge_files:
                status = "-"
            elif name in local_files:
                status = "+"
            else:
                status = "?"
            hash = badge_files[name] if name in badge_files else local_files[name]
            if hash == "":
                hash = "directory"
            print(f"{status}      {name:<40s} {hash}")

    if args.reset:
        print("Resetting badge...")
        subprocess.run(["mpremote", "reset"], check=True)