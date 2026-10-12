"""EnrolHQ API resource modules."""

from .activity_log import ActivityLogResource
from .analytics import AnalyticsResource
from .applications import ApplicationsResource
from .audit_log import AuditLogResource
from .campuses import CampusesResource
from .cms_settings import CmsSettingsResource
from .documents import DocumentsResource
from .email_log import EmailLogResource
from .entry_grade_settings import EntryGradeSettingsResource
from .event_bookings import EventBookingsResource
from .event_settings import EventSettingsResource
from .events import EventsResource
from .forms import FormsResource
from .leads import LeadsResource
from .look_and_feel import LookAndFeelResource
from .metafields import MetafieldsResource
from .notes import NotesResource
from .payment_settings import PaymentSettingsResource
from .payments import PaymentsResource
from .reference_data import ReferenceDataResource
from .school import SchoolResource
from .staff import StaffResource

__all__ = [
    "ActivityLogResource",
    "AnalyticsResource",
    "ApplicationsResource",
    "AuditLogResource",
    "CampusesResource",
    "CmsSettingsResource",
    "DocumentsResource",
    "EmailLogResource",
    "EntryGradeSettingsResource",
    "EventBookingsResource",
    "EventSettingsResource",
    "EventsResource",
    "FormsResource",
    "LeadsResource",
    "LookAndFeelResource",
    "MetafieldsResource",
    "NotesResource",
    "PaymentSettingsResource",
    "PaymentsResource",
    "ReferenceDataResource",
    "SchoolResource",
    "StaffResource",
]
