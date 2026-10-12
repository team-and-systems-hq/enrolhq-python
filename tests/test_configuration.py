"""Unit tests for the school-configuration resources (offline, no API calls)."""

import base64
import datetime as dt

import pytest
import requests

from enrolhq import (
    EnrolHQClient,
    EnrolHQError,
    Replace,
    file_data_uri,
    image_data_uri,
    json_time,
    session,
)
from enrolhq.files import is_data_uri
from enrolhq.http import HttpClient
from enrolhq.resources.base import deep_merge

BASE = "https://x.enrolhq.net.au/api/v2/"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("ENROLHQ_BASE_URL", raising=False)
    monkeypatch.delenv("ENROLHQ_INSTANCE", raising=False)
    monkeypatch.delenv("ENROLHQ_DOMAIN", raising=False)
    monkeypatch.delenv("ENROLHQ_API_TOKEN", raising=False)
    monkeypatch.setattr("enrolhq.client._load_dotenv", lambda: {})


class _Resp:
    def __init__(self, payload):
        self._payload = payload
        self.content = b"" if payload is None else b"x"

    def json(self):
        return self._payload


class _Http:
    """Records requests and returns queued payloads (fresh copies each time)."""

    def __init__(self, *payloads):
        self._payloads = list(payloads)
        self.requests = []  # (method, url, body_or_params)

    def _next(self):
        import copy
        return _Resp(copy.deepcopy(self._payloads.pop(0)))

    def get(self, url, params=None, **kwargs):
        self.requests.append(("GET", url, params))
        return self._next()

    def post(self, url, json=None, params=None, **kwargs):
        self.requests.append(("POST", url, json))
        return self._next()

    def put(self, url, json=None, **kwargs):
        self.requests.append(("PUT", url, json))
        return self._next()

    def delete(self, url, **kwargs):
        self.requests.append(("DELETE", url, kwargs.get("params")))
        return self._next()

    def writes(self):
        return [r for r in self.requests if r[0] != "GET"]


# ── Client ──────────────────────────────────────────────────

def test_client_domain_param():
    c = EnrolHQClient(instance="christscollege", domain="enrolhq.net.au", api_token="t")
    assert c.base_url == "https://christscollege.enrolhq.net.au/api/v2/"


def test_client_domain_from_env(monkeypatch):
    monkeypatch.setenv("ENROLHQ_DOMAIN", "enrolhq.net.au")
    c = EnrolHQClient(instance="x", api_token="t")
    assert c.base_url == "https://x.enrolhq.net.au/api/v2/"


def test_client_default_domain_unchanged():
    assert EnrolHQClient(instance="x", api_token="t").base_url == "https://x.enrolhq.com.au/api/v2/"


def test_client_has_configuration_resources():
    c = EnrolHQClient(instance="x", api_token="t")
    for attr in ("school", "campuses", "look_and_feel", "event_settings",
                 "entry_grade_settings", "payment_settings"):
        assert hasattr(c, attr), attr


# ── Redirects on writes ─────────────────────────────────────

class _StubAuth:
    def get_headers(self):
        return {"Authorization": "Token a"}

    def authenticate(self):
        return "a"


class _StubSession:
    def __init__(self, status, location=""):
        self.status, self.location, self.kwargs = status, location, None

    def request(self, method, url, **kwargs):
        self.kwargs = kwargs
        resp = requests.Response()
        resp.status_code = self.status
        resp.headers["Location"] = self.location
        resp._content = b"{}"
        return resp


def test_write_redirect_raises_with_canonical_url():
    http = HttpClient(_StubAuth())
    http.session = _StubSession(301, "https://x.enrolhq.net.au/api/v2/school/")
    with pytest.raises(EnrolHQError, match="x.enrolhq.net.au"):
        http.put("https://x.enrolhq.com.au/api/v2/school/", json={})
    assert http.session.kwargs["allow_redirects"] is False


def test_get_still_follows_redirects():
    http = HttpClient(_StubAuth())
    http.session = _StubSession(200)
    http.get("https://x/api/v2/school/")
    assert "allow_redirects" not in http.session.kwargs


