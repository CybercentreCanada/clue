from gevent.monkey import patch_all

patch_all()

from clue.app import app, main  # noqa: F401, E402

if __name__ == "__main__":
    main()
