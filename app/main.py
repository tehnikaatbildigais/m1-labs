"""Ezermalas pieteikumu sistēma · iesniegumu API (mācību prototips)."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import omd_client, storage
from app.errors import SubmissionNotFound, register_error_handlers
from app.models import (
    STATUS_NAMES,
    TOPIC_NAMES,
    Error,
    Health,
    PreferredChannel,
    ReasonCode,
    ReplyChannel,
    StatusLookup,
    Submission,
    SubmissionCreate,
    SubmissionCreated,
    SubmissionStatus,
    SubmissionStatusView,
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


def get_omd() -> omd_client.MailboxLookup:
    return omd_client.mailbox_status


def check_reply_channel(
    omd: omd_client.MailboxLookup, personal_code: str, preferred: PreferredChannel
) -> tuple[ReplyChannel, ReasonCode | None, str | None]:
    """CR-2: nosaka atbildes kanālu. Atgriež kanālu, reasonCode un iemeslu žurnālam."""
    try:
        status = omd(personal_code)
    except omd_client.OmdUnavailable as exc:
        return _pending(exc.reason)
    except Exception:
        # Iesniedzējs nekad nesaņem 500 OMD dēļ. Izņēmuma tekstu nežurnalējam.
        return _pending("CLIENT_ERROR")

    if status == omd_client.MailboxStatus.ACTIVE:
        return ReplyChannel.E_ADDRESS, None, None
    if status not in (
        omd_client.MailboxStatus.NOT_ACTIVATED,
        omd_client.MailboxStatus.NO_RECORD,
    ):
        return _pending("UNDOCUMENTED_STATUS")
    # 404 (reģistrā nav ieraksta) nozīmē to pašu, ko NOT_ACTIVATED.
    log_reason = "NO_RECORD" if status == omd_client.MailboxStatus.NO_RECORD else None
    if preferred == PreferredChannel.E_ADDRESS:
        return ReplyChannel.EMAIL, ReasonCode.E_ADDRESS_NOT_ACTIVE, log_reason
    return ReplyChannel(preferred.value), None, log_reason


def _pending(reason: str) -> tuple[ReplyChannel, ReasonCode, str]:
    return ReplyChannel.PENDING_CHANNEL_CHECK, ReasonCode.REGISTER_UNAVAILABLE, reason


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
    omd: Annotated[omd_client.MailboxLookup, Depends(get_omd)],
) -> SubmissionCreated:
    received_at = datetime.now(timezone.utc).replace(microsecond=0)
    reply_channel, reason_code, log_reason = check_reply_channel(
        omd, data.personalCode, data.preferredChannel
    )

    record = storage.add(
        {
            **data.model_dump(mode="json"),
            "status": SubmissionStatus.RECEIVED.value,
            "receivedAt": received_at.isoformat(),
            "dueDate": (received_at.date() + timedelta(days=REPLY_DAYS)).isoformat(),
            "replyChannel": reply_channel.value,
            "reasonCode": reason_code.value if reason_code else None,
        }
    )
    # Žurnālā tikai ID un iemesls: nekad personas kods vai iesnieguma teksts.
    logger.info("Jauns iesniegums: %s", record["id"])
    if log_reason:
        logger.warning(
            "OMD pārbaude neveiksmīga: iesniegums %s, iemesls %s",
            record["id"],
            log_reason,
        )
    return SubmissionCreated(**record)


@app.post(
    "/submissions/status-lookup",
    response_model=SubmissionStatusView,
    responses={400: {"model": Error}, 404: {"model": Error}},
    tags=["Iesniegumi"],
)
def lookup_submission_status(data: StatusLookup) -> SubmissionStatusView:
    record = storage.get(data.id)
    # Neeksistējošs ID un nepareizs e-pasts dod vienu un to pašu atbildi,
    # lai pēc atbildes nevarētu uzzināt, kuri iesniegumi eksistē.
    if record is None or record["email"].casefold() != data.email.casefold():
        raise SubmissionNotFound()
    status = SubmissionStatus(record["status"])
    return SubmissionStatusView(
        id=record["id"],
        status=status,
        statusName=STATUS_NAMES[status],
        dueDate=record["dueDate"],
    )


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
