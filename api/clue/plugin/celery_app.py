from typing import List

from celery import Celery, Task
from flask import Flask

celery = Celery("app")


def celery_init_app(app: Flask, tasks: List[str] | None = None) -> None:
    """initialize the celery worker for the flask app

    Args:
        app (Flask): flask app instance
    """

    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    if tasks:
        celery_app.autodiscover_tasks(
            tasks,
            force=True,
        )
    app.extensions["celery"] = celery_app
