"""The typed results the agent can return."""

from typing import Optional

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    """One calendar event found in an email."""

    title: str = Field(description="Short event title")
    date: str = Field(description="Event date as YYYY-MM-DD")
    start_time: Optional[str] = Field(None, description="Start time as 24-hour HH:MM, if stated")
    end_time: Optional[str] = Field(None, description="End time as 24-hour HH:MM, if stated")
    all_day: bool = Field(False, description="True only if the email says the event lasts all day")
    timezone: Optional[str] = Field(None, description="Time zone exactly as the email names it")
    location: Optional[str] = Field(None, description="Physical place, if one is given")
    meeting_link: Optional[str] = Field(None, description="Video meeting URL, if one is given")
    attendees: list[str] = Field(
        default_factory=list, description="People the email says will attend"
    )


class NoEvent(BaseModel):
    """The email does not describe a concrete event with a date."""

    reason: str = Field(description="One sentence on why there is no schedulable event")
