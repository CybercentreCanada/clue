import os
import platform
import re
import shlex
import subprocess
import sys
import textwrap
import time
from pathlib import Path


def prep_command(cmd: str):
    print(">", cmd)
    return shlex.split(cmd)


def generate_flask_command(server_id: str, port: int):
    if len(sys.argv) < 2:
        preamble = f"coverage run --data-file=.coverage.{server_id} -m "
    else:
        preamble = ""

    return f"{preamble}flask --app test.utils.{server_id} run --no-reload --port {port}"


def main():  # noqa: C901
    servers: list[subprocess.Popen] = []
    try:
        if Path(".coverage").exists():
            print("Removing existing coverage files")
            subprocess.check_call(
                prep_command("coverage erase --data-file=.coverage"),
            )

        print("Running test enrichments")
        servers.append(
            subprocess.Popen(
                prep_command(generate_flask_command("test_server", 5008)),
                env={**os.environ.copy(), "SKIP_DISCOVERY": "true", "TESTING": "true"},
            )
        )
        servers.append(
            subprocess.Popen(
                prep_command(generate_flask_command("bad_server", 5009)),
                env={**os.environ.copy(), "SKIP_DISCOVERY": "true", "TESTING": "true"},
            )
        )
        servers.append(
            subprocess.Popen(
                prep_command(generate_flask_command("slow_server", 5010)),
                env={**os.environ.copy(), "SKIP_DISCOVERY": "true", "TESTING": "true"},
            )
        )
        servers.append(
            subprocess.Popen(
                prep_command(generate_flask_command("telemetry_server", 5011)),
                env={**os.environ.copy(), "SKIP_DISCOVERY": "true", "TESTING": "true"},
            )
        )
        servers.append(
            subprocess.Popen(
                prep_command("flask --app test.utils.test_server run --no-reload --port 5012"),
                env={
                    **os.environ.copy(),
                    "SKIP_DISCOVERY": "true",
                    "CLASSIFICATION": "TLP:AMBER+STRICT",
                    "TESTING": "true",
                },
            )
        )

        print(f"Running central API {'(with coverage)' if len(sys.argv) < 2 else ''}")
        servers.append(
            subprocess.Popen(
                prep_command(f"{'coverage run -m ' if len(sys.argv) < 2 else ''}flask --app clue.app run --no-reload"),
                env={**os.environ.copy(), "SKIP_DISCOVERY": "true", "DISABLE_CACHE": "true", "TESTING": "true"},
            )
        )

        time.sleep(2)

        print("Running pytest")
        if len(sys.argv) > 1:
            pytest = subprocess.Popen(
                prep_command(f"pytest -rP -vv {' '.join(sys.argv[1:])}"),
            )
        else:
            pytest = subprocess.Popen(
                prep_command("pytest --cov=clue --cov-branch --cov-config=.coveragerc.pytest -rfE -vv test"),
                stdout=subprocess.PIPE,
            )

        output = ""
        while pytest.poll() is None:
            if pytest.stdout:
                out = pytest.stdout.read(1).decode()
                output += out
                sys.stdout.write(out)
                sys.stdout.flush()

        if pytest.stdout:
            out = pytest.stdout.read().decode()
            output += out
            sys.stdout.write(out)
            sys.stdout.flush()

        return_code = pytest.poll()
        if return_code is not None and return_code > 0:
            if output and os.environ.get("WRITE_MARKDOWN", ""):
                markdown_output = textwrap.dedent(
                    f"""
                ![Static Badge](https://img.shields.io/badge/build%20(Python%20{platform.python_version()})-failing-red)

                <details>
                    <summary>Error Output</summary>
                """
                ).strip()

                markdown_output += "\n".join(
                    ("    " + line)
                    for line in re.sub(
                        r"[\s\S]+=+ FAILURES =+([\S\s]+)-+ coverage[\s\S]+",
                        r"\n\1",
                        output,
                    ).splitlines()
                )

                markdown_output += "\n</details>"

                print("Markdown result:")
                print(markdown_output)

                (Path(__file__).parent.parent / "test-results.md").write_text(markdown_output)

            raise subprocess.CalledProcessError(return_code, pytest.args, output=output, stderr=None)  # noqa: TRY301

        print("Shutting down background servers")

        for server in servers:
            server.terminate()

        if len(sys.argv) > 1:
            return

        print("Coverage server is down, combining coverage files")

        workdir = Path(__file__).parent.parent
        if not (workdir / ".coverage.server").exists():
            print("WARN: .coverage.server file missing!")

        if not (workdir / ".coverage.pytest").exists():
            print("WARN: .coverage.pytest file missing!")

        if not (workdir / ".coverage.test_server").exists():
            print("WARN: .coverage.test_server file missing!")

        if not (workdir / ".coverage.bad_server").exists():
            print("WARN: .coverage.bad_server file missing!")

        if not (workdir / ".coverage.slow_server").exists():
            print("WARN: .coverage.slow_server file missing!")

        if not (workdir / ".coverage.telemetry_server").exists():
            print("WARN: .coverage.telemetry_server file missing!")

        subprocess.check_call(
            prep_command(
                "coverage combine --data-file=.coverage .coverage.server .coverage.pytest .coverage.test_server "
                ".coverage.bad_server .coverage.slow_server"
            ),
        )

    except subprocess.CalledProcessError as e:
        print("Error occurred while running script:", e)
        print("Shutting down background servers")
        for server in servers:
            server.terminate()
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
