import os
from pathlib import Path
from unittest.mock import patch

import pytest
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic_core import Url
from pytz import timezone

from clue.api.v1.registration import EXTERNAL_PLUGIN_SET
from clue.config import config
from clue.cronjobs import scheduler, setup_jobs
from clue.cronjobs.plugins import update_external_source_list
from clue.models.config import ExternalSource


@pytest.fixture()
def sample_external_source():
    return ExternalSource(
        name="test",
        classification="TLP:CLEAR",
        max_classification="TLP:CLEAR",
        url="http://localhost:5008/",
        maintainer="Example <example@example.com>",
        datahub_link=Url("http://example.com"),
        documentation_link=Url("http://example.com"),
        built_in=False,
    ).model_dump(mode="json", exclude_none=True)


@pytest.fixture()
def mock_scheduler():
    mock_scheduler = BackgroundScheduler(timezone=timezone(os.getenv("SCHEDULER_TZ", "America/Toronto")))
    return mock_scheduler


def test_update_external_source_list(host, mock_scheduler: BackgroundScheduler, sample_external_source: ExternalSource):
    EXTERNAL_PLUGIN_SET.pop_all()
    update_external_source_list()
    assert all(item.built_in for item in config.api.external_sources)

    EXTERNAL_PLUGIN_SET.add(sample_external_source)
    update_external_source_list()

    assert sample_external_source in EXTERNAL_PLUGIN_SET.members()
    mock_scheduler.remove_all_jobs()
    assert not all(item.built_in for item in config.api.external_sources)

    EXTERNAL_PLUGIN_SET.remove(sample_external_source)
    update_external_source_list()
    assert all(item.built_in for item in config.api.external_sources)
    assert sample_external_source not in EXTERNAL_PLUGIN_SET.members()
    mock_scheduler.remove_all_jobs()


def test_job_scheduler(host):
    if scheduler.state == 1:
        scheduler.remove_all_jobs()
        scheduler.shutdown(False)

    root_dir = Path(__file__).parent.parent.parent.parent
    module_path = root_dir / "clue" / "cronjobs"
    modules_to_import = [
        _file for _file in module_path.iterdir() if _file.suffix == ".py" and _file.name != "__init__.py"
    ]

    setup_jobs()
    assert len(scheduler.get_jobs()) == len(modules_to_import)
    scheduler.remove_all_jobs()
    scheduler.shutdown(False)


def test_job_scheduler_exception_raised(host):
    exception = Exception("Mocked exception")
    with patch("importlib.import_module") as mock_import:
        mock_import.side_effect = exception
        setup_jobs()
        assert len(scheduler.get_jobs()) == 0
        scheduler.shutdown(False)
