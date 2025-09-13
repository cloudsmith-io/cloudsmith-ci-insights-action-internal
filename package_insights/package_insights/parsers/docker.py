import re
from package_insights.parsers import BaseFormatClientParser


class DockerParser(BaseFormatClientParser):
    """
    Parser for Docker client pull FAILURE messages from Cloudsmith repositories.
    
    Only handles failed Docker pull operations, specifically:
    - Pull access denied errors
    - Authentication failures during pull
    - Registry connection errors during pull
    - 403/404/401 HTTP errors from Cloudsmith registries
    """
    package_format = "docker"
    client = "docker"

    # Match classic, non-BuildKit build failures
    # Example: "FROM docker.cloudsmith.io/workspace/repo/image:tag" followed by "pull access denied"
    DOCKER_NON_BUILDKIT_BUILD_FAILURE_RE = re.compile(
        r"FROM\s+docker\.cloudsmith\.io/([^/]+)/([^/]+)/([^:/\s]+)(?::([^/\s]+))?.*?pull access denied",
        re.IGNORECASE | re.DOTALL,
    )

    # Match Docker pull access denied errors (explicit failure)
    # Example: "pull access denied for docker.cloudsmith.io/workspace/repo/image"
    DOCKER_PULL_ACCESS_DENIED_RE = re.compile(
        r"pull access denied for docker\.cloudsmith\.io/([^/]+)/([^/]+)/([^/,\s]+)",
        re.IGNORECASE,
    )

    # Match classic, non-BuildKit build failures
    DOCKER_BUILDKIT_BUILD_FAILURE_RE = re.compile(
        r"ERROR: failed to build: failed to solve: docker\.cloudsmith\.io/([^/]+)/([^/]+)/([^:/,\s]+)(?::([^:/,\s]+))?",
        re.IGNORECASE,
    )    
    
    # Match Docker daemon error responses (explicit failure)
    # Example: "Error response from daemon: ... docker.cloudsmith.io/workspace/repo/image:tag"
    DOCKER_DAEMON_ERROR_RE = re.compile(
        r"Error response from daemon:.*?docker\.cloudsmith\.io/([^/]+)/([^/]+)/([^:/,\s]+)(?::([^:/,\s]+))?",
        re.IGNORECASE,
    )

    def log_matches_format_and_client(self, log_text: str) -> bool:
        print("log_matches_format_and_client called")
        """Check if the log contains Docker pull FAILURE indicators from Cloudsmith."""
        # Only match if we have both Cloudsmith registry AND failure indicators
        has_cloudsmith_registry = "docker.cloudsmith.io" in log_text.lower()
        
        failure_indicators = [
            "error: failed to build",
            "pull access denied",
            "error response from daemon",
            "denied:",
            "403",
            "401",
            "404",
            "forbidden",
            "unauthorized",
            "quarantined"
        ]
        has_failure = any(indicator in log_text.lower() for indicator in failure_indicators)

        print(f"has_cloudsmith_registry: {has_cloudsmith_registry}, has_failure: {has_failure}")
        
        return has_cloudsmith_registry and has_failure

    def extract(self, log_text: str):
        seen_images = set()
        
        # Strategy 1: Extract from non-BuildKit build failures (FROM + pull access denied)
        for match in self.DOCKER_NON_BUILDKIT_BUILD_FAILURE_RE.finditer(log_text):
            workspace, repo, image_name, tag = match.groups()
            tag = tag or "latest"  # Default to latest if no tag specified
            
            image_key = (workspace, repo, image_name, tag)
            if image_key not in seen_images:
                seen_images.add(image_key)
                yield (workspace, repo, image_name, tag, self.package_format)
        
        # Strategy 2: Extract from BuildKit build failures (ERROR: failed to build: failed to solve)
        for match in self.DOCKER_BUILDKIT_BUILD_FAILURE_RE.finditer(log_text):
            workspace, repo, image_name, tag = match.groups()
            tag = tag or "latest"  # Default to latest if no tag specified
            
            image_key = (workspace, repo, image_name, tag)
            if image_key not in seen_images:
                seen_images.add(image_key)
                yield (workspace, repo, image_name, tag, self.package_format)
        
        # Strategy 3: Extract from explicit Docker pull access denied errors
        for match in self.DOCKER_PULL_ACCESS_DENIED_RE.finditer(log_text):
            workspace, repo, image_name = match.groups()
            # Try to find the tag from context
            tag = self._extract_tag_from_context(log_text, workspace, repo, image_name)
            
            image_key = (workspace, repo, image_name, tag)
            if image_key not in seen_images:
                seen_images.add(image_key)
                yield (workspace, repo, image_name, tag, self.package_format)
        
        # Strategy 4: Extract from Docker daemon error messages
        for match in self.DOCKER_DAEMON_ERROR_RE.finditer(log_text):
            workspace, repo, image_name, tag = match.groups()
            tag = tag or "latest"  # Default to latest if no tag specified
            
            image_key = (workspace, repo, image_name, tag)
            if image_key not in seen_images:
                seen_images.add(image_key)
                yield (workspace, repo, image_name, tag, self.package_format)

    def _extract_tag_from_context(self, log_text: str, workspace: str, repo: str, image_name: str) -> str:
        """Try to extract the tag from the surrounding context in the log."""
        # Look for the full image reference with tag in the log
        full_image_pattern = re.compile(
            rf"docker\.cloudsmith\.io/{re.escape(workspace)}/{re.escape(repo)}/{re.escape(image_name)}:([^/\s]+)",
            re.IGNORECASE
        )
        
        match = full_image_pattern.search(log_text)
        if match:
            return match.group(1)
        
        # Default to latest if no tag found
        return "latest"

    def normalise_name(self, name: str) -> str:
        return name

    def normalise_version(self, version: str) -> str:
        # Docker tags should be kept as-is since they can contain various formats
        # like semantic versions, build numbers, branch names, etc.
        return version if version else "latest"
