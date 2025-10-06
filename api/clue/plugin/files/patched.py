from gevent.monkey import patch_all

patch_all()

from app import app, main  # noqa: F401, E402
