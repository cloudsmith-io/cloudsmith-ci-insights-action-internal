import pytest
from package_insights.package_insights.utils import parse_logs_for_all_details
from package_insights.package_insights.parsers import NpmParser
import importlib


class TestNpmLogParsing:
    @pytest.fixture(autouse=True)
    def only_npm_parser(self, monkeypatch):
        # Restrict PARSERS to only the Npm parser for these tests
        module = importlib.import_module("package_insights.package_insights.parsers")
        monkeypatch.setattr(module, "PARSERS", [NpmParser()])

    def test_parse_npm_signed_fetch_lines(self):
        log = (
            "npm http fetch GET 403 https://dl.cloudsmith.io/signed/workspace-name/repository-name/upstream/filename/npm/xml2js/xml2js-0.6.2.tgz?created=1&expires=2 10ms\n"
            "npm http fetch GET 403 https://dl.cloudsmith.io/signed/workspace-name/repository-name/upstream/filename/npm/jmespath/jmespath-0.16.0.tgz?created=1&expires=2 11ms\n"
            "npm error 403 403 Forbidden - GET https://npm.cloudsmith.io/workspace-name/repository-name/xmlbuilder/-/xmlbuilder-11.0.1.tgz - Package is quarantined.\n"
        )
        matches = parse_logs_for_all_details(log)
        assert ("workspace-name", "repository-name", "xml2js", "0.6.2") in matches
        assert ("workspace-name", "repository-name", "jmespath", "0.16.0") in matches

    def test_parse_npm_error_direct_quarantine_line(self):
        log = (
            "npm error code E403\n"
            "npm error 403 403 Forbidden - GET https://npm.cloudsmith.io/workspace-name/repository-name/xmlbuilder/-/xmlbuilder-11.0.1.tgz - Package is quarantined.\n"
        )
        matches = parse_logs_for_all_details(log)
        assert matches[0] == ("workspace-name", "repository-name", "xmlbuilder", "11.0.1")

    def test_parse_npm_error_signed_line(self):
        log = (
            "npm error code E403\n"
            "npm error 403 403 Forbidden - GET https://dl.cloudsmith.io/signed/workspace-name/repository-name/upstream/filename/npm/vary/vary-1.1.2.tgz?created=1&expires=2\n"
        )
        matches = parse_logs_for_all_details(log)
        assert matches[0] == ("workspace-name", "repository-name", "vary", "1.1.2")

    def test_parse_multiple_npm_direct_fetch_lines(self):
        log = (
            "npm http fetch GET 403 https://npm.cloudsmith.io/workspace-name/repository-name/xmlbuilder/-/xmlbuilder-11.0.1.tgz 10ms (cache skip)\n"
            "npm http fetch GET 403 https://npm.cloudsmith.io/workspace-name/repository-name/querystring/-/querystring-0.2.0.tgz 11ms (cache skip)\n"
            "npm http fetch GET 403 https://npm.cloudsmith.io/workspace-name/repository-name/url/-/url-0.10.3.tgz 12ms (cache skip)\n"
        )
        matches = parse_logs_for_all_details(log)
        assert ("workspace-name", "repository-name", "xmlbuilder", "11.0.1") in matches
        assert ("workspace-name", "repository-name", "querystring", "0.2.0") in matches
        assert ("workspace-name", "repository-name", "url", "0.10.3") in matches

    def test_parse_npm_detection_no_match_returns_empty(self):
        # Contains 'npm ' and '403' to trigger detection, but no recognized patterns
        log = (
            "npm WARN 403 rate limit exceeded for token\n"
            "npm info attempt registry ping\n"
        )
        assert parse_logs_for_all_details(log) == []

    def test_parse_npm_duplicate_signed_fetch_dedup(self):
        log = (
            "npm http fetch GET 403 https://dl.cloudsmith.io/signed/wsA/repoA/upstream/x/npm/dup/dup-0.1.0.tgz?created=1&expires=2 10ms\n"
            "npm http fetch GET 403 https://dl.cloudsmith.io/signed/wsA/repoA/upstream/x/npm/dup/dup-0.1.0.tgz?created=1&expires=2 11ms\n"  # duplicate
        )
        matches = parse_logs_for_all_details(log)
        assert matches == [("wsA", "repoA", "dup", "0.1.0")]
