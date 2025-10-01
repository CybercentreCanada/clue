import importlib
import os
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

from clue.common.logging import get_logger

logger = get_logger(__file__)

scheduler = BackgroundScheduler(timezone=timezone(os.getenv("SCHEDULER_TZ", "America/Toronto")))


def setup_jobs():
    """Imports all modules in the current directory (cronjobs) and adds them to the scheduler."""
    module_path = Path(__file__).parent
    modules_to_import = [
        _file for _file in module_path.iterdir() if _file.suffix == ".py" and _file.name != "__init__.py"
    ]

    for module in modules_to_import:
        try:
            job = importlib.import_module(f"clue.cronjobs.{module.stem}")

            job.setup_job(scheduler)
        except Exception as e:
            logger.critical("Error when initializing %s - %s", module, e)

    if scheduler.state != 1:
        scheduler.start()
