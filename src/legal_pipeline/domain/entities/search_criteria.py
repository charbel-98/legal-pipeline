from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class SearchCriteria:
    body: Optional[str] = None
    case_number: Optional[str] = None
    decision_number: Optional[str] = None
    legislation: Optional[str] = None
    topic: Optional[str] = None
    keyword: Optional[str] = None

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

