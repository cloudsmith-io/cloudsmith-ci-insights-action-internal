from package_insights.package_insights.utils import parse_logs_for_all_details


class TestLogParsing:
    """Integration tests with all parsers present."""

    def test_parse_python_error_single_package(self):
        log = (
            "ERROR: Could not install requirement foo==2.0.0 from https://dl.cloudsmith.io/public/acme/tools/python/foo-2.0.0.whl because of HTTP error 403 Client Error: Forbidden for url\n"
        )
        assert parse_logs_for_all_details(log) == [
            ("acme", "tools", "foo", "2.0.0"),
        ]

    def test_parse_npm_error_single_package(self):
        log = (
            "npm error code E403\n"
            "npm error 403 403 Forbidden - GET https://npm.cloudsmith.io/workspace-name/repository-name/xmlbuilder/-/xmlbuilder-11.0.1.tgz - Package is quarantined.\n"
        )
        matches = parse_logs_for_all_details(log)
        assert matches[0] == ("workspace-name", "repository-name", "xmlbuilder", "11.0.1")
