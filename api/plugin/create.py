from plugin.commands import header


def main():
    header("Clue Plugin Generation", "This script will walk you through the creation of a new clue plugin.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\rExiting!" + " " * 80)