def test_token_refresh_redirect_raises_with_real_status(monkeypatch):
    from enrolhq import AuthenticationError
    from enrolhq.auth import TokenAuth

    calls = []

    def fake_post(url, **kwargs):
        calls.append(kwargs)
        resp = requests.Response()
        resp.status_code = 301
        resp.headers["Location"] = "https://x.enrolhq.net.au/api/v2/accounts/refresh/"
        return resp

    monkeypatch.setattr("enrolhq.auth.requests.post", fake_post)
    with pytest.raises(AuthenticationError, match="x.enrolhq.net.au") as exc_info:
        TokenAuth("https://x.enrolhq.com.au/api/v2/", "t").authenticate()
    assert exc_info.value.status_code == 301
    assert str(exc_info.value).startswith("HTTP 301: ")
    assert calls[0]["allow_redirects"] is False


def test_authentication_error_defaults_to_401():
    from enrolhq import AuthenticationError
    assert AuthenticationError(detail="nope").status_code == 401


# ── Files ───────────────────────────────────────────────────

def test_image_data_uri_sniffs_type(tmp_path):
    path = tmp_path / "logo.bin"
    path.write_bytes(PNG)
    assert image_data_uri(path).startswith("data:image/png;base64,")
    uri = image_data_uri(JPEG)
    assert uri.startswith("data:image/jpeg;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == JPEG


@pytest.mark.parametrize("data", [b"<svg xmlns='http://www.w3.org/2000/svg'/>", b"GIF89a....", b"\x00\x00\x01\x00ico"])
def test_image_data_uri_rejects_unsupported(data):
    with pytest.raises(ValueError, match="convert"):
        image_data_uri(data)


def test_file_data_uri_includes_filename(tmp_path):
    path = tmp_path / "policy.pdf"
    path.write_bytes(b"%PDF-1.4")
    assert file_data_uri(path).startswith("data:application/pdf;filename:policy.pdf;base64,")
    font = file_data_uri(b"wOF2", filename="brand.woff2")
    assert font.startswith("data:font/woff2;filename:brand.woff2;base64,")


def test_file_data_uri_validates_filename():
    with pytest.raises(ValueError):
        file_data_uri(b"x")
    with pytest.raises(ValueError):
        file_data_uri(b"x", filename="a;b.pdf")


def test_is_data_uri():
    assert is_data_uri("data:image/png;base64,AAAA")
    assert not is_data_uri("https://cdn/x.png")
    assert not is_data_uri(None)


# ── deep_merge / Replace ────────────────────────────────────

def test_deep_merge_merges_dicts_and_replaces_lists():
    base = {"a": {"x": 1, "y": 2}, "items": [1, 2], "keep": True}
    merged = deep_merge(base, {"a": {"y": 3}, "items": [9]})
    assert merged == {"a": {"x": 1, "y": 3}, "items": [9], "keep": True}
    assert base["a"]["y"] == 2  # input untouched


def test_replace_swaps_dict_wholesale():
    base = {"country": {"id": 36, "alpha_2_code": "AU"}}
    merged = deep_merge(base, {"country": Replace({"alpha_2_code": "NZ"})})
    assert merged["country"] == {"alpha_2_code": "NZ"}


# ── SchoolResource ──────────────────────────────────────────

def _school():
    return {
        "name": "",
        "school": {"tzname": "Australia/Sydney", "cors": [],
                   "country": {"id": 36, "alpha_2_code": "AU"}},
        "lead_references": [{"id": "r1"}],
    }


def test_school_update_fields_round_trips():
    from enrolhq.resources.school import SchoolResource
    http = _Http(_school(), {})
    SchoolResource(http, BASE).update_fields({"name": "Christ's College"})
    method, url, body = http.writes()[0]
    assert (method, url) == ("PUT", BASE + "school/")
    assert body["name"] == "Christ's College"
    assert body["lead_references"] == [{"id": "r1"}]  # untouched keys preserved
    assert body["school"]["tzname"] == "Australia/Sydney"


def test_school_set_region_replaces_country():
    from enrolhq.resources.school import SchoolResource
    http = _Http(_school(), {})
    SchoolResource(http, BASE).set_region(tzname="Pacific/Auckland", country="nz")
    body = http.writes()[0][2]
    assert body["school"]["tzname"] == "Pacific/Auckland"
    assert body["school"]["country"] == {"alpha_2_code": "NZ"}  # no stale id
    assert body["school"]["cors"] == []


def test_school_set_region_requires_an_argument():
    from enrolhq.resources.school import SchoolResource
    with pytest.raises(ValueError):
        SchoolResource(_Http(), BASE).set_region()


def test_school_create_commencement_date():
    from enrolhq.resources.school import SchoolResource
    http = _Http({"id": "c1"})
    SchoolResource(http, BASE).create_commencement_date(2027, "2027-02-02")
    assert http.writes()[0] == ("POST", BASE + "school/commencement_dates/",
                                {"year": 2027, "grade": None, "commencement_date": "2027-02-02"})


# ── CampusesResource ────────────────────────────────────────

def _campus():
    return {
        "id": "c1", "name": "Main Campus", "is_default": True, "telephone": "",
        "residential_address": {"street_address": "", "country": {"id": 36}},
        "cms_images": {"logo_dark": "https://cdn/logo.png", "favicon": None},
    }


def test_campus_update_fields_sends_only_changed_images():
    from enrolhq.resources.campuses import CampusesResource
    http = _Http(_campus(), {})
    CampusesResource(http, BASE).update_fields("c1", {"telephone": "+6433668705"})
    method, url, body = http.writes()[0]
    assert (method, url) == ("PUT", BASE + "school-campuses/c1/")
    assert body["telephone"] == "+6433668705"
    assert body["cms_images"] == {}  # GET URLs are never sent back


def test_campus_set_images_encodes_and_clears(tmp_path):
    from enrolhq.resources.campuses import CampusesResource
    path = tmp_path / "fav.png"
    path.write_bytes(PNG)
    http = _Http(_campus(), {})
    CampusesResource(http, BASE).set_images("c1", favicon=path, logo_light=None)
    images = http.writes()[0][2]["cms_images"]
    assert images["favicon"].startswith("data:image/png;base64,")
    assert images["logo_light"] is None
    assert set(images) == {"favicon", "logo_light"}


def test_campus_update_fields_replaces_country():
    from enrolhq.resources.campuses import CampusesResource
    http = _Http(_campus(), {})
    CampusesResource(http, BASE).update_fields(
        "c1", {"residential_address": {"state": "Canterbury",
                                       "country": {"alpha_2_code": "NZ"}}}
    )
    address = http.writes()[0][2]["residential_address"]
    assert address == {"street_address": "", "state": "Canterbury",
                       "country": {"alpha_2_code": "NZ"}}  # no stale id


def test_campus_set_images_requires_a_slot():
    from enrolhq.resources.campuses import CampusesResource
    http = _Http()
    with pytest.raises(ValueError):
        CampusesResource(http, BASE).set_images("c1")
    assert http.requests == []


def test_campus_set_images_rejects_unknown_slot():
    from enrolhq.resources.campuses import CampusesResource
    with pytest.raises(ValueError, match="logo_huge"):
        CampusesResource(_Http(), BASE).set_images("c1", logo_huge=PNG)


def test_campus_default_prefers_is_default():
    from enrolhq.resources.campuses import CampusesResource
    rows = [{"id": "a", "is_default": False}, {"id": "b", "is_default": True}]
    res = CampusesResource(_Http({"results": rows, "next": None}), BASE)
    assert res.default()["id"] == "b"


# ── LookAndFeelResource ─────────────────────────────────────

def _laf():
    return {
        "palette": {"primary_color": "#7ED321", "secondary_color": "#ac0031"},
        "form_header_themes": {c: "dark" for c in ("lead", "enq", "evt", "eoi", "enr", "cust")},
        "fonts": {"regular": "f1", "brand": None},
        "font_library": [{"id": "f1", "name": "DINOT Regular"}],
    }


def test_set_palette_keeps_themes_and_fonts():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    http = _Http(_laf(), {})
    LookAndFeelResource(http, BASE).set_palette(primary_color="#08080A")
    body = http.writes()[0][2]
    assert body["palette"] == {"primary_color": "#08080A", "secondary_color": "#ac0031"}
    assert body["fonts"] == {"regular": "f1", "brand": None}
    assert "font_library" not in body


def test_set_palette_validates_hex():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    with pytest.raises(ValueError):
        LookAndFeelResource(_Http(), BASE).set_palette(primary_color="black")


def test_set_form_header_themes_validates():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    with pytest.raises(ValueError):
        LookAndFeelResource(_Http(), BASE).set_form_header_themes(enq="grey")
    with pytest.raises(ValueError):
        LookAndFeelResource(_Http(), BASE).set_form_header_themes(zzz="dark")


def test_set_fonts_keeps_other_slots():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    http = _Http(_laf(), {})
    LookAndFeelResource(http, BASE).set_fonts(brand="f2")
    method, url, body = http.writes()[0]
    assert (method, url) == ("PUT", BASE + "cms-look-and-feel/")
    assert body["fonts"] == {"regular": "f1", "brand": "f2"}
    assert body["palette"] == _laf()["palette"]


def test_set_fonts_rejects_unknown_slot():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    with pytest.raises(ValueError, match="italic"):
        LookAndFeelResource(_Http(), BASE).set_fonts(italic="f1")


@pytest.mark.parametrize("method", ["set_palette", "set_form_header_themes", "set_fonts"])
def test_look_and_feel_setters_require_a_change(method):
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    http = _Http()
    with pytest.raises(ValueError):
        getattr(LookAndFeelResource(http, BASE), method)()
    assert http.requests == []


def test_upload_font_posts_both_files():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    http = _Http({"id": "new", "name": "Playfair Display"})
    font = LookAndFeelResource(http, BASE).upload_font("Playfair Display", b"wOFF", b"wOF2")
    method, url, body = http.writes()[0]
    assert (method, url, font["id"]) == ("POST", BASE + "cms-fonts/", "new")
    assert body["woff"].startswith("data:font/woff;filename:Playfair-Display.woff;base64,")
    assert body["woff2"].startswith("data:font/woff2;filename:Playfair-Display.woff2;base64,")


def test_find_or_upload_font_reuses_library_entry():
    from enrolhq.resources.look_and_feel import LookAndFeelResource
    http = _Http(_laf())
    font = LookAndFeelResource(http, BASE).find_or_upload_font("DINOT Regular", b"", b"")
    assert font["id"] == "f1"
    assert http.writes() == []


# ── CmsSettingsResource writes ──────────────────────────────

def test_cms_settings_update_fields_merges_nested():
    from enrolhq.resources.cms_settings import CmsSettingsResource
    current = {"enquiry": {"page_header": "Make an Enquiry", "page_sub_header": "x"},
               "school_level_label": "Grade"}
    http = _Http(current, {})
    CmsSettingsResource(http, BASE).update_fields(
        {"school_level_label": "Year", "enquiry": {"page_header": "Enquire"}}
    )
    body = http.writes()[0][2]
    assert body == {"enquiry": {"page_header": "Enquire", "page_sub_header": "x"},
                    "school_level_label": "Year"}


# ── EventSettingsResource ───────────────────────────────────

def _event_settings():
    return {
        "event_kind_options": [
            {"id": "k1", "label": "Junior", "slug": "junior", "is_enabled": True},
            {"id": "k2", "label": "Open Day", "slug": "open-day", "is_enabled": False},
        ],
        "event_autohide_duration": 12,
    }


def test_ensure_kinds_keeps_existing_and_creates_missing():
    from enrolhq.resources.event_settings import EventSettingsResource
    result = {"event_kind_options": [{"id": "k2"}, {"id": "k3"}, {"id": "k1"}]}
    http = _Http(_event_settings(), result)
    kinds = EventSettingsResource(http, BASE).ensure_kinds(["open day", "College Tour"])
    sent = http.writes()[0][2]["event_kind_options"]
    assert sent[0] == {"id": "k2", "label": "Open Day", "slug": "open-day", "is_enabled": True}
    assert sent[1] == {"label": "College Tour", "slug": "college-tour", "is_enabled": True}
    assert sent[2]["id"] == "k1"  # kept: remove_others defaults to False
    assert http.writes()[0][2]["event_autohide_duration"] == 12
    assert kinds == result["event_kind_options"]


def test_ensure_kinds_remove_others():
    from enrolhq.resources.event_settings import EventSettingsResource
    http = _Http(_event_settings(), {"event_kind_options": []})
    EventSettingsResource(http, BASE).ensure_kinds(["Open Day"], remove_others=True)
    sent = http.writes()[0][2]["event_kind_options"]
    assert [k["label"] for k in sent] == ["Open Day"]


@pytest.mark.parametrize("labels,match", [
    (["Open-Day!"], "open-day"),           # collides with existing "Open Day"
    (["Campus Tour", "Campus  Tour?"], "campus-tour"),  # collide with each other
    (["参观"], "slug"),                     # nothing to build a slug from
])
def test_ensure_kinds_rejects_bad_slugs(labels, match):
    from enrolhq.resources.event_settings import EventSettingsResource
    http = _Http(_event_settings())
    with pytest.raises(ValueError, match=match):
        EventSettingsResource(http, BASE).ensure_kinds(labels)
    assert http.writes() == []


def test_ensure_kinds_ignores_existing_duplicate_slugs():
    from enrolhq.resources.event_settings import EventSettingsResource
    settings = _event_settings()
    settings["event_kind_options"].append(
        {"id": "k3", "label": "Open-Day", "slug": "open-day", "is_enabled": True}
    )
    http = _Http(settings, {"event_kind_options": []})
    EventSettingsResource(http, BASE).ensure_kinds(["School Tour"])
    assert len(http.writes()) == 1


# ── EntryGradeSettingsResource ──────────────────────────────

def test_modify_grades_applies_fn_and_top_level():
    from enrolhq.resources.entry_grade_settings import EntryGradeSettingsResource
    current = {"first_grade_age": 6, "entry_grade_settings": [
        {"entry_grade": 8, "campus_entry_years_settings": [{"is_available": True}]},
        {"entry_grade": 13, "campus_entry_years_settings": [{"is_available": False}]},
    ]}
    http = _Http(current, {})

    def senior(row):
        for campus in row["campus_entry_years_settings"]:
            campus["is_available"] = row["entry_grade"] >= 9

    EntryGradeSettingsResource(http, BASE).modify_grades(senior, first_grade_age=5)
    method, url, body = http.writes()[0]
    assert (method, url) == ("PUT", BASE + "entry-grade-settings/")
    assert body["first_grade_age"] == 5
    assert [r["campus_entry_years_settings"][0]["is_available"]
            for r in body["entry_grade_settings"]] == [False, True]


# ── PaymentSettingsResource ─────────────────────────────────

def test_payment_settings_update_fields():
    from enrolhq.resources.payment_settings import PaymentSettingsResource
    current = {"currency": "AUD", "gst_percent": "10.0",
               "stripe_secret_key": {"masked": ""}, "attendance_types": [{"id": "a"}]}
    http = _Http(current, {})
    PaymentSettingsResource(http, BASE).update_fields({"currency": "NZD", "gst_percent": "15.0"})
    body = http.writes()[0][2]
    assert (body["currency"], body["gst_percent"]) == ("NZD", "15.0")
    assert body["attendance_types"] == [{"id": "a"}]


# ── Events ──────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    ("09:30", {"HH": "09", "mm": "30"}),
    ("9", {"HH": "09", "mm": "00"}),
    (dt.time(14, 5), {"HH": "14", "mm": "05"}),
    ({"HH": 9, "mm": 0}, {"HH": "09", "mm": "00"}),
    ({"HH": "10", "mm": "45"}, {"HH": "10", "mm": "45"}),
    ("09:30:00", {"HH": "09", "mm": "30"}),
    (str(dt.time(9, 30, 0, 500000)), {"HH": "09", "mm": "30"}),
    (None, None),
])
def test_json_time(value, expected):
    assert json_time(value) == expected


