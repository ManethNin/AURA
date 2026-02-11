"""
Maven Central Verification Tool
Verifies dependency versions against Maven Central before writing rewrite.yaml or diffs.
Uses the Maven Central Search API (no authentication required).
"""

import requests
from typing import Optional
from app.utils.logger import logger


class MavenCentralTool:
    """
    Verifies and resolves Maven dependency versions against Maven Central.
    
    Instead of guessing version formats (e.g. appending .0),
    this tool queries the real source of truth — Maven Central — to confirm
    whether a version string actually exists for a given artifact.
    """

    SEARCH_URL = "https://search.maven.org/solrsearch/select"
    REQUEST_TIMEOUT = 10  # seconds

    def resolve_correct_version(self, group_id: str, artifact_id: str, version: str) -> str:
        """
        Resolve a correct, existing version for a Maven artifact.
        
        Strategy (Verify, Don't Guess):
            1. Check if the exact version exists on Maven Central.
            2. If not, try the alternative format (X.Y <-> X.Y.0).
            3. If still not found, fall back to the latest available version.
        
        Args:
            group_id: Maven groupId (e.g. "commons-codec")
            artifact_id: Maven artifactId (e.g. "commons-codec")
            version: The version string to verify (e.g. "1.15")
            
        Returns:
            A verified version string that exists on Maven Central,
            or the original version as a last resort if the API is unreachable.
        """
        dep_label = f"{group_id}:{artifact_id}:{version}"
        version = version.strip()

        # Strip leading 'v' prefix (e.g. "v2.1.0" -> "2.1.0")
        if version.lower().startswith('v'):
            version = version[1:]

        # 1. Check if the exact requested version exists
        if self._check_version_exists(group_id, artifact_id, version):
            logger.info(f"[MavenCentralTool] ✅ Version verified: {dep_label}")
            return version

        # 2. Try the alternative format (handle 2-digit vs 3-digit mismatch)
        alt_version = self._get_alternative_format(version)
        if alt_version and self._check_version_exists(group_id, artifact_id, alt_version):
            logger.info(f"[MavenCentralTool] ✅ Corrected version: {group_id}:{artifact_id}:{version} -> {alt_version}")
            return alt_version

        # 3. Fallback: fetch the latest available version
        logger.warning(
            f"[MavenCentralTool] ⚠️ Version '{version}'"
            + (f" and '{alt_version}'" if alt_version else "")
            + f" not found for {group_id}:{artifact_id}. Fetching latest..."
        )
        latest = self._get_latest_version(group_id, artifact_id)
        if latest and latest != "LATEST":
            logger.info(f"[MavenCentralTool] ✅ Using latest version: {group_id}:{artifact_id}:{latest}")
            return latest

        # 4. Absolute fallback — return the original version and let Maven try
        logger.warning(f"[MavenCentralTool] ⚠️ Could not verify {dep_label}, using original value")
        return version

    # ------------------------------------------------------------------
    # Public helpers (useful for agents / tools)
    # ------------------------------------------------------------------

    def check_version_exists(self, group_id: str, artifact_id: str, version: str) -> bool:
        """Public wrapper — checks if a specific GAV coordinate exists on Maven Central."""
        return self._check_version_exists(group_id, artifact_id, version)

    def get_latest_version(self, group_id: str, artifact_id: str) -> Optional[str]:
        """Public wrapper — returns the latest version of an artifact, or None."""
        v = self._get_latest_version(group_id, artifact_id)
        return v if v and v != "LATEST" else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_alternative_format(version: str) -> Optional[str]:
        """
        Return an alternative version format to try:
            - "1.15"   -> "1.15.0"
            - "1.15.0" -> "1.15"
        Returns None if no alternative makes sense.
        """
        if version.count('.') == 2 and version.endswith('.0'):
            return version[:-2]       # 1.15.0 -> 1.15
        elif version.count('.') == 1:
            parts = version.split('.')
            try:
                int(parts[0])
                int(parts[1])
                return f"{version}.0"  # 1.15 -> 1.15.0
            except ValueError:
                return None
        return None

    def _check_version_exists(self, g: str, a: str, v: str) -> bool:
        """Query Maven Central to see if a specific GAV coordinate exists."""
        params = {
            "q": f'g:"{g}" AND a:"{a}" AND v:"{v}"',
            "rows": 1,
            "wt": "json",
        }
        try:
            resp = requests.get(self.SEARCH_URL, params=params, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            found = data["response"]["numFound"] > 0
            logger.debug(f"[MavenCentralTool] Check {g}:{a}:{v} -> {'exists' if found else 'NOT found'}")
            return found
        except Exception as e:
            logger.error(f"[MavenCentralTool] Failed to query Maven Central for {g}:{a}:{v}: {e}")
            return False  # Can't verify — caller decides fallback

    def _get_latest_version(self, g: str, a: str) -> str:
        """Fetch the latest version of an artifact from Maven Central."""
        params = {
            "q": f'g:"{g}" AND a:"{a}"',
            "core": "gav",
            "rows": 1,
            "wt": "json",
        }
        try:
            resp = requests.get(self.SEARCH_URL, params=params, timeout=self.REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data["response"]["numFound"] > 0:
                return data["response"]["docs"][0]["v"]
        except Exception as e:
            logger.error(f"[MavenCentralTool] Failed to fetch latest version for {g}:{a}: {e}")
        return "LATEST"


# Singleton instance for shared use across agents
maven_central_tool = MavenCentralTool()
