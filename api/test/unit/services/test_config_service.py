from datetime import datetime, timedelta

from clue.services import config_service

time = datetime.now() + timedelta(seconds=10)


def test_config_service_config():
    result = config_service.get_configuration()

    assert isinstance(result["configuration"]["auth"]["oauth_providers"], list)
