
class BaseFormatClientParser:
    """Base parser for a (package_format, client) pair.

    Subclasses should implement:
      log_matches_format_and_client(log_text): return True if the logs indicate this is the correct parser
      extract(log_text): yield raw tuples (workspace, repo, package, version)
      normalise_name(name)
      normalise_version(version)
    """
    package_format = "generic"
    client = "generic"

    def log_matches_format_and_client(self, log_text: str) -> bool:  # pragma: no cover - default
        return False

    def extract(self, log_text: str):  # pragma: no cover - default
        return []

    def normalise_name(self, name: str) -> str:
        return name

    def normalise_version(self, version: str) -> str:
        return version

    def parse(self, log_text: str):
        seen = set()
        results = []
        for workspace, repo, name, version, package_format, client in self.extract(log_text):
            normalised_name = self.normalise_name(name)
            normalised_version = self.normalise_version(version)
            tup = (workspace, repo, normalised_name, normalised_version, package_format, client)
            if tup not in seen:
                seen.add(tup)
                results.append(tup)
        return results

