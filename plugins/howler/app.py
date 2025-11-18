"""Howler Plugin

Team: Canadian Centre for Cybersecurity

Status: Production

This plugin enriches selectors based on their presence in Howler. It also allows analysts to pivot on specified
selectors to search for information about them in the Howler UI.
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Optional, Union, cast

import geventhttpclient
from actions.model import SearchPivotRequest
from clue.common.exceptions import AuthenticationException, InvalidDataException
from clue.common.logging import get_logger
from clue.models.actions import Action, ActionResult, ExecuteRequest
from clue.models.network import Annotation, QueryEntry
from clue.plugin import ClueException, CluePlugin
from clue.plugin.utils import Params
from constants import CLASSIFICATION, HOWLER_URL
from flask import request
from pydantic_core import Url

logger = get_logger(__file__)

# Mapping of Clue type names to external systems "type" names
with open(Path(__file__).parent / "type_mapping.json", "r") as json_file:
    TYPE_MAPPING = json.load(json_file)


ACTIONS = [
    Action[SearchPivotRequest](
        id="search",
        name="Search in Howler",
        classification=CLASSIFICATION,
        format="pivot",
        summary="Search for the specified selector in Howler",
        supported_types={tname for tname in TYPE_MAPPING},
        accept_multiple=True,
        action_icon="material-symbols:sound-detection-dog-barking",
    )
]


plugin = CluePlugin(
    app_name=os.environ.get("APP_NAME", "howler-plugin"),
    classification=CLASSIFICATION,
    enable_apm=False,
    enable_cache=True,
    supported_types={tname for tname in TYPE_MAPPING},
    logger=logger,
    actions=ACTIONS,
)


@plugin.use
def validate_token():
    "Validate JWT"
    logger.info("Validating Token")

    token = request.headers.get("Authorization", None, type=str)
    if token:
        token = token.split()[1]

        # Default to howler-aks-u-dev
        hwl_audience = os.environ.get("HOWLER_AUDIENCE", "7fd79813-310c-456f-b90e-2fdbdf55471b")
        # keycloak sets the aud field to a list of audiences, so it might be a list
        token_audience: Union[list, str] = json.loads(base64.b64decode(token.split(".")[1] + "==").decode()).get("aud")

        if hwl_audience not in token_audience if isinstance(token_audience, list) else hwl_audience != token_audience:
            logger.error("Audience does not match: %s != %s", token_audience, hwl_audience)
            return None, "The token provided to authenticate with Howler does not match the expected audience."

    return token, None


def find_same_analytic(annotations: list[Annotation], analytic: str, type: str, value: str) -> Optional[Annotation]:
    "Find an annotation matching the given analytic"
    for annotation in annotations:
        if annotation.analytic == analytic and annotation.type == type and annotation.value == value:
            logger.info("Matching annotation found for %s (type %s, value %s)", analytic, type, value)
            return annotation

    return None


def update_annotation(annotation: Annotation, new_id: str):
    "Update an annotation matching with an aditional ID"
    logger.info("Annotation link %s being updated with ID %s", annotation.link, new_id)

    if not annotation.link:
        annotation.link = Url(f"{HOWLER_URL}/hits/{new_id}")
        annotation.quantity = 1

    if not annotation.link.path:
        return Url(f"{HOWLER_URL}/hits/{new_id}")

    query_ids: list[str] = []
    if annotation.link.path.startswith("/hits"):
        query_ids.append(annotation.link.path.split("/")[-1])
    elif annotation.link.path == "/search":
        query = next((pair for pair in annotation.link.query_params() if pair[0] == "query"), None)
        if query:
            query_ids.extend([_id for _id in query[1].replace("howler.id:(", "")[:-1].split(" ") if _id != "OR"])

    query_ids.append(new_id)
    unique_query_ids = set(query_ids)

    annotation.quantity = len(unique_query_ids)
    annotation.link = Url(
        f"{HOWLER_URL}/search?span=date.range.all&query=howler.id:({' OR '.join(sorted(unique_query_ids))})"
    )


@plugin.use
def enrich(type_name: str, value: str, params: Params, token: Optional[str]) -> QueryEntry:  # noqa: C901
    "Provide a list of enrichments"
    if type_name not in TYPE_MAPPING:
        raise InvalidDataException(
            message=f"Type name `{type_name}` is invalid. Valid types are: {', '.join(TYPE_MAPPING.keys())}"
        )

    logger.info(f"Enriching [{type_name}] {value} limit {params.limit} (annotate={params.annotate})")
    query = " OR ".join(f'{howler_type}:"{value}"' for howler_type in TYPE_MAPPING[type_name])

    if not token:
        raise AuthenticationException("Authentication Token is necessary to authenticate with Howler")

    try:
        response = cast(
            Any,
            geventhttpclient.Session(network_timeout=params.max_timeout).post(
                f"{HOWLER_URL}/api/v1/search/hit",
                headers={"Authorization": f"Bearer {token}"},
                json={"filters": [], "offset": 0, "query": query, "rows": params.limit},
            ),
        ).json()
    except Exception as e:
        logger.exception("Exception on howler connection:")
        raise ClueException(f"Something went wrong when connecting to howler: {str(e)}", cause=e)

    search_results = response["api_response"]

    annotations: list[Annotation] = []
    if params.annotate and search_results["total"] > 0:
        logger.info("Processing %s entries for value", search_results["total"])
        for result in search_results["items"]:
            analytic = result["howler"]["analytic"]
            assessment = result["howler"].get("assessment", None)
            escalation = result["howler"]["escalation"]
            timestamp = result["event"]["created"]
            threat = result["howler"]["outline"].get("threat", None)
            target = result["howler"]["outline"].get("target", None)
            howler_id = result["howler"]["id"]

            logger.debug(
                "Processing howler.id:'%s' - howler.outline.threat:'%s' - howler.outline.target:'%s' - value:'%s'",
                howler_id,
                threat,
                target,
                value,
            )
            annotation_value = f"Value seen in howler hit created by {analytic}"
            if (
                existing_annotation := find_same_analytic(annotations, analytic, "context", annotation_value)
            ) is not None:
                logger.info("Selector is threat in confirmed malicious event")
                update_annotation(existing_annotation, howler_id)
            else:
                annotations.append(
                    Annotation(
                        analytic=analytic,
                        analytic_icon="material-symbols:sound-detection-dog-barking",
                        version=None,
                        timestamp=timestamp,
                        type="context",
                        value=annotation_value,
                        confidence=1.0,
                        severity=0.0,
                        summary=annotation_value,
                        link=Url(f"{HOWLER_URL}/hits/{howler_id}"),
                    )
                )

            if threat == value:
                if escalation == "evidence":
                    logger.info("Selector is threat in confirmed malicious event")
                    short_desc = f"Value marked as threat in alert resolved as {assessment}."
                    if result["howler"].get("rationale", None):
                        long_desc = short_desc + f"\n\nRationale: {result['howler']['rationale']}"
                    else:
                        long_desc = None

                    if (
                        existing_annotation := find_same_analytic(annotations, analytic, "assessment", assessment)
                    ) is not None:
                        update_annotation(existing_annotation, howler_id)
                    else:
                        annotations.append(
                            Annotation(
                                analytic=analytic,
                                analytic_icon="material-symbols:sound-detection-dog-barking",
                                version=None,
                                timestamp=timestamp,
                                type="assessment",
                                value=assessment,
                                confidence=1.0,
                                severity=1.0,
                                summary=short_desc,
                                details=long_desc,
                                link=Url(f"{HOWLER_URL}/hits/{howler_id}"),
                            )
                        )
                elif escalation == "miss":
                    logger.info("Selector is threat in confirmed miss event, setting benign opinion")
                    if (
                        existing_annotation := find_same_analytic(annotations, analytic, "opinion", "benign")
                    ) is not None:
                        update_annotation(existing_annotation, howler_id)
                    else:
                        annotations.append(
                            Annotation(
                                analytic=analytic,
                                analytic_icon="material-symbols:sound-detection-dog-barking",
                                version=None,
                                timestamp=timestamp,
                                type="opinion",
                                value="benign",
                                confidence=0.5,
                                severity=0.1,
                                summary="Value marked as threat in missed hit in Howler.",
                                link=Url(f"{HOWLER_URL}/hits/{howler_id}"),
                            )
                        )
                else:
                    logger.info("Selector is threat in untriaged event, setting suspicious opinion")
                    if (
                        existing_annotation := find_same_analytic(annotations, analytic, "opinion", "suspicious")
                    ) is not None:
                        update_annotation(existing_annotation, howler_id)
                    else:
                        annotations.append(
                            Annotation(
                                analytic=analytic,
                                analytic_icon="material-symbols:sound-detection-dog-barking",
                                version=None,
                                timestamp=timestamp,
                                type="opinion",
                                value="suspicious",
                                confidence=0.5 if escalation == "alert" else 0.1,
                                severity=0.4 if escalation == "alert" else 0.2,
                                summary=f"Value marked as threat in {result['howler']['escalation']} in Howler.",
                                link=Url(f"{HOWLER_URL}/hits/{howler_id}"),
                            )
                        )
            else:
                logger.debug("No match on threat: %s != %s", threat, value)

            if target == value:
                logger.info("Value is a target in Howler, howler.id:%s", howler_id)
                if (existing_annotation := find_same_analytic(annotations, analytic, "opinion", "benign")) is not None:
                    update_annotation(existing_annotation, howler_id)
                else:
                    annotations.append(
                        Annotation(
                            analytic=analytic,
                            analytic_icon="material-symbols:sound-detection-dog-barking",
                            version=None,
                            timestamp=timestamp,
                            type="opinion",
                            value="benign",
                            confidence=0.1,
                            severity=0.1,
                            summary="Value marked as target of a threat actor in Howler",
                            link=Url(f"{HOWLER_URL}/hits/{howler_id}"),
                        )
                    )
            else:
                logger.debug("No match on target: %s != %s", threat, value)

    logger.info("Returning %s annotations", len(annotations))

    return QueryEntry(
        annotations=annotations,
        classification=CLASSIFICATION,
        count=search_results["total"],
        raw_data=search_results if params.raw else None,
        link=Url(HOWLER_URL),
    )


@plugin.use
def run_action(action: Action, action_request: ExecuteRequest, access_token: str | None):
    "Execute a howler action"
    if action.id == "search":
        pivot_request = cast(SearchPivotRequest, action_request)

        query = ""
        for selector in pivot_request.selectors:
            sub_query = " OR ".join(f'{howler_type}:"{selector.value}"' for howler_type in TYPE_MAPPING[selector.type])
            query += f"({sub_query}) OR "

        if len(query) > 0:
            # Remove the trailing OR
            query = query[:-4]

        if not (pivot_request.start_date and pivot_request.end_date):
            time_span = ""
        else:
            time_span = (
                f"&span=date.range.custom&start_date={pivot_request.start_date}&end_date={pivot_request.end_date}"
            )

        output = Url(f"{HOWLER_URL}/search?query={query}{time_span}")

        return ActionResult(
            outcome="success",
            summary=f"Created query to pivot to Howler for {len(pivot_request.selectors)} selectors.",
            format="pivot",
            output=output,
            link=output,
        )

    return ActionResult(outcome="failure", summary="Invalid action ID.")
