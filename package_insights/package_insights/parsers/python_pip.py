import re
from package_insights.parsers import BaseFormatClientParser


# Regex for extracting package info from artifact URLs
LOG_403_TARBALL_URL_RE = re.compile(
    r"""
    (?:.*403.*?)?                              # Optional: any text before '403', non-greedy
    https://dl\.cloudsmith\.io/                # Match the base Cloudsmith URL
    [^/]+/                                     # Match the domain segment (not captured)
    ([^/]+)/                                   # Capture group 1: workspace
    ([^/]+)/                                   # Capture group 2: repo
    python/                                    # Match the 'python' segment
    ([A-Za-z0-9_.-]+)-                         # Capture group 3: package name
    ([0-9][A-Za-z0-9_.-]*)                     # Capture group 4: version (starts with a digit)
    \.                                         # Literal dot before extension
    (?:tar\.gz|zip|whl)                        # Match one of the allowed extensions
    """,
    re.VERBOSE
)


class PythonPipParser(BaseFormatClientParser):
    package_format = "python"
    client = "pip"

    # Match name==version from error log
    ERROR_COULD_NOT_INSTALL_RE = re.compile(
        r"ERROR: Could not install requirement\s+([A-Za-z0-9_.-]+)==([0-9][A-Za-z0-9_.-]*)\s+from\s+(https://dl\.cloudsmith\.io/[^\s)]+)",
        re.IGNORECASE,
    )
    # Match name from error log (pip install called without specific version)
    ERROR_COULD_NOT_INSTALL_NO_VER_RE = re.compile(
        r"ERROR: Could not install requirement\s+([A-Za-z0-9_.-]+)\s+from\s+(https://dl\.cloudsmith\.io/[^\s)]+)",
        re.IGNORECASE,
    )
    WORKSPACE_REPO_FROM_URL_RE = re.compile(r"https://dl\.cloudsmith\.io/[^/]+/([^/]+)/([^/]+)/python/")
    # Extract from wheel filename e.g. python_gitlab-6.3.0-py3-none-any.whl
    ARTIFACT_FILENAME_RE = re.compile(r"/python/([A-Za-z0-9_.-]+)-([0-9][A-Za-z0-9_.-]*)-py[0-9]", re.IGNORECASE)

    def log_matches_format_and_client(self, log_text: str) -> bool:
        return "ERROR: Could not install requirement" in log_text and "python" in log_text

    def extract(self, log_text: str):
        # First: explicit version form
        matched = False
        for m in self.ERROR_COULD_NOT_INSTALL_RE.finditer(log_text):
            pkg, ver, url = m.groups()
            nsrp = self.WORKSPACE_REPO_FROM_URL_RE.search(url)
            if not nsrp:
                continue
            workspace, repo = nsrp.groups()
            yield (workspace, repo, pkg, ver, self.package_format)
            matched = True
        if matched:
            return

        # Second: no-version form; derive version from artifact filename if possible
        for m in self.ERROR_COULD_NOT_INSTALL_NO_VER_RE.finditer(log_text):
            pkg, url = m.groups()
            nsrp = self.WORKSPACE_REPO_FROM_URL_RE.search(url)
            if not nsrp:
                continue
            workspace, repo = nsrp.groups()
            ver = None
            art = self.ARTIFACT_FILENAME_RE.search(url)
            if art:
                wheel_name, wheel_ver = art.groups()
                ver = wheel_ver
            else:
                # As a fallback attempt to pull version from any artifact URL in log
                art2 = self.ARTIFACT_FILENAME_RE.search(log_text)
                if art2:
                    _, wheel_ver = art2.groups()
                    ver = wheel_ver
            if ver:
                yield (workspace, repo, pkg, ver, self.package_format)
                matched = True
        if matched:
            return

        # Fallback: artifact URLs
        for m in LOG_403_TARBALL_URL_RE.finditer(log_text):
            ns, rp, pkg, ver = m.groups()
            yield (ns, rp, pkg, ver, self.package_format)

    def normalise_name(self, name: str) -> str:
        # Keep original requested form (hyphens) if present; ensure underscores from artifact names
        # are converted to hyphens for consistency with pip requirement syntax.
        return name.replace('_', '-')

    def normalise_version(self, version: str) -> str:
        # Strip trailing wheel/platform qualifiers if they slipped in (defensive)
        if not version:
            return version
        # Match PEP 440-compliant version strings: X.Y, X.Y.Z, and optional pre/post/dev tags
        m = re.match(r"^(\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9_.-]*)?)$", version)
        return m.group(1) if m else version
