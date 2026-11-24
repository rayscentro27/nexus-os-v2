#!/usr/bin/env python3

from getpass import getpass
from pathlib import Path
import os
import sys


ENV_PATH = Path.home() / ".config" / "nexus" / "runtime.env"
KEY = "PGPASSWORD"


def main() -> int:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)

    password = getpass("New Supabase database password: ")
    confirm = getpass("Confirm Supabase database password: ")

    if not password:
        print("PASSWORD_UPDATE=FAILED")
        print("REASON=EMPTY_PASSWORD")
        return 1

    if password != confirm:
        print("PASSWORD_UPDATE=FAILED")
        print("REASON=PASSWORDS_DO_NOT_MATCH")
        return 1

    existing_lines = []

    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text().splitlines()

    new_lines = []
    replaced = False

    for line in existing_lines:
        if line.startswith(f"{KEY}="):
            new_lines.append(f"{KEY}={password}")
            replaced = True
        else:
            new_lines.append(line)

    if not replaced:
        new_lines.append(f"{KEY}={password}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n")
    os.chmod(ENV_PATH, 0o600)

    print("PGPASSWORD_UPDATED=YES")
    print(f"SECRET_FILE={ENV_PATH}")
    print("SECRET_FILE_MODE=600")
    print("PASSWORD_DISCLOSED=NO")

    return 0


if __name__ == "__main__":
    sys.exit(main())
