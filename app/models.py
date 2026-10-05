"""Datu modeļi pēc API līguma (API contract) docs/openapi.yaml."""

import re
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, field_validator
from pydantic_core import PydanticCustomError

from app import personal_code


class PreferredChannel(str, Enum):
    EMAIL = "EMAIL"
    POST = "POST"
    E_ADDRESS = "E_ADDRESS"


class ReplyChannel(str, Enum):
    EMAIL = "EMAIL"
    POST = "POST"
    E_ADDRESS = "E_ADDRESS"
    PENDING_CHANNEL_CHECK = "PENDING_CHANNEL_CHECK"


class ReasonCode(str, Enum):
    E_ADDRESS_NOT_ACTIVE = "E_ADDRESS_NOT_ACTIVE"
    REGISTER_UNAVAILABLE = "REGISTER_UNAVAILABLE"


class Topic(str, Enum):
    ROADS = "ROADS"
    WASTE = "WASTE"
    PLANNING = "PLANNING"
    PARKS = "PARKS"
    OTHER = "OTHER"


# Secība kā GET /topics atbildē: OTHER vienmēr beigās.
TOPIC_NAMES = {
    Topic.ROADS: "Ceļi un ielas",
    Topic.WASTE: "Atkritumi",
    Topic.PLANNING: "Teritorijas plānošana",
    Topic.PARKS: "Parki un skvēri",
    Topic.OTHER: "Cits",
}


class SubmissionStatus(str, Enum):
    RECEIVED = "RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    FORWARDED = "FORWARDED"
    ANSWERED = "ANSWERED"
    WITHDRAWN = "WITHDRAWN"


# Statusa nosaukumi iedzīvotājam (statusa lapa).
STATUS_NAMES = {
    SubmissionStatus.RECEIVED: "Saņemts",
    SubmissionStatus.IN_PROGRESS: "Izskatīšanā",
    SubmissionStatus.FORWARDED: "Pārsūtīts",
    SubmissionStatus.ANSWERED: "Atbildēts",
    SubmissionStatus.WITHDRAWN: "Atsaukts",
}

SUBMISSION_ID_PATTERN = re.compile(r"^IES-[0-9]{4}-[0-9]{6}$")


class TopicItem(BaseModel):
    code: Topic
    name: str


class SubmissionFields(BaseModel):
    personalCode: str
    fullName: str
    email: str  # TODO: pārbaudīt e-pasta formātu
    preferredChannel: PreferredChannel
    topic: Topic
    subject: str
    body: str


class SubmissionCreate(SubmissionFields):
    @field_validator("personalCode")
    @classmethod
    def check_personal_code(cls, value: str) -> str:
        # CR-1: tukšs kods ir REQUIRED, viss pārējais nederīgais ir INVALID_FORMAT.
        if value == "":
            raise PydanticCustomError("missing", "Field required")
        if not personal_code.is_valid(value):
            raise PydanticCustomError("personal_code", "Invalid personal code")
        return value


class SubmissionCreated(BaseModel):
    id: str
    status: SubmissionStatus
    receivedAt: datetime
    dueDate: date
    replyChannel: ReplyChannel
    reasonCode: ReasonCode | None = None


class Submission(SubmissionCreated, SubmissionFields):
    # Bez ievades pārbaudes: agrāk saglabātie ieraksti var neatbilst CR-1 noteikumiem.
    pass


class StatusLookup(BaseModel):
    id: str
    email: str

    @field_validator("id", "email")
    @classmethod
    def check_not_empty(cls, value: str) -> str:
        value = value.strip()
        if value == "":
            raise PydanticCustomError("missing", "Field required")
        return value

    @field_validator("id")
    @classmethod
    def check_id_format(cls, value: str) -> str:
        if not SUBMISSION_ID_PATTERN.match(value):
            raise PydanticCustomError("submission_id", "Invalid submission id")
        return value


class SubmissionStatusView(BaseModel):
    """Iedzīvotājam: tikai statuss un termiņš, bez personas datiem."""

    id: str
    status: SubmissionStatus
    statusName: str
    dueDate: date


class Health(BaseModel):
    status: str
    version: str


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class Error(BaseModel):
    error: ErrorBody
