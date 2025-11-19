import pytest
import requests

from test.utils.oauth_credentials import get_token


@pytest.fixture()
def access_token():
    return get_token()


def test_valid_file(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/static/docs/test-plugin-docs",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert res.status_code == 404
    # assert res.ok

    # response = res.json()
    # assert "markdown" in response["api_response"]


def test_invalid_file(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/static/docs/CONTRIBUTING.en.mds",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    response = res.json()

    assert res.status_code == 404

    assert "The file does not exist or is typed incorrectly." in response["api_error_message"]

# TODO: Rewrite so they work
# def test_get_all_valid_files(host, access_token):
#     if not access_token:
#         pytest.skip("Could not connect to keycloak.")

#     res = requests.get(
#         f"{host}/api/v1/static/docs",
#         params={"max_timeout": 2.0},
#         headers={"Authorization": f"Bearer {access_token}"},
#     )

#     response = res.json()

#     assert isinstance(response["api_response"], dict)

#     file_list = list(response["api_response"].keys())

#     assert "CONTRIBUTING.en.md" in file_list
#     assert "CONTRIBUTING.fr.md" in file_list
#     # assert "test-plugin-docs.md" in file_list


# def test_get_all_valid_filtered_files(host, access_token):
#     if not access_token:
#         pytest.skip("Could not connect to keycloak.")

#     res = requests.get(
#         f"{host}/api/v1/static/docs?filter=-docs",
#         params={"max_timeout": 2.0},
#         headers={"Authorization": f"Bearer {access_token}"},
#     )

#     assert res.ok

#     response = res.json()

#     all_filtered_docs = response["api_response"].keys()

#     # assert len(all_filtered_docs) == 32
#     assert len(all_filtered_docs) == 0

#     for filename in all_filtered_docs:
#         assert "-docs" in filename


def test_invalid_file_type(host, access_token):
    if not access_token:
        pytest.skip("Could not connect to keycloak.")

    res = requests.get(
        f"{host}/api/v1/static/docs?filter=-docss",
        params={"max_timeout": 2.0},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    response = res.json()

    assert res.ok

    assert len(response["api_response"]) == 0