@pytest.mark.parametrize("value", ["25:00", "09:60", "9:30pm", "nine", "", {"HH": "x", "mm": "0"}, {"HH": 9}])
def test_json_time_rejects_invalid(value):
    with pytest.raises(ValueError, match="Invalid time"):
        json_time(value)


def test_session_builder():
    s = session("Tue tour", dt.date(2026, 10, 13), "10:00", "10:45",
                capacity=12, registrations_limit=3, session_id="s1")
    assert s == {
        "id": "s1", "name": "Tue tour", "date": "2026-10-13",
        "start_time": {"HH": "10", "mm": "00"}, "end_time": {"HH": "10", "mm": "45"},
        "capacity": 12, "registrations_limit": 3, "is_session_enabled": True,
    }


def test_event_create_fills_required_keys():
    from enrolhq.resources.events import EventsResource
    http = _Http({"id": "e1"})
    EventsResource(http, BASE).create({"name": "Open Day", "sessions": []})
    body = http.writes()[0][2]
    assert body["slug"] == "" and body["after_submit_settings"] is None


def test_event_create_keeps_explicit_values():
    from enrolhq.resources.events import EventsResource
    http = _Http({"id": "e1"})
    after = {"action": "REDIRECT_TO_URL", "redirect_url": "https://x"}
    EventsResource(http, BASE).create({"name": "x", "slug": "x", "after_submit_settings": after})
    body = http.writes()[0][2]
    assert body["slug"] == "x" and body["after_submit_settings"] == after


