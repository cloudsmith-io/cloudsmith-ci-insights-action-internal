import pytest
import importlib
from package_insights.parsers.docker import DockerParser


class TestDockerLogParsing:
    @pytest.fixture(autouse=True)
    def only_docker_parser(self, monkeypatch):
        # Restrict PARSERS to only the Docker parser for these tests
        module = importlib.import_module("package_insights.package_insights.parsers")
        monkeypatch.setattr(module, "PARSERS", [DockerParser()])


    def test_docker_buildkit_build_solve_error(self):
        """Test parsing of Docker buildkit build solve error with 403 Forbidden."""
        log = (
            "ERROR: failed to build: failed to solve: docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb:11.2.3: "
            "failed to resolve source metadata for docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb:11.2.3: "
            "unexpected status from HEAD request to https://docker.cloudsmith.io/v2/cloudsmith/kmanning-testing/mariadb/manifests/11.2.3: 403 Forbidden"
        )
        parser = DockerParser()
        
        # Should match as it contains error indicators and cloudsmith registry
        assert parser.log_matches_format_and_client(log)
        
        # Should extract the image details
        results = list(parser.extract(log))
        assert len(results) >= 1
        
        # Should find the mariadb image with specific tag
        expected = ("cloudsmith", "kmanning-testing", "mariadb", "11.2.3")
        assert expected in results

    def test_docker_non_buildkit_from_failure(self):
        """Test parsing of non-BuildKit build failure with FROM and pull access denied."""
        log = (
            "FROM docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb:11.2.3\n"
            "pull access denied for docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb, "
            "repository does not exist or may require 'docker login': "
            "denied: requested access to the resource is denied: Package is quarantined"
        )
        parser = DockerParser()
        
        # Should match as it contains error indicators and cloudsmith registry
        assert parser.log_matches_format_and_client(log)
        
        # Should extract the image details
        results = list(parser.extract(log))
        assert len(results) >= 1
        
        # Should find the mariadb image with specific tag from the FROM line
        expected = ("cloudsmith", "kmanning-testing", "mariadb", "11.2.3")
        assert expected in results

    def test_pull_access_denied_with_quarantine(self):
        """Test parsing of pull access denied error with quarantine message."""
        log = (
            "pull access denied for docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb, "
            "repository does not exist or may require 'docker login': "
            "denied: requested access to the resource is denied: Package is quarantined"
        )
        parser = DockerParser()
        
        # Should match as it contains error indicators and cloudsmith registry
        assert parser.log_matches_format_and_client(log)
        
        # Should extract the image details
        results = list(parser.extract(log))
        assert len(results) >= 1
        
        # Should find the mariadb image (tag should default to latest since not specified in error)
        expected = ("cloudsmith", "kmanning-testing", "mariadb", "latest")
        assert expected in results

    def test_combined_log_with_multiple_errors(self):
        """Test parsing when multiple error types appear in the same log for the same image."""
        log = (
            "ERROR: failed to build: failed to solve: docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb:11.2.3: "
            "failed to resolve source metadata for docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb:11.2.3: "
            "unexpected status from HEAD request to https://docker.cloudsmith.io/v2/cloudsmith/kmanning-testing/mariadb/manifests/11.2.3: 403 Forbidden\n"
            "pull access denied for docker.cloudsmith.io/cloudsmith/kmanning-testing/mariadb, "
            "repository does not exist or may require 'docker login': "
            "denied: requested access to the resource is denied: Package is quarantined"
        )
        parser = DockerParser()
        
        # Should match
        assert parser.log_matches_format_and_client(log)
        
        # Should extract image details with deduplication (same image, same tag)
        results = list(parser.extract(log))
        assert len(results) >= 1
        
        # Should find the mariadb image with the specific tag (11.2.3)
        expected = ("cloudsmith", "kmanning-testing", "mariadb", "11.2.3")
        assert expected in results

    def test_non_cloudsmith_registry_does_not_match(self):
        """Test that errors from non-Cloudsmith registries do not match."""
        non_cloudsmith_logs = [
            "pull access denied for docker.io/library/nginx:latest",
            "Error response from daemon: manifest for gcr.io/project/image:tag not found",
            "ERROR: failed to build: failed to solve: registry.example.com/image:tag"
        ]
        
        parser = DockerParser()
        
        for log in non_cloudsmith_logs:
            # Should NOT match non-Cloudsmith registries
            assert not parser.log_matches_format_and_client(log)
            
            # Should extract nothing
            results = list(parser.extract(log))
            assert len(results) == 0
