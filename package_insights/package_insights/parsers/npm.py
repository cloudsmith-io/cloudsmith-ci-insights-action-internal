import re
from .base import BaseFormatClientParser


class NpmParser(BaseFormatClientParser):
    package_format = "npm"
    client = "npm"

    # Match signed URL style (npm http fetch GET 403 ... dl.cloudsmith.io/signed/.../npm/<pkg>/<pkg>-<ver>.tgz)
    NPM_SIGNED_FETCH_RE = re.compile(
        r"npm http fetch GET 403\s+(https://dl\.cloudsmith\.io/[^\s]+/npm/([A-Za-z0-9_.-]+)/\2-([0-9]+\.[0-9]+\.[0-9]+[^/]*)\.tgz)",
        re.IGNORECASE,
    )
    # Match direct registry http fetch 403 lines (npm http fetch GET 403 https://npm.cloudsmith.io/ws/repo/<pkg>/-/<pkg>-<ver>.tgz)
    NPM_HTTP_DIRECT_FETCH_RE = re.compile(
        r"npm http fetch GET 403\s+(https://npm\.cloudsmith\.io/[^\s]+/([A-Za-z0-9_.-]+)/-/\2-([0-9]+\.[0-9]+\.[0-9]+[^/]*)\.tgz)",
        re.IGNORECASE,
    )
    # Match npm.cloudsmith.io style (quarantine message version)
    NPM_DIRECT_FETCH_RE = re.compile(
        r"npm error 403 403 Forbidden - GET (https://npm\.cloudsmith\.io/[^\s]+/([A-Za-z0-9_.-]+)/-/\2-([0-9]+\.[0-9]+\.[0-9]+[^/]*)\.tgz)",
        re.IGNORECASE,
    )
    # Generic 403 Forbidden GET (signed) in error line
    NPM_ERROR_SIGNED_RE = re.compile(
        r"npm error 403 403 Forbidden - GET (https://dl\.cloudsmith\.io/[^\s]+/npm/([A-Za-z0-9_.-]+)/\2-([0-9]+\.[0-9]+\.[0-9]+[^/]*)\.tgz)",
        re.IGNORECASE,
    )
    WORKSPACE_REPO_FROM_URL_RE = re.compile(r"https://(?:dl|npm)\.cloudsmith\.io/(?:signed/)?([^/]+)/([^/]+)/")

    def log_matches_format_and_client(self, log_text: str) -> bool:
        return 'npm ' in log_text and '403' in log_text

    def extract(self, log_text: str):
        matched = False
        patterns = [
            self.NPM_SIGNED_FETCH_RE,
            self.NPM_HTTP_DIRECT_FETCH_RE,
            self.NPM_DIRECT_FETCH_RE,
            self.NPM_ERROR_SIGNED_RE,
        ]
        for pattern in patterns:
            for m in pattern.finditer(log_text):
                full_url, pkg, ver = m.groups()
                ws_repo = self.WORKSPACE_REPO_FROM_URL_RE.search(full_url)
                if not ws_repo:
                    continue
                workspace, repo = ws_repo.groups()
                yield (workspace, repo, pkg, ver)
                matched = True
        if matched:
            return

    def normalise_name(self, name: str) -> str:
        return name  # npm names usually kept as-is (ignoring scoped packages for now)

    def normalise_version(self, version: str) -> str:
        return version