def test_event_update_copies_missing_keys_from_current():
    from enrolhq.resources.events import EventsResource
    after = {"action": "REDIRECT_TO_URL", "redirect_url": "https://x"}
    http = _Http({"id": "e1", "slug": "tour", "after_submit_settings": after}, {})
    EventsResource(http, BASE).update("e1", {"name": "Tour", "sessions": []})
    assert http.requests[0][:2] == ("GET", BASE + "staff-events/e1/")
    method, url, body = http.writes()[0]
    assert (method, url) == ("PUT", BASE + "staff-events/e1/")
    assert body["slug"] == "tour" and body["after_submit_settings"] == after


def test_event_update_sends_explicit_values_without_get():
    from enrolhq.resources.events import EventsResource
    http = _Http({})
    EventsResource(http, BASE).update(
        "e1", {"name": "Tour", "slug": "tour", "after_submit_settings": None}
    )
    assert [r[0] for r in http.requests] == ["PUT"]
    body = http.writes()[0][2]
    assert body["slug"] == "tour" and body["after_submit_settings"] is None


def test_event_preview_uses_existing_endpoint():
    from enrolhq.resources.events import EventsResource
    http = _Http([])
    EventsResource(http, BASE).preview()
    assert http.requests[0][1] == BASE + "staff-events-preview/"


