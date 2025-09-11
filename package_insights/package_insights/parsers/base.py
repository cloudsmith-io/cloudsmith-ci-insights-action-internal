from abc import ABC, abstractmethod


class BaseFormatClientParser(ABC):
    """Abstract base parser for a (package_format, client) pair.

    Subclasses must implement:
      log_matches_format_and_client(log_text): return True if the logs indicate this is the correct parser
      extract(log_text): yield raw tuples (workspace, repo, package, version)
      normalise_name(name): normalise package names (optional override)
      normalise_version(version): normalise package versions (optional override)
    """
    package_format = "generic"
    client = "generic"

    @abstractmethod
    def log_matches_format_and_client(self, log_text: str) -> bool:
        """Check if the log text matches this parser's format and client.
        
        Args:
            log_text: The raw log text to analyze
            
        Returns:
            True if this parser should handle the log, False otherwise
        """
        pass

    @abstractmethod
    def extract(self, log_text: str):
        """Extract package information from log text.
        
        Args:
            log_text: The raw log text to parse
            
        Yields:
            Tuples of (workspace, repo, package_name, version)
        """
        pass

    def normalise_name(self, name: str) -> str:
        """Normalise package names. Override if needed.
        
        Args:
            name: Raw package name
            
        Returns:
            Normalised package name
        """
        return name

    def normalise_version(self, version: str) -> str:
        """Normalise package versions. Override if needed.
        
        Args:
            version: Raw version string
            
        Returns:
            Normalised version string
        """
        return version

    def parse(self, log_text: str):
        """Parse log text and return deduplicated results.
        
        Args:
            log_text: The raw log text to parse
            
        Returns:
            List of unique (workspace, repo, normalised_name, normalised_version) tuples
        """
        seen = set()
        results = []
        for workspace, repo, name, version in self.extract(log_text):
            normalised_name = self.normalise_name(name)
            normalised_version = self.normalise_version(version)
            tup = (workspace, repo, normalised_name, normalised_version)
            if tup not in seen:
                seen.add(tup)
                results.append(tup)
        return results

