"""EnrolHQ API resource modules."""

from .activity_log import ActivityLogResource
from .admission_processes import AdmissionProcessesResource
from .analytics import AnalyticsResource
from .application_status_settings import ApplicationStatusSettingsResource
from .applications import ApplicationsResource
from .audit_log import AuditLogResource
from .automations import AutomationsResource
from .campuses import CampusesResource
from .cms_settings import CmsSettingsResource
from .documents import DocumentsResource
from .email_log import EmailLogResource
from .email_templates import EmailTemplatesResource
from .entry_grade_settings import EntryGradeSettingsResource
from .event_bookings import EventBookingsResource
from .event_settings import EventSettingsResource
from .events import EventsResource
from .forms import FormsResource
from .interviews import InterviewsResource
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
    "AdmissionProcessesResource",
    "AnalyticsResource",
    "ApplicationStatusSettingsResource",
    "ApplicationsResource",
    "AuditLogResource",
    "AutomationsResource",
    "CampusesResource",
    "CmsSettingsResource",
    "DocumentsResource",
    "EmailLogResource",
    "EmailTemplatesResource",
    "EntryGradeSettingsResource",
    "EventBookingsResource",
    "EventSettingsResource",
    "EventsResource",
    "FormsResource",
    "InterviewsResource",
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
