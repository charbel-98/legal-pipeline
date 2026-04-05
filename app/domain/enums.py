from enum import StrEnum


class LegalBody(StrEnum):
    EMPLOYMENT_APPEALS_TRIBUNAL = "Employment Appeals Tribunal"
    EQUALITY_TRIBUNAL = "Equality Tribunal"
    LABOUR_COURT = "Labour Court"
    WORKPLACE_RELATIONS_COMMISSION = "Workplace Relations Commission"


class ContentType(StrEnum):
    HTML = "text/html"
    PDF = "application/pdf"
    DOC = "application/msword"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    DOCM = "application/vnd.ms-word.document.macroenabled.12"
    BINARY = "application/octet-stream"