def test_event_find_matches_exact_name():
    from enrolhq.resources.events import EventsResource
    rows = [{"id": "1", "name": "Open Day 2027 (late)"}, {"id": "2", "name": "Open Day 2027"}]
    http = _Http({"results": rows, "next": None})
    assert EventsResource(http, BASE).find("Open Day 2027")["id"] == "2"
    assert http.requests[0][2]["search"] == "Open Day 2027"


# ── Metafield writes ────────────────────────────────────────

def _metafields():
    return {"field_settings": {"parent": {"how_hear": {
        "label": "How Did You Hear About Us",
        "options": ["Website"], "disabled_options": ["Radio"],
        "enabled": {"enr": True, "enq": True}, "mandatory": {"enr": True, "enq": True},
    }}}}


def test_metafields_update_field_merges_current_settings():
    from enrolhq.resources.metafields import MetafieldsResource
    http = _Http(_metafields(), {})
    MetafieldsResource(http, BASE).update_field(
        "parent", "how_hear", {"options": ["Website", "Other"], "mandatory": {"enq": False}}
    )
    method, url, body = http.writes()[0]
    assert (method, url) == ("PUT", BASE + "metafields/")
    assert body["block"] == "parent" and body["field"] == "how_hear"
    assert body["options"] == ["Website", "Other"]
    assert body["mandatory"] == {"enr": True, "enq": False}
    assert body["label"] == "How Did You Hear About Us"
    assert "disabled_options" not in body


