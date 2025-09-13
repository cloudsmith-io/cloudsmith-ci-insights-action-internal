"""CLI interface for Cloudsmith package insights."""

import os
import sys
import click
from typing import Optional

from ..utils import (
    ExitCode,
    get_api_key,
    build_headers,
    find_package,
    extract_action_slug,
    fetch_policy_of_action,
    parse_logs_for_all_details,
)


def report_package(package_name: str, pkg: dict, policy_info: str, action_slug: str, follow_up: Optional[str] = None):
    """Display package information and quarantine status."""
    status_str = pkg.get('status_str', 'Unknown')
    status_reason = pkg.get('status_reason', 'No reason provided')
    quarantined = pkg.get('is_quarantined', False)
    version = pkg.get('version')
    
    # Package info
    click.secho(f"📦 Package: {package_name}=={version} 📦", fg='white', bold=True)
    click.echo("-" * 40)
    
    if not quarantined:
        click.secho("🛑 Status: Likely Blocked", fg='green', bold=True)
        click.secho(f"🔍 Current Status: {status_str}", fg='blue')
        click.echo()
        click.secho("⚠️  IMPORTANT:", fg='yellow', bold=True)
        click.echo("   Package is likely blocked given 403 response.")
        click.echo("   This could be a transient issue or a policy restriction.")
        
        if follow_up:
            click.echo()
            click.secho("🎯 Next Steps:", fg='magenta', bold=True)
            click.echo(f"   {follow_up}")
        click.echo("=" * 60)
        return quarantined  # False
    
    # Quarantined package
    click.secho("🚫 Status: QUARANTINED", fg='red', bold=True)
    click.secho(f"📊 Package Status: {status_str}", fg='yellow')
    click.secho(f"💬 Reason: {status_reason}", fg='yellow')
    
    if action_slug:
        click.echo()
        click.secho(f"🔑 Action Slug: {action_slug}", fg='magenta')
    
    if policy_info:
        click.echo()
        click.secho("🛡️  POLICY DETAILS:", fg='blue', bold=True)
        for line in policy_info.split('\n'):
            click.echo(f"   {line}")
    else:
        click.echo()
        click.secho("🛡️  POLICY DETAILS:", fg='blue', bold=True)
        click.echo("   No associated policy found - this can happen when the action has occurred but since been deleted")
    
    if follow_up:
        click.echo()
        click.secho("🎯 Next Steps:", fg='magenta', bold=True)
        click.echo(f"   {follow_up}")
    
    click.echo("-" * 40)
    click.echo()

    return quarantined # True


def _read_log_text(log):
    """Read log text from file or use raw string."""
    if os.path.exists(log):
        with open(log, 'r', encoding='utf-8', errors='ignore') as fh:
            return fh.read()
    return log


def _validate_log(log_text):
    return True
    """Validate log for 403 errors and Python package format."""
    if '403' not in log_text:
        click.secho('ℹ️  No 403 errors detected in log', fg='blue')
        click.echo('   Insights are currently only supported for 403 (Forbidden) errors')
        return False
    return True


def _handle_parse_error():
    """Handle error when package details cannot be parsed."""
    click.secho('❌ Unable to parse package details from log', fg='red', bold=True)
    click.echo('   Could not extract package name and version information')
    sys.exit(ExitCode.PARSE_ERROR)


def _handle_package_not_found(package_name, package_version, workspace, repo, follow_up):
    """Handle error when package is not found in repository."""
    click.secho(f'❌ Package not found: {package_name}=={package_version}', fg='red', bold=True)
    click.echo(f'   Not present in repository: {workspace}/{repo}')
    if follow_up:
        click.echo()
        click.secho("🎯 Next Steps:", fg='magenta', bold=True)
        click.echo(f"   {follow_up}")


@click.command()
@click.argument('log', nargs=1)
@click.option('--follow-up', 'follow_up', required=False, help='Custom follow-up instructions to display with results.')
def package_insights(log, follow_up):
    """Parse a pip install log, derive package + workspace/repo, then look up quarantine/policy info."""
    log_text = _read_log_text(log)
    if not _validate_log(log_text):
        return
    matches = parse_logs_for_all_details(log_text, unique=True)
    if not matches:
        _handle_parse_error()
        return

    api_key = get_api_key()
    headers = build_headers(api_key)

    # Print Header
    click.echo("=" * 60)
    click.secho("☁️  CLOUDSMITH INSIGHTS ☁️", fg='cyan', bold=True)
    click.echo("=" * 60)

    # Track whether any quarantined package exists to triggered an exit code after loop.
    quarantined_detected = False
    for workspace, repo, package_name, package_version, package_format, client in matches:

        match = find_package(workspace, repo, headers, package_name, package_version, package_format)
        if match is None:
            # Report missing package but continue processing remaining packages.
            _handle_package_not_found(package_name, package_version, workspace, repo, follow_up)
            continue

        status_reason = match.get('status_reason', 'No reason provided')
        action_slug = extract_action_slug(status_reason)
        policy_info = None
        if action_slug:
            policy_info = fetch_policy_of_action(workspace, headers, action_slug)
        quarantined = report_package(
            package_name,
            match,
            policy_info,
            action_slug,
            follow_up=follow_up
        )
        if quarantined:
            quarantined_detected = True

    if quarantined_detected:
        # After reporting all, use exit code 1 to indicate at least one quarantined
        sys.exit(ExitCode.QUARANTINED_DETECTED)
