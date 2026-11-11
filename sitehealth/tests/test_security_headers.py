import re

from django.contrib.auth.models import User
from django.test import Client

from briefs.site_setup import SiteStructure


def test_public_pages_send_a_strict_policy_with_a_nonce(
    client: Client, site_structure: SiteStructure
) -> None:
    response = client.get("/en/")

    policy = response["Content-Security-Policy"]
    nonce = re.search(r"'nonce-([^']+)'", policy)
    assert nonce is not None
    assert "script-src 'self' 'nonce-" in policy
    assert "'unsafe-inline'" not in policy.split("script-src")[1].split(";")[0]
    assert "object-src 'none'" in policy
    assert f'<script nonce="{nonce.group(1)}">' in response.content.decode()


def test_each_response_gets_a_fresh_nonce(
    client: Client, site_structure: SiteStructure
) -> None:
    first = client.get("/en/")["Content-Security-Policy"]
    second = client.get("/en/")["Content-Security-Policy"]

    assert first != second


def test_admin_allows_wagtails_inline_scripts_but_no_other_origins(
    client: Client, admin_user: User
) -> None:
    client.force_login(admin_user)

    policy = client.get("/admin/")["Content-Security-Policy"]

    assert "script-src 'self' 'unsafe-inline'" in policy
    assert "default-src 'self'" in policy
    assert "connect-src 'self'" in policy
