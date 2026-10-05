"""Ezermalas pieteikumu sistēma · iesniegumu API (mācību prototips)."""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import omd_client, storage
from app.errors import SubmissionNotFound, register_error_handlers
from app.models import (
    TOPIC_NAMES,
    Error,
    Health,
    ReplyChannel,
    Submission,
    SubmissionCreate,
    SubmissionCreated,
    SubmissionStatus,
    TopicItem,
)

VERSION = "0.1.0"
REPLY_DAYS = 30  # Vienkāršots termiņš: 30 kalendāra dienas
UI_DIR = Path(__file__).resolve().parent.parent / "ui"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ezermala.submissions")

app = FastAPI(title="Ezermalas pieteikumu sistēma · iesniegumu API", version=VERSION)
register_error_handlers(app)
storage.reset()


def get_omd() -> Callable[[str], str | None]:
    return omd_client.mailbox_status


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/ui/")


@app.get("/health", response_model=Health, tags=["Sistēma"])
def get_health() -> Health:
    return Health(status="ok", version=VERSION)


@app.get("/topics", response_model=list[TopicItem], tags=["Klasifikatori"])
def list_topics() -> list[TopicItem]:
    return [TopicItem(code=code, name=name) for code, name in TOPIC_NAMES.items()]


@app.post(
    "/submissions",
    status_code=201,
    response_model=SubmissionCreated,
    responses={400: {"model": Error}},
    tags=["Iesniegumi"],
)
def create_submission(
    data: SubmissionCreate,
    omd: Annotated[Callable[[str], str | None], Depends(get_omd)],
) -> SubmissionCreated:
    received_at = datetime.now(timezone.utc).replace(microsecond=0)

    if omd(data.personalCode) == "ACTIVE":
        reply_channel = ReplyChannel.E_ADDRESS
    else:
        reply_channel = ReplyChannel(data.preferredChannel.value)

    record = storage.add(
        {
            **data.model_dump(mode="json"),
            "status": SubmissionStatus.RECEIVED.value,
            "receivedAt": received_at.isoformat(),
            "dueDate": (received_at.date() + timedelta(days=REPLY_DAYS)).isoformat(),
            "replyChannel": reply_channel.value,
            "reasonCode": None,
        }
    )
    # Žurnālā tikai ID: personas kods un teksts ir personas dati.
    logger.info("Jauns iesniegums: %s", record["id"])
    return SubmissionCreated(**record)


@app.get(
    "/submissions/{submission_id}",
    response_model=Submission,
    responses={404: {"model": Error}},
    tags=["Iesniegumi"],
)
def get_submission(submission_id: str) -> Submission:
    record = storage.get(submission_id)
    if record is None:
        raise SubmissionNotFound()
    return Submission(**record)


app.mount("/ui", StaticFiles(directory=UI_DIR, html=True), name="ui")
