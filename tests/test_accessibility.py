import re
from html.parser import HTMLParser

import pytest
from flask.testing import FlaskClient

from app.models import User, VirtualMachine


class AccessibilityAttributeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.described_by: list[str] = []

    def handle_starttag(
        self, _tag: str, attributes: list[tuple[str, str | None]]
    ) -> None:
        attribute_map = dict(attributes)
        if attribute_map.get("id"):
            self.ids.append(attribute_map["id"])
        if attribute_map.get("aria-describedby"):
            self.described_by.extend(attribute_map["aria-describedby"].split())


def login(client: FlaskClient, user: User, password: str) -> None:
    response = client.post(
        "/login",
        data={"username": user.username, "password": password},
    )
    assert response.status_code == 302


def test_base_layout_has_landmarks_skip_link_and_responsive_navigation(
    client: FlaskClient, viewer_user: User
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b'<html lang="pt-BR">' in response.data
    assert b'class="skip-link" href="#main-content"' in response.data
    assert b'<nav class="navbar navbar-expand-lg' in response.data
    assert b'aria-label="Navega\xc3\xa7\xc3\xa3o principal"' in response.data
    assert b'data-bs-target="#primaryNavigation"' in response.data
    assert b'aria-controls="primaryNavigation"' in response.data
    assert b'<main id="main-content"' in response.data
    assert b"<footer" in response.data
    assert re.search(rb'tabindex="[1-9][0-9]*"', response.data) is None


def test_current_module_is_exposed_to_assistive_technology(
    client: FlaskClient, viewer_user: User, sample_virtual_machine: VirtualMachine
) -> None:
    login(client, viewer_user, "valid-viewer-password")

    response = client.get("/assets")

    assert response.status_code == 200
    assert b'class="dropdown-item active" href="/assets" aria-current="page"' in (
        response.data
    )
    assert b'href="/admin/users"' not in response.data


@pytest.mark.parametrize(
    ("path", "region_label"),
    [
        ("/datacenters", "Datacenters cadastrados"),
        ("/rooms", "Salas cadastradas"),
        ("/racks", "Racks cadastrados"),
        ("/assets", "Ativos cadastrados"),
        ("/virtual-machines", "Máquinas Virtuais cadastradas"),
        ("/admin/users", "Usuários cadastrados"),
        ("/admin/audit", "Eventos de auditoria"),
    ],
)
def test_data_tables_are_named_scrollable_keyboard_regions(
    path: str,
    region_label: str,
    client: FlaskClient,
    admin_user: User,
    sample_virtual_machine: VirtualMachine,
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get(path)

    assert response.status_code == 200
    expected_region = (
        f'role="region" aria-label="{region_label}" tabindex="0"'
    ).encode()
    assert expected_region in response.data
    assert b"<caption" in response.data
    headers = re.findall(rb"<th\b([^>]*)>", response.data)
    assert headers
    assert all(b'scope="col"' in attributes for attributes in headers)


def test_form_descriptions_reference_existing_unique_ids(
    client: FlaskClient, admin_user: User
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get("/admin/users/new")
    parser = AccessibilityAttributeParser()
    parser.feed(response.get_data(as_text=True))

    assert response.status_code == 200
    assert len(parser.ids) == len(set(parser.ids))
    assert parser.described_by
    assert set(parser.described_by).issubset(parser.ids)
    assert "is_active-help" in parser.described_by
    assert b'aria-describedby="None"' not in response.data


def test_dashboard_activity_table_has_accessible_structure(
    client: FlaskClient, admin_user: User
) -> None:
    login(client, admin_user, "valid-admin-password")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b'aria-label="Atividade recente" tabindex="0"' in response.data
    assert b"Atividade recente no sistema</caption>" in response.data
    assert response.data.count(b'<th scope="col">') >= 4


def test_styles_preserve_focus_reduced_motion_and_local_table_overflow(
    client: FlaskClient,
) -> None:
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert b":focus-visible" in response.data
    assert b"outline: 3px solid" in response.data
    assert b"@media (prefers-reduced-motion: reduce)" in response.data
    assert b".content-shell { border-radius: 0.6rem; overflow-x: auto; }" not in (
        response.data
    )
