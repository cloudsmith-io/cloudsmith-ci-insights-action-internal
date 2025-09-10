"""Utility functions for Cloudsmith API interactions and package operations."""

import os
import sys
import re
import requests
import click
from urllib.parse import quote as _urlquote
from typing import Optional
from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    QUARANTINED_DETECTED = 1
    PARSE_ERROR = 2
    MISSING_API_KEY = 3


def get_api_key() -> str:
    api_key = os.getenv('CLOUDSMITH_API_KEY')
    if not api_key:
        click.secho('❌ Missing API Key', fg='red', bold=True)
        click.echo('   CLOUDSMITH_API_KEY environment variable not set')
        click.secho('💡 Hint: export CLOUDSMITH_API_KEY=your_key_here', fg='blue')
        sys.exit(ExitCode.MISSING_API_KEY)
    return api_key


def build_headers(api_key: str) -> dict:
    return {
        'X-Api-Key': api_key,
        'Accept': 'application/json',
    }


def fetch_policies(workspace: str, headers: dict) -> dict:
    """Return a dict of policy_slug_perm -> policy object."""
    base_url = f"https://api.cloudsmith.io/v2/workspaces/{workspace}/policies/"
    page = 1
    total_pages = None
    policies = {}

    while True:
        url = f"{base_url}?page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            click.secho(f'⚠️  Failed to fetch policies (page {page}) (HTTP {resp.status_code})', fg='yellow')
            click.echo(f'   Response: {resp.text}')
            break
        try:
            data = resp.json()
        except ValueError:
            click.secho(f'⚠️  Invalid JSON while fetching policies (page {page})', fg='yellow')
            break
        for policy in data.get('results', []):
            slug = policy.get('slug_perm')
            if slug and slug not in policies:  # avoid duplicates if any
                policies[slug] = policy

        if total_pages is None:
            total_header = resp.headers.get('x-pagination-pagetotal')
            if total_header and total_header.isdigit():
                total_pages = int(total_header)
            else:
                # No pagination headers -> assume single page
                break
        page += 1
        if total_pages is not None and page > total_pages:
            break
    return policies


def fetch_policy_of_action(workspace: str, headers: dict, action_slug: str) -> str|None:
    """Return policy information for a given action slug."""
    base_url = f"https://api.cloudsmith.io/v2/workspaces/{workspace}/policies/"
    page = 1
    total_pages = None

    while True:
        url = f"{base_url}?page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            click.secho(f'⚠️  Failed to fetch policies (page {page}) (HTTP {resp.status_code})', fg='yellow')
            click.echo(f'   Response: {resp.text}')
            break
        try:
            data = resp.json()
        except ValueError:
            click.secho(f'⚠️  Invalid JSON while fetching policies (page {page})', fg='yellow')
            break
        for policy in data.get('results', []):
            slug = policy.get('slug_perm')
            actions_url = f"https://api.cloudsmith.io/v2/workspaces/{workspace}/policies/{slug}/actions/"
            resp = requests.get(actions_url, headers=headers)
            if resp.status_code != 200:
                click.secho(f"⚠️  Could not fetch actions for policy '{slug}' (HTTP {resp.status_code})", fg='yellow')
                continue
            for action in resp.json().get('results', []):
                if action.get('slug_perm') == action_slug:
                    policy_name = policy.get('name', 'Unnamed Policy')
                    policy_desc = policy.get('description', 'No description available')
                    return (f"📋 Policy Name: {policy_name}\n"
                        f"🔗 Policy Slug: {slug}\n"
                        f"📝 Description: {policy_desc}")

        if total_pages is None:
            total_header = resp.headers.get('x-pagination-pagetotal')
            if total_header and total_header.isdigit():
                total_pages = int(total_header)
            else:
                # No pagination headers -> assume single page
                break
        page += 1
        if total_pages is not None and page > total_pages:
            break
    return None


def parse_package_entry(entry: str):
    if '==' in entry:
        return entry.split('==', 1)
    return entry, None


def find_package(workspace: str, repo: str, headers: dict, name: str, version: Optional[str]):
    """Locate a package using Cloudsmith packages API."""

    base_url = f"https://api.cloudsmith.io/packages/{workspace}/{repo}/"
    
    query_term = name if not version else f"name:{name} AND version:{version}"
    page = 1
    total_pages = None
    while True:
        url = f"{base_url}?sort=-date&query={_urlquote(query_term)}&page={page}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            click.secho(
                f"⚠️  Failed to list packages (page {page}) in {workspace}/{repo} (HTTP {resp.status_code})",
                fg='yellow'
            )
            click.echo(f'   Response: {resp.text}')
            return None
        try:
            packages = resp.json()
        except ValueError:
            click.secho(f"⚠️  Invalid JSON response for page {page}", fg='yellow')
            return None

        if isinstance(packages, dict) and 'results' in packages:
            packages_iter = packages.get('results', [])
        else:
            packages_iter = packages

        for pkg in packages_iter:
            if pkg.get('display_name') == name and (version is None or pkg.get('version') == version):
                return pkg

        if total_pages is None:
            total_header = resp.headers.get('x-pagination-pagetotal')
            if total_header and total_header.isdigit():
                total_pages = int(total_header)
            else:
                # No pagination headers -> assume single page; stop.
                break
        page += 1
        if total_pages is not None and page > total_pages:
            break
    return None


ACTION_SLUG_PERM_REGEX = re.compile(r"slug_perm '([A-Za-z0-9]+)'")


def extract_action_slug(status_reason: str) -> Optional[str]:
    if not status_reason:
        return None
    m = ACTION_SLUG_PERM_REGEX.search(status_reason)
    return m.group(1) if m else None


def find_policy_for_action_slug(policies: dict, action_slug: str, workspace: str, headers: dict) -> Optional[str]:
    """Iterate policies and their actions to find which policy contains the action slug."""
    if not action_slug:
        return None
    for policy_slug, policy in policies.items():
        actions_url = f"https://api.cloudsmith.io/v2/workspaces/{workspace}/policies/{policy_slug}/actions/"
        resp = requests.get(actions_url, headers=headers)
        if resp.status_code != 200:
            click.secho(f"⚠️  Could not fetch actions for policy '{policy_slug}' (HTTP {resp.status_code})", fg='yellow')
            continue
        for action in resp.json().get('results', []):
            if action.get('slug_perm') == action_slug:
                policy_name = policy.get('name', 'Unnamed Policy')
                policy_desc = policy.get('description', 'No description available')
                return (f"📋 Policy Name: {policy_name}\n"
                       f"🔗 Policy Slug: {policy_slug}\n"
                       f"📝 Description: {policy_desc}")
    return None


def parse_logs_for_all_details(log_text: str, unique: bool = True):
    """Parse log output for all (workspace, repo, package, version) tuples.

    Extensible pipeline:
      1. Iterate registered parsers; the first whose log_matches_format_and_client() returns True is used.
      2. If that parser returns results, return them.
      3. If detection passes but no results extracted, fall through to next parser 
        - this allows us to try multiple parsers where similar errors occur 
        - TODO: it might make more sense to match package format and then iterate through multiple client parsers
      4. Return an empty list if no results found
    """
    from ..parsers import PARSERS
    
    for parser in PARSERS:
        if parser.log_matches_format_and_client(log_text):
            results = parser.parse(log_text)
            if results:
                return results
    return []
