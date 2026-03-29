from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    body: str | None = None
    case_number: str | None = None
    decision_number: str | None = None
    legislation: str | None = None
    topic: str | None = None
    keyword: str | None = None

    def active_filters(self) -> dict[str, str]:
        return {
            key: value
            for key, value in {
                "body": self.body,
                "case_number": self.case_number,
                "decision_number": self.decision_number,
                "legislation": self.legislation,
                "topic": self.topic,
                "keyword": self.keyword,
            }.items()
            if value
        }
