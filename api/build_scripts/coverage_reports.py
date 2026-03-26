import os
import platform
import re
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path


def get_color(percentage):
    if percentage < 50:
        return "red"
    elif percentage < 70:
        return "yellow"
    else:
        return "green"


def generate_badge(title, percentage, color):
    return (
        f"![Static Badge](https://img.shields.io/badge/{title.replace(' ', '_')}-{percentage}25-{color}?style="
        "flat&logo=azuredevops&logoColor=%230078D7)"
    )


def main():
    print(f"Running on branch {os.environ.get('GIT_BRANCH', 'unknown')}")

    develop = "develop" in os.environ.get("GIT_BRANCH", "unknown")
    rc_or_main = any(x in os.environ.get("GIT_BRANCH", "unknown") for x in ["patch", "rc", "main", "master", "sync"])

    try:
        report_result = subprocess.check_output(shlex.split("coverage report --data-file=.coverage")).decode()
        subprocess.check_output(shlex.split("coverage xml --data-file=.coverage"))
        subprocess.check_output(shlex.split("coverage html --data-file=.coverage"))

        print(report_result)

        diff_report_result: str | None = None
        diff_result: str | None = None
        diff_failed = False
        if not develop and not rc_or_main:
            diff_proc = subprocess.run(
                shlex.split(
                    "diff-cover coverage.xml --diff-file=diff.txt --format markdown:diff-cover-report.md "
                    "--fail-under=50"
                ),
                stdout=subprocess.PIPE,
            )
            diff_report_result = diff_proc.stdout.decode()
            diff_failed = diff_proc.returncode != 0
            print(diff_report_result)

        total_percentage = report_result.splitlines().pop().split(" ").pop()
        total_percentage_int = int(total_percentage.replace("%", ""))
        total_color = get_color(total_percentage_int)

        diff_percentage = "NA%"
        diff_percentage_int = 0
        if not develop and not rc_or_main:
            if diff_report_result:
                try:
                    diff_percentage = (
                        [line for line in diff_report_result.splitlines() if "Coverage:" in line].pop().split(" ").pop()
                    )
                    diff_percentage_int = int(diff_percentage.replace("%", ""))
                except IndexError:
                    pass

            with open("diff-cover-report.md") as diff_report:
                diff_result = diff_report.read().replace("# ", "## ").replace("__init__.py", "\\_\\_init\\_\\_.py")

                diff_result = re.sub(r"### (.+py)", r"<details>\n<summary>\1</summary>\n", diff_result)
                diff_result = re.sub(r"\n---(\n+<details>)", r"\n</details>\1", diff_result)

                diff_result += "\n</details>"

        diff_color = get_color(diff_percentage_int)
        badge = generate_badge("Diff Coverage", diff_percentage, diff_color) if (not develop and not rc_or_main) else ""

        newline = "\n"
        markdown_output = textwrap.dedent(
            f"""
        ![Static Badge](https://img.shields.io/badge/Build%20(Python%20{platform.python_version()})-passing-brightgreen)

        # Clue API - Coverage Results
        {generate_badge('Total Coverage', total_percentage, total_color)} {badge}

{newline.join([(' ' * 8) + line for line in diff_result.splitlines()]) if diff_result else ''}

        ## Full Coverage Report
        <details>
            <summary>Expand</summary>

{newline.join([(' ' * 12) + line for line in report_result.splitlines()])}
        </details>
        """
        ).strip()

        print("Markdown result:")
        print(markdown_output)

        output_path = Path(__file__).parents[1] / "coverage-results.md"
        print("Writing to:", str(output_path))
        output_path.write_text(markdown_output)

        if diff_failed:
            print("diff-cover failed: diff coverage is below 50%")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(" ".join(e.cmd), "failed.")

        if e.output:
            print(e.output.decode())

        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
