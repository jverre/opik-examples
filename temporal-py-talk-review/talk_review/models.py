from dataclasses import dataclass, field


@dataclass
class Submission:
    talk_id: str
    title: str
    speaker: str
    speaker_email: str
    conference_date: str
    abstract: str


@dataclass
class AbstractAnalysis:
    level: str  # beginner | intermediate | advanced
    concrete_claims: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class Availability:
    speaker: str
    date: str
    available: bool
    note: str


@dataclass
class Review:
    talk_id: str
    analysis: AbstractAnalysis
    availability: Availability
    recommendation: str  # accept | waitlist | decline
    review_text: str
