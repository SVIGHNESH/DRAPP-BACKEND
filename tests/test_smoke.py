"""Smoke tests — no DB required, just validates app import and schema logic."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.booking import BookingCreate, BookingStatusUpdate, AssignedNurseIn
from app.schemas.user import (
    RegisterRequest,
    LoginRequest,
    PasswordResetConfirm,
    FamilyMemberCreate,
    FamilyMemberUpdate,
    UserUpdate,
)
from app.schemas.address import AddressCreate, AddressUpdate


# ── Booking: address constraint ───────────────────────────────────────────────

BASE_BOOKING = dict(service_id=1, slot_start=datetime(2026, 6, 15, 8), slot_end=datetime(2026, 6, 15, 20))


def test_booking_requires_exactly_one_address():
    # both provided → error
    with pytest.raises(ValidationError):
        BookingCreate(**BASE_BOOKING, address_id=1, custom_address="123 Main St")

    # neither provided → error
    with pytest.raises(ValidationError):
        BookingCreate(**BASE_BOOKING)

    # only address_id → ok
    b = BookingCreate(**BASE_BOOKING, address_id=1)
    assert b.address_id == 1
    assert b.custom_address is None

    # only custom_address → ok
    b = BookingCreate(**BASE_BOOKING, custom_address="123 Main St, Delhi")
    assert b.custom_address == "123 Main St, Delhi"
    assert b.address_id is None


def test_booking_custom_address_whitespace_is_rejected():
    with pytest.raises(ValidationError):
        BookingCreate(**BASE_BOOKING, custom_address="   ")


def test_booking_optional_fields_default_to_none():
    b = BookingCreate(**BASE_BOOKING, address_id=5)
    assert b.member_id is None
    assert b.notes is None


def test_booking_status_update_accepts_valid_status():
    for s in ("requested", "confirmed", "in_progress", "completed", "cancelled"):
        u = BookingStatusUpdate(status=s)
        assert u.status == s


def test_assigned_nurse_contact_is_optional():
    n = AssignedNurseIn(nurse_name="Priya Mehta")
    assert n.nurse_contact is None

    n2 = AssignedNurseIn(nurse_name="Priya Mehta", nurse_contact="+91-9876543210")
    assert n2.nurse_contact == "+91-9876543210"


# ── Auth: register / login schemas ───────────────────────────────────────────

def test_register_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Test", email="a@b.com", password="short")


def test_register_rejects_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(name="Test", email="not-an-email", password="validpassword")


def test_register_accepts_valid_input():
    r = RegisterRequest(name="Vighnesh", email="v@example.com", password="securepass")
    assert r.name == "Vighnesh"
    assert r.email == "v@example.com"


def test_login_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(email="bad-email", password="anything")


def test_password_reset_confirm_rejects_short_password():
    with pytest.raises(ValidationError):
        PasswordResetConfirm(token="sometoken", new_password="abc")


def test_password_reset_confirm_accepts_valid():
    p = PasswordResetConfirm(token="tok", new_password="newpassword")
    assert p.token == "tok"


# ── Family members ────────────────────────────────────────────────────────────

def test_family_member_create_required_name():
    with pytest.raises(ValidationError):
        FamilyMemberCreate()


def test_family_member_create_optional_fields():
    m = FamilyMemberCreate(name="Ramesh")
    assert m.age is None
    assert m.relation is None
    assert m.medical_notes is None


def test_family_member_create_full():
    m = FamilyMemberCreate(name="Ramesh", age=65, relation="Father", medical_notes="Diabetic")
    assert m.age == 65
    assert m.relation == "Father"


def test_family_member_update_all_optional():
    u = FamilyMemberUpdate()
    assert u.name is None
    assert u.age is None


def test_user_update_requires_name():
    with pytest.raises(ValidationError):
        UserUpdate()

    u = UserUpdate(name="Vighnesh")
    assert u.name == "Vighnesh"


# ── Addresses ─────────────────────────────────────────────────────────────────

def test_address_create_requires_mandatory_fields():
    with pytest.raises(ValidationError):
        AddressCreate(line1="42 MG Road", city="Bangalore", state="Karnataka")  # missing pincode

    with pytest.raises(ValidationError):
        AddressCreate(city="Bangalore", state="Karnataka", pincode="560001")  # missing line1


def test_address_create_defaults():
    a = AddressCreate(line1="42 MG Road", city="Bangalore", state="Karnataka", pincode="560001")
    assert a.label is None
    assert a.line2 is None
    assert a.is_default is False


def test_address_create_with_all_fields():
    a = AddressCreate(
        label="Home",
        line1="42 MG Road",
        line2="Apt 3B",
        city="Bangalore",
        state="Karnataka",
        pincode="560001",
        is_default=True,
    )
    assert a.label == "Home"
    assert a.is_default is True


def test_address_update_all_optional():
    u = AddressUpdate()
    assert u.line1 is None
    assert u.city is None
    assert u.is_default is None
