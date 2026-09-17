#!/usr/bin/env python3
"""Automated management-demo Basic Auth safety check (Claude finding, security §E).

Verifies that the DEPLOYED demo Basic Auth is NOT the CI fixture credential
(user ``sentinel-demo`` / password ``test``). Two independent checks:

1. Behavioural (preferred): request the deployed URL with the CI fixture
   credential. A non-401 response means the CI credential is accepted -> FAIL.
2. Configuration: if a Railway token + service/environment ids are provided,
   read ``BASIC_AUTH_HTPASSWD`` and compare it byte-for-byte to the CI fixture.

On FAIL, with ``--rotate`` and Railway access, a strong new credential is
generated, the Railway variable is updated (nginx-compatible SHA-512 crypt), and
the new plaintext is written to a local file (never stdout). The check output is
only ``Railway Basic Auth differs from CI fixture: PASS/FAIL`` — the real
credential/hash is never printed.

Stdlib only; no new dependencies. Configuration via environment:
  DEMO_URL                  deployed demo URL for the behavioural probe
  RAILWAY_TOKEN             Railway API token (project- or account-scoped)
  RAILWAY_PROJECT_ID        Railway project id (for rotation/config read)
  RAILWAY_ENVIRONMENT_ID    Railway environment id
  RAILWAY_SERVICE_ID        frontend service id holding BASIC_AUTH_HTPASSWD
  NEW_CREDENTIAL_FILE       where to write a rotated plaintext credential
"""

from __future__ import annotations

import argparse
import base64
import crypt
import hashlib
import json
import os
import secrets
import sys
import urllib.error
import urllib.request

CI_FIXTURE_USER = "sentinel-demo"
CI_FIXTURE_PASSWORD = "test"  # noqa: S105 - a public CI fixture value, not a secret
# The exact htpasswd string committed in CI (SHA-1 of "test").
_CI_SHA = base64.b64encode(hashlib.sha1(CI_FIXTURE_PASSWORD.encode()).digest()).decode()  # noqa: S324
CI_FIXTURE_HTPASSWD = f"{CI_FIXTURE_USER}:{{SHA}}{_CI_SHA}"

RAILWAY_GRAPHQL = "https://backboard.railway.app/graphql/v2"


def _behavioural_probe(url: str) -> bool | None:
    """Return True if the deployed URL ACCEPTS the CI fixture credential (FAIL)."""
    token = base64.b64encode(f"{CI_FIXTURE_USER}:{CI_FIXTURE_PASSWORD}".encode()).decode()
    request = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return response.status != 401
    except urllib.error.HTTPError as exc:
        return exc.code != 401
    except OSError as exc:
        print(f"(probe could not reach {url}: {exc})", file=sys.stderr)
        return None


def _railway_request(token: str, query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        RAILWAY_GRAPHQL,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read().decode())
    if payload.get("errors"):
        raise RuntimeError(f"Railway API error: {payload['errors']}")
    return payload["data"]


def _railway_htpasswd(token: str, project: str, environment: str, service: str) -> str | None:
    query = """
    query vars($projectId: String!, $environmentId: String!, $serviceId: String!) {
      variables(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId)
    }
    """
    data = _railway_request(
        token,
        query,
        {"projectId": project, "environmentId": environment, "serviceId": service},
    )
    variables = data.get("variables") or {}
    return variables.get("BASIC_AUTH_HTPASSWD")


def _railway_set_htpasswd(
    token: str, project: str, environment: str, service: str, value: str
) -> None:
    mutation = """
    mutation upsert($input: VariableUpsertInput!) {
      variableUpsert(input: $input)
    }
    """
    _railway_request(
        token,
        mutation,
        {
            "input": {
                "projectId": project,
                "environmentId": environment,
                "serviceId": service,
                "name": "BASIC_AUTH_HTPASSWD",
                "value": value,
            }
        },
    )


def _generate_htpasswd() -> tuple[str, str]:
    """Return (plaintext 'user:password', nginx-compatible htpasswd line)."""
    user = "arie-demo"
    password = secrets.token_urlsafe(24)
    hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
    return f"{user}:{password}", f"{user}:{hashed}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rotate", action="store_true", help="rotate the credential on FAIL")
    args = parser.parse_args()

    demo_url = os.environ.get("DEMO_URL")
    token = os.environ.get("RAILWAY_TOKEN")
    project = os.environ.get("RAILWAY_PROJECT_ID")
    environment = os.environ.get("RAILWAY_ENVIRONMENT_ID")
    service = os.environ.get("RAILWAY_SERVICE_ID")

    failed = False
    checked = False

    if demo_url:
        accepts_fixture = _behavioural_probe(demo_url)
        if accepts_fixture is not None:
            checked = True
            failed = failed or accepts_fixture

    if token and project and environment and service:
        deployed = _railway_htpasswd(token, project, environment, service)
        if deployed is not None:
            checked = True
            failed = failed or (deployed.strip() == CI_FIXTURE_HTPASSWD)

    if not checked:
        print(
            "Railway Basic Auth differs from CI fixture: UNKNOWN "
            "(no DEMO_URL probe and no Railway config access)",
            file=sys.stderr,
        )
        return 2

    if failed and args.rotate and token and project and environment and service:
        plaintext, htpasswd_line = _generate_htpasswd()
        _railway_set_htpasswd(token, project, environment, service, htpasswd_line)
        target = os.environ.get("NEW_CREDENTIAL_FILE", "new-demo-credential.txt")
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(plaintext + "\n")
        os.chmod(target, 0o600)
        print(f"(rotated demo credential written to {target}; redeploy the frontend service)")
        failed = False

    print(f"Railway Basic Auth differs from CI fixture: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
