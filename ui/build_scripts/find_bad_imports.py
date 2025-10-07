#!/usr/bin/python3

import glob
import sys
import textwrap
from pathlib import Path

BANNED_STRINGS = [
    (
        "@mui/icons-material",
        "Using @mui/icons-material in exported components leads to issues when importing and using borealis in other "
        "applications: https://stackoverflow.com/questions/78815858/mui-icons-material-vitest-es-module-issue",
    ),
    (
        "@mui/material/colors",
        "Using @mui/material/colors in exported components leads to issues when importing and using borealis in other "
        "applications.",
    ),
    (
        "lib/main",
        "Using lib/main.ts in exported components leads to issues when exporting types.",
    ),
    (
        "process.env",
        "Using process.env unguarded can lead to errors in downstream applications.",
    ),
]

root = Path(__file__).parent.parent

lib_dir = root / "src" / "lib"

print("Ensuring no banned imports are used in the lib directory: ", end="")

for filename in glob.glob(str(lib_dir / "**/*.ts*"), recursive=True):
    if "test.ts" in filename:
        continue

    _file = Path(filename)
    data = _file.read_text()

    for banned_string, explanation in BANNED_STRINGS:
        if banned_string in data:
            print("failed")

            indent = "\n" + (len(banned_string) + 4) * " "

            print(f"ERROR: {_file.relative_to(root)} contains a banned string:")
            print(
                f"> {banned_string}: {indent.join(textwrap.wrap(explanation, width=120))}"
            )
            sys.exit(1)

print("passed")
