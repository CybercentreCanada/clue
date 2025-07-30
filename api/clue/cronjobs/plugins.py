from apscheduler.schedulers.base import BaseScheduler
from gevent.queue import Queue

from clue.api.v1.registration import EXTERNAL_PLUGIN_SET
from clue.common.logging import get_logger
from clue.config import config
from clue.models.config import ExternalSource

logger = get_logger(__file__)

config_updates = Queue()

__scheduler_instance: BaseScheduler | None = None


def update_external_source_list():
    """Updates the external_sources list with the plugins that have been registered through the API."""
    plugin_list: list[ExternalSource] = [ExternalSource.model_validate(item) for item in EXTERNAL_PLUGIN_SET.members()]
    config.api.external_sources = [item for item in config.api.external_sources if item.built_in is True]
    config.api.external_sources.extend(plugin_list)


def setup_job(sched: BaseScheduler):
    """Sets the scheduler instance to the one provided, and refreshes the external sources.

    Arguments:
        sched: The scheduler instance to set.
    """
    global __scheduler_instance
    __scheduler_instance = sched
    sched.add_job(update_external_source_list, "interval", minutes=1)
    logger.debug("Plugin job setup complete.")
