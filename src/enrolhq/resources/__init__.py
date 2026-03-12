"""EnrolHQ API resource modules."""

from .activity_log import ActivityLogResource
from .analytics import AnalyticsResource
from .applications import ApplicationsResource
from .documents import DocumentsResource
from .email_log import EmailLogResource
from .event_bookings import EventBookingsResource
from .events import EventsResource
from .notes import NotesResource
from .payments import PaymentsResource
from .reference_data import ReferenceDataResource
from .staff import StaffResource

__all__ = [
    "ActivityLogResource",
    "AnalyticsResource",
    "ApplicationsResource",
    "DocumentsResource",
    "EmailLogResource",
    "EventBookingsResource",
    "EventsResource",
    "NotesResource",
    "PaymentsResource",
    "ReferenceDataResource",
    "StaffResource",
]
