from apscheduler.schedulers.base import BaseScheduler
from gevent.queue import Queue
from pydantic import ValidationError

from clue.api.v1.registration import EXTERNAL_PLUGIN_SET, is_registration_url_allowed
from clue.common.logging import get_logger
from clue.config import config
from clue.models.config import ExternalSource

logger = get_logger(__file__)

config_updates = Queue()

__scheduler_instance: BaseScheduler | None = None


def update_external_source_list():
    """Updates the external_sources list with the plugins that have been registered through the API."""
    built_in_sources = [item for item in config.api.external_sources if item.built_in is True]
    source_names = {source.name for source in built_in_sources}
    plugin_list: list[ExternalSource] = []

    for item in EXTERNAL_PLUGIN_SET.members():
        try:
            source = ExternalSource.model_validate({**item, "built_in": False})
        except ValidationError:
            logger.warning("Ignoring invalid runtime external source configuration")
            continue
        if not is_registration_url_allowed(source.url):
            logger.warning("Ignoring runtime source %s because its origin is not allowed", source.name)
            continue
        if source.name in source_names:
            logger.warning("Ignoring duplicate runtime source name %s", source.name)
            continue

        source_names.add(source.name)
        plugin_list.append(source)

    config.api.external_sources = built_in_sources + plugin_list


def setup_job(sched: BaseScheduler):
    """Sets the scheduler instance to the one provided, and refreshes the external sources.

    Arguments:
        sched: The scheduler instance to set.
    """
    global __scheduler_instance
    __scheduler_instance = sched
    sched.add_job(update_external_source_list, "interval", minutes=1)
    logger.debug("Plugin job setup complete.")
