# import logging

# import pytest

# from clue.models.actions import Action, ExecuteRequest
# from clue.models.network import QueryEntry
# from clue.plugin import CluePlugin
# from clue.plugin.helpers.central_server import connect_to_central_server


# class ExecuteTestParams(ExecuteRequest):
#     rationale: str


# @pytest.fixture(scope="module")
# def mock_plugin():
#     plugin = CluePlugin(
#         app_name="tester",
#         supported_types={"ipv4", "ipv6"},
#         enrich=lambda *args: QueryEntry(count=10, annotations=[], link="https://example.com"),
#         logger=logging.getLogger("test"),
#         actions=[
#             Action[ExecuteTestParams](
#                 id="other_action",
#                 name="Test Action",
#                 classification="TLP:CLEAR",
#                 summary="Another Test Action",
#                 supported_types={"ip"},
#                 accept_multiple=True,
#             ),
#         ],
#     )

#     return plugin


# def test_connect(mock_plugin: CluePlugin, caplog):
#     with (
#         mock_plugin.app.test_request_context(headers={"X-Clue-Authorization": "Bearer potato.potato"}),
#         caplog.at_level(logging.DEBUG),
#     ):
#         connect_to_central_server()

#     assert "using pre-OBO token" in caplog.text

#     caplog.clear()

#     with (
#         mock_plugin.app.test_request_context(headers={"Authorization": "Bearer potato.potato"}),
#         caplog.at_level(logging.DEBUG),
#     ):
#         connect_to_central_server()

#     assert "X-Clue-Authorization header not specified" in caplog.text

#     caplog.clear()

#     with mock_plugin.app.test_request_context(), caplog.at_level(logging.DEBUG):
#         connect_to_central_server()

#     assert "No token specified, continuing with no authentication" in caplog.text

#     caplog.clear()
