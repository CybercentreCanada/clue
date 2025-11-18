import os
import shlex
import subprocess
import sys


def execute_command(cmd: str):
    print(">", cmd)
    return subprocess.check_output(shlex.split(cmd)).decode()


def main():
    # Short-circuit on manual builds
    if os.environ["BUILD_REASON"].lower() == "manual":
        has_changes = "True"
    else:
        last_successful_commit = os.environ["LAST_SUCCESS"]

        print(f"Last successful commit: {last_successful_commit}")

        result = execute_command(f"git --no-pager diff --no-color --name-only {last_successful_commit} {sys.argv[1]}")

        print(result)

        has_changes = str(True if result.strip() else False).lower()

    print(f"Changes in directory: {has_changes}")

    print(f"##vso[task.setvariable variable=changed]{has_changes}")


if __name__ == "__main__":
    main()
