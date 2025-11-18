import shlex
import subprocess
import textwrap
from pathlib import Path

from termcolor import colored


def header(title: str, subtitle: str | None):
    width = max(len(title) + 4, 70)

    print(colored("\n" + ("#" * width), "green"))
    print(colored(f"# {title.center(width - 4)} #", "green"))
    print(colored("#" * width, "green"), end="\n")
    if subtitle:
        for line in textwrap.wrap(subtitle, width=width):
            print(line)

    print()


def warn(*messages: str):
    "Print error message"
    print(f"[{colored("warn", "yellow")}]", *messages)


def error(*messages: str):
    "Print error message"
    print(f"[{colored("error", "red")}]", *messages)


def info(*messages: str):
    "Print info message"
    print(f"[{colored("info", "cyan")}]", *messages)


def success(title: str, latency: float | None = None, skip_wait: bool = False):
    title = colored(title, "green")

    if latency is not None:
        title += " " + colored(f"({latency:.2f}s)", "dark_grey")

    print(title)

    if not skip_wait:
        wait_to_continue()


def prep_command(cmd: str) -> list[str]:
    print(f"> {colored(cmd, 'dark_grey')}", end="\n\n")
    return shlex.split(cmd)


def confirm(prompt: str, default_yes: bool = False) -> bool:
    response = input(
        f"{colored(prompt, 'blue')} [{f'{colored('Y', 'green')}/{colored('n', 'red')}' if default_yes else
                                      f'{colored('y', 'green')}/{colored('N', 'red')}'}] "
    )

    if response.lower() in ["y", "yes"] or not response and default_yes:
        return True

    return False


def wait_to_continue():
    input(colored("Press enter to continue. ", "blue"))
    print()


def execute(
    cmd: list[str] | str, check: bool = True, capture_output: bool = False, cwd: Path | str | None = None
) -> subprocess.CompletedProcess:
    if isinstance(cmd, str):
        cmd = prep_command(cmd)

    if isinstance(cwd, Path):
        cwd = str(cwd)

    return subprocess.run(cmd, check=check, capture_output=capture_output, cwd=cwd)


def cmd_exists(cmd: str) -> bool:
    try:
        subprocess.run(shlex.split(f"which {cmd}"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return True
    except subprocess.CalledProcessError:
        return False


def get_output(cmd: list[str] | str, check: bool = True) -> str:
    return execute(cmd, check=check, capture_output=True).stdout.decode()


def fails(cmd: str) -> bool:
    try:
        subprocess.run(shlex.split(cmd), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return False
    except subprocess.CalledProcessError:
        return True
