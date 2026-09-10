"""Brand isolation: agents are hard-scoped to one brand, admins are not."""
from app.api.deps import can_access_brand, scoped_brand_id


class _U:
    def __init__(self, role, brand_id=None):
        self.role = role
        self.brand_id = brand_id


def test_admin_can_access_any_brand():
    u = _U("admin")
    assert can_access_brand(u, "brand-x") is True
    assert can_access_brand(u, "brand-y") is True
    assert scoped_brand_id(u) is None  # admins see everything


def test_agent_scoped_to_own_brand():
    u = _U("agent", "brand-a")
    assert can_access_brand(u, "brand-a") is True
    assert can_access_brand(u, "brand-b") is False
    assert scoped_brand_id(u) == "brand-a"


def test_agent_without_brand_assignment_has_no_reads():
    u = _U("agent", None)
    assert can_access_brand(u, "brand-a") is False
    assert scoped_brand_id(u) is None