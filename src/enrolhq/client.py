"""Main EnrolHQ client."""

import os
from typing import Optional

from .auth import TokenAuth
from .http import DEFAULT_TIMEOUT, HttpClient
from .resources import (
    ActivityLogResource,
    AnalyticsResource,
    ApplicationsResource,
    AuditLogResource,
    CampusesResource,
    CmsSettingsResource,
    DocumentsResource,
    EmailLogResource,
    EntryGradeSettingsResource,
    EventBookingsResource,
    EventSettingsResource,
    EventsResource,
    FormsResource,
    LeadsResource,
    LookAndFeelResource,
    MetafieldsResource,
    NotesResource,
    PaymentSettingsResource,
    PaymentsResource,
    ReferenceDataResource,
    SchoolResource,
    StaffResource,
)

#: Default domain used to build the base URL from ``instance``. Schools on
#: another domain (e.g. ``enrolhq.net.au``) must pass ``domain=`` or set
#: ``ENROLHQ_DOMAIN`` — EnrolHQ redirects non-canonical hosts, which breaks
#: authenticated writes.
DEFAULT_DOMAIN = "enrolhq.com.au"


def _load_dotenv() -> dict:
    """Parse .env file from CWD and return a dict of key-value pairs.

    Does NOT mutate os.environ.
    """
    env_path = os.path.join(os.getcwd(), ".env")
    result = {}
    if not os.path.isfile(env_path):
        return result
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                result[key] = value
    return result


class EnrolHQClient:
    """Client for the EnrolHQ API.

    Usage::

        # Explicit parameters
        client = EnrolHQClient(instance="demo", api_token="your_token")

        # Or from a .env file (ENROLHQ_BASE_URL / ENROLHQ_INSTANCE + ENROLHQ_API_TOKEN)
        client = EnrolHQClient()

        # Schools hosted on enrolhq.net.au
        client = EnrolHQClient(instance="myschool", domain="enrolhq.net.au", api_token="...")

        # List applications
        for app in client.applications.list(entry_year=2026):
            print(app["first_name"])
    """

    def __init__(
        self,
        *,
        api_token: Optional[str] = None,
        instance: Optional[str] = None,
        base_url: Optional[str] = None,
        domain: Optional[str] = None,
        timeout: object = DEFAULT_TIMEOUT,
    ) -> None:
        dotenv = _load_dotenv()

        def _resolve(explicit, env_key):
            if explicit is not None:
                return explicit
            return os.environ.get(env_key) or dotenv.get(env_key)

        if api_token is None:
            api_token = _resolve(None, "ENROLHQ_API_TOKEN")
        if base_url is None and instance is None:
            base_url = _resolve(None, "ENROLHQ_BASE_URL")
            instance = _resolve(None, "ENROLHQ_INSTANCE")
        if domain is None:
            domain = _resolve(None, "ENROLHQ_DOMAIN") or DEFAULT_DOMAIN

        if not api_token:
            raise ValueError(
                "api_token is required (pass it directly or set ENROLHQ_API_TOKEN)"
            )

        if base_url:
            self.base_url = base_url.rstrip("/") + "/"
        elif instance:
            self.base_url = f"https://{instance}.{domain.strip('.')}/api/v2/"
        else:
            raise ValueError(
                "Provide instance, base_url, or set ENROLHQ_BASE_URL / ENROLHQ_INSTANCE"
            )

        auth = TokenAuth(self.base_url, api_token, timeout=timeout)
        self._http = HttpClient(auth, timeout=timeout)

        self.applications = ApplicationsResource(self._http, self.base_url)
        self.leads = LeadsResource(self._http, self.base_url)
        self.forms = FormsResource(self._http, self.base_url)
        self.documents = DocumentsResource(self._http, self.base_url)
        self.notes = NotesResource(self._http, self.base_url)
        self.activity_log = ActivityLogResource(self._http, self.base_url)
        self.audit_log = AuditLogResource(self._http, self.base_url)
        self.email_log = EmailLogResource(self._http, self.base_url)
        self.events = EventsResource(self._http, self.base_url)
        self.event_bookings = EventBookingsResource(self._http, self.base_url)
        self.payments = PaymentsResource(self._http, self.base_url)
        self.staff = StaffResource(self._http, self.base_url)
        self.analytics = AnalyticsResource(self._http, self.base_url)
        self.reference_data = ReferenceDataResource(self._http, self.base_url)
        self.cms_settings = CmsSettingsResource(self._http, self.base_url)
        self.metafields = MetafieldsResource(self._http, self.base_url)
        # School configuration
        self.school = SchoolResource(self._http, self.base_url)
        self.campuses = CampusesResource(self._http, self.base_url)
        self.look_and_feel = LookAndFeelResource(self._http, self.base_url)
        self.event_settings = EventSettingsResource(self._http, self.base_url)
        self.entry_grade_settings = EntryGradeSettingsResource(
            self._http, self.base_url
        )
        self.payment_settings = PaymentSettingsResource(self._http, self.base_url)

    def __repr__(self) -> str:
        return f"EnrolHQClient(base_url={self.base_url!r})"
