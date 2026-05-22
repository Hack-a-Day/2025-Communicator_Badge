#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path


def discover_ports():
    try:
        from serial.tools import list_ports
    except Exception as exc:
        raise RuntimeError("pyserial is required to auto-detect serial ports") from exc
    return [p.device for p in list_ports.comports()]


def run_cmd(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def run_cmd_allow_fail(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=False)


def flash_port(port, source_dir, reset=True):
    # Clean artifacts from accidental nested copies so imports resolve correctly.
    run_cmd_allow_fail(["mpremote", "connect", port, "rm", "-r", "badge"])
    run_cmd_allow_fail(["mpremote", "connect", port, "rm", "-r", "net/net"])

    source_dot = str(source_dir) + os.sep + "."
    run_cmd(["mpremote", "connect", port, "cp", "-r", source_dot, ":"])
    # Enable safer startup for serial HITL stability.
    run_cmd_allow_fail([
        "mpremote",
        "connect",
        port,
        "exec",
        "import json; p='/data/config.json'; d={};\n"
        "\n"
        "try:\n"
        "  d=json.loads(open(p).read())\n"
        "except Exception:\n"
        "  d={}\n"
        "d['hitl_mode']='1'\n"
        "open(p,'w').write(json.dumps(d))\n"
        "print('hitl_mode set')",
    ])
    if reset:
        run_cmd(["mpremote", "connect", port, "reset"])


def main():
    parser = argparse.ArgumentParser(description="Flash current firmware to all connected badges")
    parser.add_argument(
        "--ports",
        nargs="*",
        default=None,
        help="Optional explicit serial ports (e.g. COM6 COM7). If omitted, auto-detect all serial ports.",
    )
    parser.add_argument(
        "--source",
        default="badge",
        help="Firmware source folder to copy to the badge root (default: badge)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not reset badges after flashing",
    )
    args = parser.parse_args()

    source_dir = Path(args.source).resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise SystemExit("Source directory not found: %s" % source_dir)

    ports = args.ports or discover_ports()
    if not ports:
        raise SystemExit("No serial ports found.")

    print("Flashing firmware from %s" % source_dir)
    print("Ports:", ", ".join(ports))

    failures = []
    for port in ports:
        print("\n=== Flashing %s ===" % port)
        try:
            flash_port(port, source_dir, reset=not args.no_reset)
        except subprocess.CalledProcessError as exc:
            failures.append((port, exc.returncode))

    if failures:
        print("\nFailures:")
        for port, code in failures:
            print("- %s (exit code %s)" % (port, code))
        raise SystemExit(1)

    print("\nAll selected badges flashed successfully.")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