def test_metafields_update_field_unknown_raises():
    from enrolhq.resources.metafields import MetafieldsResource
    with pytest.raises(KeyError):
        MetafieldsResource(_Http(_metafields()), BASE).update_field("parent", "nope", {})


def test_metafields_delete_field_uses_query_params():
    from enrolhq.resources.metafields import MetafieldsResource
    http = _Http(None)
    MetafieldsResource(http, BASE).delete_field("questionnaire", "q1")
    assert http.writes()[0] == ("DELETE", BASE + "metafields/",
                                {"block": "questionnaire", "field": "q1"})


def test_metafields_create_field_posts_data():
    from enrolhq.resources.metafields import MetafieldsResource
    http = _Http({"field": "q1"})
    data = {"block": "questionnaire", "label": "Dietary needs", "type": "text"}
    MetafieldsResource(http, BASE).create_field(data)
    assert http.writes()[0] == ("POST", BASE + "metafields/", data)


def test_metafields_toggle_block():
    from enrolhq.resources.metafields import MetafieldsResource
    http = _Http(None)
    MetafieldsResource(http, BASE).toggle_block("medical", "enr", False)
    assert http.writes()[0] == ("POST", BASE + "metafields/toggle_block/",
                                {"block_name": "medical", "form_code": "enr",
                                 "is_enabled": False})


def test_metafields_mutate_ordering():
    from enrolhq.resources.metafields import MetafieldsResource
    http = _Http(None)
    MetafieldsResource(http, BASE).mutate_ordering("parent", ["how_hear", "email"])
    assert http.writes()[0] == ("POST", BASE + "metafields/mutate_ordering/",
                                {"block_name": "parent", "ordering": ["how_hear", "email"]})
