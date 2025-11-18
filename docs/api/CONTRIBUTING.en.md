# Creating a new Clue Plugin

## Introduction

Clue aims to function as a connecting tissue of sorts between applications. Initially envisioned primarily as an
enrichment platform, its functionality has expanded to also permit execution of actions through a unified interface, and
will eventually include fetching representations of data (i.e. email renders, process trees for a host, etc.)

In order to accomplish this, clue supports a plugin architecture, where services are configured such that clue
knows to reach out to a given plugin in various circumstances. For example, a request to execute the action
`example_plugin.example_action` would be directed to the plugin with id `example_plugin`. For enrichment, the central
server requests all relevant plugins to provide enrichment annotations for a given selector.

This document will walk you through developing, publishing and deploying a new clue plugin.

## Design

The "default" approach to clue plugins is to run a flask server in a containerized environment, with
communication between plugins occurring through the central API. However, plugins can be hosted anywhere that is
accessible by the central server. The actual process of executing an application looks something like this:

### Request Initiation

Various client applications can make requests to the central API, which will in turn proxy requests to every relevant registered plugin.

![Request Initiation Diagram](https://mermaid.ink/img/pako:eNqFkk9PwkAQxb_KZrxoAgfg1oMJCokcTIjIRcphbId24_6p012RAN_dpaWxpqJ7mjf5vZmX7OwhsSlBBBtlt0mO7MTzJDYivAe7VcTL2aouxHK2Fv3-7WFqWCa5JuPEE717Kt3hzNa-cVmSflU7JQ0Fd1v-OaMNthM0-8fz2iwWxB_E1_fBzajEnWVCJcsTcNON8DNAM-TXBP8ProkqxVz5TJrBavqJulB01uJqsL6ADjvo8BI66qCjCoUeaGKNMg0_tj91YnA5aYohCmWK_BZDbI6BQ-_sYmcSiBx76gFbn-WN8EWKjiYSM0YN0QZVGboFmhdrvzWl0ll-rO-jOpPjF8rrveU?type=png)

### Response

The responses from each plugin are then merged together and returned with some metadata to the client application.

![Response Explanation](https://mermaid.ink/img/pako:eNqNkjFvwjAQhf-K5S6tBAPJlqESBaQyVEKlLCUMp_iSWLV90cUprQj_vYYEAaIDXnzv-d2nk847mZFCmcjc0DYrgb34mKZOhLMwTaHdaD37AVsZ7LV4GG3EcPjczhzrrLTovBg7Rx68JleLnPicbMUS-Rv5EhjdAKO7gdF_wPgGGN8NjK-BXf04CS0MRrwQIxhdi_Fi_nRETgKAjFbgUYkL_jvWVXjCVrzS1iCvu-vQuOnQvREgfbman0KrLiMH0iJb0CqsY3dwUulLtJjKJJQK-CuVqduHHDSelr8uk4nnBgeSqSnKk2iqw3hTDQWDlUkOpg5uBe6T6KxRaU_81i3_-Af2f73PsxQ?type=png)

## Valid Plugin Operations

### Enrichment

Enrichments are a bread and butter of clue. This entails the user requesting enrichment information about a given
selector by making a network call to the central API, like this:

```python
# Enriching a single selector
res = requests.get(
    f"{host}/api/v1/lookup/enrich/ip/127.0.0.1",
    params={"max_timeout": 2.0},
    headers={"Authorization": f"Bearer {access_token}"},
)

# Bulk enrichment of selectors
bulk_req = [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}]

res = requests.post(
    f"{host}/api/v1/lookup/enrich",
    params={"max_timeout": 5.0, "sources": "test|bad"},
    headers={"Authorization": f"Bearer {access_token}"},
    json=bulk_req,
)
```

For a single enrichment, the response body will be a `QueryResult`:

<details>
<summary>QueryResult Example</summary>

```json
{
  "type": "ip",
  "value": "127.0.0.1",
  "source": "example_plugin",
  "error": null,
  "items": [
    {
      "classification": "TLP:CLEAR",
      "count": 23,
      "link": "https://example.com/moreinfo",
      "annotations": [
        {
          "analytic": "Assemblyline",
          "analytic_icon": "material-symbols:sound-detection-dog-barking",
          "author": null,
          "quantity": 10,
          "version": "1.0.0",
          "timestamp": "2024-12-16T12:54:26.374945+00:00",
          "type": "context",
          "value": "suspect",
          "confidence": 0.0,
          "severity": 0.0,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": "# Here's some annotation details\\n\\nIt's very interesting",
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": true
        },
        {
          "analytic": "Howler",
          "analytic_icon": null,
          "author": null,
          "quantity": 10,
          "version": "v0.0.1",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "context",
          "value": "benign",
          "confidence": 1.0,
          "severity": 1.0,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": true
        },
        {
          "analytic": "Assemblyline",
          "analytic_icon": null,
          "author": "John Smith",
          "quantity": 25,
          "version": "1.0.0",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "mitigation",
          "value": 42.0,
          "confidence": 0.0,
          "severity": 0.5,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": "# Here's some annotation details\\n\\nIt's very interesting",
          "link": null,
          "icon": null,
          "ubiquitous": false
        }
      ],
      "raw_data": {
        "id": 1,
        "raw_field": "some_data"
      }
    },
    {
      "classification": "TLP:CLEAR",
      "count": 9,
      "link": null,
      "annotations": [
        {
          "analytic": "Howler",
          "analytic_icon": "material-symbols:sound-detection-dog-barking",
          "author": null,
          "quantity": 10,
          "version": null,
          "timestamp": "2024-12-16T12:54:26.374945+00:00",
          "type": "frequency",
          "value": 42.0,
          "confidence": 0.5,
          "severity": 0.0,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": true
        },
        {
          "analytic": null,
          "analytic_icon": null,
          "author": "John Smith",
          "quantity": 25,
          "version": "v0.0.1",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "context",
          "value": "Involved in Operation Cat",
          "confidence": 1.0,
          "severity": 0.5,
          "priority": 1.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": false
        }
      ],
      "raw_data": [
        {
          "id": 1,
          "other_data": "example",
          "other_row": 45
        }
      ]
    },
    {
      "classification": "TLP:CLEAR",
      "count": 23,
      "link": "https://example.com/moreinfo",
      "annotations": [
        {
          "analytic": "Howler",
          "analytic_icon": null,
          "author": "John Smith",
          "quantity": 25,
          "version": "v0.0.1",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "context",
          "value": "Involved in Operation Cat",
          "confidence": 1.0,
          "severity": null,
          "priority": 1000.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": null,
          "icon": null,
          "ubiquitous": false
        },
        {
          "analytic": null,
          "analytic_icon": null,
          "author": null,
          "quantity": 25,
          "version": null,
          "timestamp": "2024-12-16T12:54:26.374945+00:00",
          "type": "frequency",
          "value": 42.0,
          "confidence": 0.0,
          "severity": null,
          "priority": 1000.0,
          "summary": "Example summary of the information in this Annotation",
          "details": "# Here's some annotation details\\n\\nIt's very interesting",
          "link": null,
          "icon": null,
          "ubiquitous": true
        }
      ],
      "raw_data": {
        "id": 1,
        "raw_field": "some_data"
      }
    }
  ],
  "maintainer": null,
  "datahub_link": "https://example.com/datahub",
  "documentation_link": null,
  "latency": 1470
}
```

</details>

A bulk enrichment will return the data in a dict of dicts of a list of `QueryResult`s, where the first key is the type
and the second key is the value:

```json
{
    "ip": {
        "127.0.0.1": [
            // See above for a full query result example
            {
                "type": "ip",
                "value": "127.0.0.1",
                "source": "example_plugin",
                ...
            }
        ]
    }
}
```

However, this formatting is handled by the central API and the clue plugin for the most part.

### Actions

Actions are operations a plugin can perform on either a single or several selectors. For example, an action could add
a selector to a database somewhere for tracking purposes, return a markdown summary of refined results for a set of
selectors, or any other arbitrary action. Clue only enforces the format of the response - there are no restrictions
on what an action can do.

In order to execute an action, the user must send an execution request to the central API:

```python
res = requests.post(
    f"{host}/api/v1/actions/execute/example/example_action",
    params={"max_timeout": 2.0},
    headers={"Authorization": f"Bearer {access_token}"},
    json={"selector": {"type": "ip", "value": "127.0.0.1"}, "other_choice": "b"},
)
```

You'll note the additional field provided. We will explain that next.

#### Additional Parameters

Clue plugins that expose an action can request additional parameters from the user in order to provide context of
the action request to the plugin. These parameters can be declared on the plugin side, and the clue UI library will
handle gathering the additional parameters.

Additional parameters are specified using Python Generics and class inheritance. Here is an example corresponding to
the above request:

```python
class Params(ExecuteRequest):
    other_value: Optional[str] = Field(description="Another field you should show", default="")
    choice: ChoiceEnum = Field(default=ChoiceEnum.a, description="Another choice for you")
    other_choice: ChoiceEnum = Field(description="Another choice for you with no default")

plugin = CluePlugin(
    ...,
    actions=[
        Action[Params](
            id="test_action",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Tester",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=True,
        )
    ]
)
```

Note that parameters can be marked as optional, as is shown above - only `other_choice` is fully required.

#### Action Results

In order to notify the user on the outcome of the action, actions are expected to return an `ActionResult` model. This
allows for a short description of the outcome, the output of the action (along with a format) as well as a status enum:

```python
failed_example = ActionResult(
    outcome="failure",
    summary="Action failed.",
    format="markdown",
    output=textwrap.dedent(
        f"""
        # Action Failed

        Retaining your data was unsuccessful for an unknown reason.

        ## Error Message:

        {str(e)}
        """.strip()
    ),
)

success_example = ActionResult(
    outcome="success",
    summary="Action Completed Successfully",
    format="json",
    output={
        "example": "result"
    },
    link=Url("http://example.com"),
)
```

### Fetchers

Fetchers are a way for plugins to return data to the client to be displayed based on a selector. This data can be
returned in any support format - currently:

- Markdown
- Json
- Images

Fetchers function similarly to actions, except no additional information can be provided. Below is an example of a
fetcher implementation:

```python
def run_fetcher(fetcher: FetcherDefinition, selector: Selector, access_token: str | None) -> FetcherResult:
    "Fetch a rendering of the given email"
    try:
        if not access_token:
            return FetcherResult(outcome="failure", format="error", error="Missing access token.")

            # work here

            return FetcherResult(
                outcome="success",
                format="image",
                data=ImageResult(
                    image=f"data:image/png;base64,{base64.b64encode(image_data).decode("utf-8")}",
                    alt=f"Rendering of an image to do with the given selector",
                ),
            )
    except Exception as e:
        logger.exception("Error in run_fetcher")
        return FetcherResult.error_result(repr(e))

plugin = CluePlugin(
    ...,
    run_fetcher=run_fetcher,
)
```

## Integrating Your Plugin into Clue - Responsibilities and Expectations

Since clue is a fairly complex project with a fair number of moving parts, it's important to outline the
responsibilities of the various stakeholders:

1. The Cyber Centre is the primary code-owner of the core clue code (i.e., all code inside the `clue/` folder).
2. Each respective team is responsible for maintenance and evolution of their specific plugin.
3. Each respective team is responsible for ensuring compatibility between their plugin and the central API.
   1. This includes adapting to breaking changes introduced during development of the core clue service.
   2. The Cyber Centre will try its best to limit these breaking changes as much as possible, and give plenty of notice.
4. The Cyber Centre is available for support with development (asking questions, fixing bugs in the central service, etc.).
5. The Cyber Centre is responsible for maintaining the stability of the service as a whole.

## Integrating Your Plugin into Clue - Hosting the Code

When building a plugin, the first step is to decide where the code will be stored you have two options for hosting the
code:

### Including the plugin in the repo

This approach allows you to develop the plugin, including it in the build process for clue, ensuring it is tightly
integrated with schema changes and feature updates top the base clue packages. This allows clue devs to test
your plugin for compatibility, and currently is the recommended approach.

**Note: Only python plugins are currently supported this way!**

The first step is to create a folder for your application in the
[plugins directory](https://github.com/CybercentreCanada/clue/tree/develop/plugins).

Once you have finished development of the core features, it is **strongly recommended** that you write at least very
basic unit tests for your plugin, with the gold standard being full integration testing against mock data. For
inspiration, check existing plugins and their test regimes.

For detailed information on initializing tests, see our main [README](../README.md) file.

#### External dependencies

If you import external packages differing from the plugin template, you must specify them both in the `requirements.txt`
file of your plugin, and in plugin dependencies group of the poetry project. The following command can do so:

```bash
# Replace the dependencies here with yours
poetry add -G plugins azure-core 'azure-storage-blob>=12.2.0' 'azure-storage-file-datalake>=12.2.0'
```

#### Creating a Pull Request

Once you are satisfied with your plugin, create a pull request for a member of the Cyber Centre to review the plugin for final
approval. There are some code quality checks performed on the codebase - if issues are flagged, work with a member of
the Cyber Centre to resolve them. Only readability and compatibility checks are the responsibility of the Cyber
Centre - we do not have any say on the functionality of your plugin, and cannot assist in development of your plugin
beyond questions about the base clue codebase

### Standalone repo

If you find our code standards too strict or insufficient, or want to develop the plugin in a language other than
python, or simply don't want to be included in the repository, you are welcome to host, test and build the plugin in
a standalone repository. We recommend running integration tests with a copy of the clue API to ensure
compatibility.

## Plugin Development Guide

### Installing poetry

```bash
pip install poetry
cd clue/api
poetry install --with dev,test --all-extras

# OPTIONAL: Instead pre-commit hooks (python formatting)
poetry run pre-commit install

# Now you can run the clue server!
poetry run server
```

#### Useful Commands

To activate a venv, use **`poetry shell`**.

To add a new dependency, use **`poetry add`**:

```bash
➜  api git:(poetry) poetry add pyjwt
Using version ^2.8.0 for pyjwt

Updating dependencies
Resolving dependencies... (0.5s)

Package operations: 1 install, 0 updates, 0 removals

  - Installing pyjwt (2.8.0)

Writing lock file
```

Then commit the new `pyproject.toml` and `poetry.lock`.

### Setup Clue Folders and Configuration

```bash
# Clue config.yml should be in this location, as well as classification.yml
# For a starter config, use the test config.yml and classification.
sudo mkdir -p /etc/clue/conf
# Log file directory, will write log files here if enabled
sudo mkdir -p /var/log/clue

sudo chown -R $USER /etc/clue
sudo chown $USER /var/log/clue
```
