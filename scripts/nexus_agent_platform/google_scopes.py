"""Canonical Google scope catalogue for the one Nexus Google OAuth client ('Nexus OS Mac Mini', Desktop).

One OAuth client, two grants (both held in the existing Keychain control plane):

* credential.google.workspace.prod.v1  -- the "Google Core" grant of the owner Google account:
  Gmail / Calendar / Drive (existing scopes, unchanged) + read-only Search Console + read-only GA4
  (+ Business Profile, whose API has no read-only scope).
* credential.google.youtube.upload.prod.v1 -- the YouTube grant. Kept separate on purpose: at consent
  Google asks which channel (possibly a Brand Account) the grant is for, and that identity is not the
  owner mailbox, so YouTube scopes cannot share a token with Gmail / Drive.

Nothing here touches credentials; it only names scopes so the consent flow, the verifier and the MCP
agree on one definition.
"""
from __future__ import annotations

from typing import Iterable

G = "https://www.googleapis.com/auth/"

# service -> (scopes, credential, read_only, note)
SERVICES: dict[str, dict] = {
    "gmail": {"scopes": [G + "gmail.readonly", G + "gmail.modify"], "credential": "workspace", "read_only": False,
              "note": "existing grant; gmail.modify backs the governed draft-to-self / archive tools (no send tool exists)"},
    "calendar": {"scopes": [G + "calendar.events"], "credential": "workspace", "read_only": False,
                 "note": "existing grant; private events without guests only"},
    "drive": {"scopes": [G + "drive.file"], "credential": "workspace", "read_only": False,
              "note": "existing grant; app-created or user-selected files only"},
    "search_console": {"scopes": [G + "webmasters.readonly"], "credential": "workspace", "read_only": True,
                       "note": "read-only; sites.list + searchanalytics.query"},
    "ga4": {"scopes": [G + "analytics.readonly"], "credential": "workspace", "read_only": True,
            "note": "read-only; Analytics Admin accountSummaries + Data API runReport"},
    "business_profile": {"scopes": [G + "business.manage"], "credential": "workspace", "read_only": False,
                         "note": "Google offers no read-only Business Profile scope; the MCP exposes read tools only "
                                 "(posts / edits / review replies are not registered and stay approval-gated). "
                                 "Google must also approve Business Profile API access for the Cloud project."},
    "youtube": {"scopes": [G + "youtube.readonly", G + "youtube.upload", G + "yt-analytics.readonly"], "credential": "youtube", "read_only": False,
                "note": "separate grant (channel identity); youtube.upload exists for approval-gated uploads only; "
                        "captions.list needs youtube.force-ssl (a manage scope) and is deliberately NOT requested"},
}

CREDENTIALS = {"workspace": "credential.google.workspace.prod.v1", "youtube": "credential.google.youtube.upload.prod.v1"}

# consent profiles (what one owner consent requests)
PROFILES: dict[str, list[str]] = {
    "workspace": ["gmail", "calendar", "drive"],
    "core": ["gmail", "calendar", "drive", "search_console", "ga4", "business_profile"],
    "youtube": ["youtube"],
}

# APIs the Cloud project must have enabled for each service (Console > APIs & Services > Library)
APIS: dict[str, list[str]] = {
    "gmail": ["gmail.googleapis.com"], "calendar": ["calendar-json.googleapis.com"], "drive": ["drive.googleapis.com"],
    "search_console": ["searchconsole.googleapis.com"],
    "ga4": ["analyticsadmin.googleapis.com", "analyticsdata.googleapis.com"],
    "business_profile": ["mybusinessaccountmanagement.googleapis.com", "mybusinessbusinessinformation.googleapis.com",
                         "businessprofileperformance.googleapis.com", "mybusiness.googleapis.com"],
    "youtube": ["youtube.googleapis.com", "youtubeanalytics.googleapis.com"],
}

# exact scope names (not substrings: "yt-analytics.readonly" is a YouTube scope, "analytics.readonly" is GA4)
YOUTUBE_SCOPE_NAMES = {"youtube", "youtube.readonly", "youtube.upload", "youtube.force-ssl", "youtubepartner", "yt-analytics.readonly", "yt-analytics-monetary.readonly"}


def name(scope: str) -> str:
    return scope.rsplit("/", 1)[-1]


def scopes_for(services: Iterable[str]) -> list[str]:
    out: list[str] = []
    for s in services:
        for sc in SERVICES[s]["scopes"]:
            if sc not in out:
                out.append(sc)
    return out


def profile_scopes(profile: str) -> list[str]:
    if profile not in PROFILES:
        raise ValueError(f"unknown_google_consent_profile:{profile}")
    scopes = scopes_for(PROFILES[profile])
    validate_separation(profile, scopes)
    return scopes


def validate_separation(profile: str, scopes: Iterable[str]) -> None:
    """A YouTube grant never carries Workspace/marketing scopes, and a Core grant never carries YouTube scopes."""
    scopes = list(scopes)
    if profile == "youtube":
        bad = [s for s in scopes if name(s) not in YOUTUBE_SCOPE_NAMES]
    else:
        bad = [s for s in scopes if name(s) in YOUTUBE_SCOPE_NAMES]
    if bad:
        raise ValueError("SCOPE_SEPARATION_VIOLATION:" + ",".join(name(s) for s in bad))


def services_granted(granted_names: Iterable[str], profile: str) -> dict[str, bool]:
    g = set(granted_names)
    return {s: all(name(sc) in g for sc in SERVICES[s]["scopes"]) for s in PROFILES[profile]}
