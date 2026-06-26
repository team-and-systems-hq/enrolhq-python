"""EnrolHQ API resource modules."""

from .activity_log import ActivityLogResource
from .analytics import AnalyticsResource
from .applications import ApplicationsResource
from .audit_log import AuditLogResource
from .cms_settings import CmsSettingsResource
from .documents import DocumentsResource
from .email_log import EmailLogResource
from .event_bookings import EventBookingsResource
from .events import EventsResource
from .metafields import MetafieldsResource
from .notes import NotesResource
from .payments import PaymentsResource
from .reference_data import ReferenceDataResource
from .staff import StaffResource

__all__ = [
    "ActivityLogResource",
    "AnalyticsResource",
    "ApplicationsResource",
    "AuditLogResource",
    "CmsSettingsResource",
    "DocumentsResource",
    "EmailLogResource",
    "EventBookingsResource",
    "EventsResource",
    "MetafieldsResource",
    "NotesResource",
    "PaymentsResource",
    "ReferenceDataResource",
    "StaffResource",
]
