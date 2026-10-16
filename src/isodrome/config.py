"""The CLI's local configuration: named profiles, each an endpoint, an API key and a namespace.

Stored in `~/.config/isodrome/config.toml` (or `$ISODROME_CONFIG_DIR`, or
`$XDG_CONFIG_HOME/isodrome`), readable only by its owner because it holds API keys:

    profile = "default"

    [profiles.default]
    endpoint = "https://stg.api.isodrome.ai"
    api_key = "iso_..."
    namespace = "default"
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from isodrome._transport import DEFAULT_ENDPOINT

DEFAULT_PROFILE = "default"


def config_dir() -> Path:
    if explicit := os.environ.get("ISODROME_CONFIG_DIR"):
        return Path(explicit)
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "isodrome"


def config_path() -> Path:
    return config_dir() / "config.toml"


@dataclass
class Profile:
    endpoint: str = DEFAULT_ENDPOINT
    api_key: str | None = None
    namespace: str | None = None


@dataclass
class Config:
    current: str = DEFAULT_PROFILE
    profiles: dict[str, Profile] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        path = path or config_path()
        if not path.exists():
            return cls()
        data = tomllib.loads(path.read_text())
        profiles = {
            name: Profile(
                endpoint=values.get("endpoint", DEFAULT_ENDPOINT),
                api_key=values.get("api_key"),
                namespace=values.get("namespace"),
            )
            for name, values in data.get("profiles", {}).items()
        }
        return cls(current=data.get("profile", DEFAULT_PROFILE), profiles=profiles)

    def profile(self, name: str | None = None) -> Profile:
        """The named (or current) profile, created empty if missing."""
        return self.profiles.setdefault(name or self.current, Profile())

    def save(self, path: Path | None = None) -> Path:
        path = path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lines = [f"profile = {_quote(self.current)}"]
        for name, profile in sorted(self.profiles.items()):
            lines += ["", f"[profiles.{_quote(name)}]", f"endpoint = {_quote(profile.endpoint)}"]
            if profile.api_key:
                lines.append(f"api_key = {_quote(profile.api_key)}")
            if profile.namespace:
                lines.append(f"namespace = {_quote(profile.namespace)}")
        # Created 0600 before anything is written, so the key is never readable by others.
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write("\n".join(lines) + "\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        return path


def _quote(value: str) -> str:
    # A JSON string is a valid TOML basic string.
    return json.dumps(value)
