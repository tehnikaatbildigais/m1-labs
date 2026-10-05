"""Datu modeļi pēc API līguma (API contract) docs/openapi.yaml."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class PreferredChannel(str, Enum):
    EMAIL = "EMAIL"
    POST = "POST"
    E_ADDRESS = "E_ADDRESS"


class ReplyChannel(str, Enum):
    EMAIL = "EMAIL"
    POST = "POST"
    E_ADDRESS = "E_ADDRESS"


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


class TopicItem(BaseModel):
    code: Topic
    name: str


class SubmissionCreate(BaseModel):
    personalCode: str
    fullName: str
    email: str  # TODO: pārbaudīt e-pasta formātu
    preferredChannel: PreferredChannel
    topic: Topic
    subject: str
    body: str


class SubmissionCreated(BaseModel):
    id: str
    status: SubmissionStatus
    receivedAt: datetime
    dueDate: date
    replyChannel: ReplyChannel
    reasonCode: str | None = None


class Submission(SubmissionCreated, SubmissionCreate):
    pass


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
