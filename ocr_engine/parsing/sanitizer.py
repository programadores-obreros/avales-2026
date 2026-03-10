"""Data-driven line sanitizer using YAML config files."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


CONFIGS_DIR = Path(__file__).parent / "configs"


@dataclass
class SanitizeRule:
    """A single sanitization rule."""

    pattern: str
    replacement: str
    description: str = ""
    literal: bool = False
    _compiled: re.Pattern | None = field(default=None, repr=False)

    def compile(self) -> None:
        if not self.literal:
            self._compiled = re.compile(self.pattern)

    def apply(self, text: str) -> str:
        if self.literal:
            return text.replace(self.pattern, self.replacement)
        if self._compiled is None:
            self.compile()
        return self._compiled.sub(self.replacement, text)


class LineSanitizer:
    """Loads base + distrito YAML configs and applies sanitization rules.

    Usage:
        sanitizer = LineSanitizer("069")  # La Matanza
        clean = sanitizer.sanitize("DNI 14009185. PEREZ JUAN 0-069-MS5-0042 1")
    """

    def __init__(self, distrito: str | None = None) -> None:
        self.distrito = distrito
        self._rules: list[SanitizeRule] = []
        self._config: dict = {}
        self._load_configs()

    def _load_configs(self) -> None:
        # Load base rules
        base_path = CONFIGS_DIR / "_base.yaml"
        if base_path.exists():
            base_config = yaml.safe_load(base_path.read_text(encoding="utf-8"))
            self._add_rules(base_config.get("sanitize_rules", []))
            self._config.update(base_config)

        # Load distrito overlay
        if self.distrito:
            distrito_path = CONFIGS_DIR / f"distrito_{self.distrito}.yaml"
            if distrito_path.exists():
                distrito_config = yaml.safe_load(distrito_path.read_text(encoding="utf-8"))
                self._add_rules(distrito_config.get("sanitize_rules", []))
                # Overlay distrito config onto base
                for key in ("distrito", "distrito_name", "filas_esperadas",
                            "codigos_escuela", "destinos_especiales"):
                    if key in distrito_config:
                        self._config[key] = distrito_config[key]

    def _add_rules(self, rules_data: list[dict]) -> None:
        for rule_dict in rules_data:
            rule = SanitizeRule(
                pattern=rule_dict["pattern"],
                replacement=rule_dict["replacement"],
                description=rule_dict.get("description", ""),
                literal=rule_dict.get("literal", False),
            )
            rule.compile()
            self._rules.append(rule)

    def sanitize(self, line: str) -> str:
        """Apply all sanitization rules to a line of OCR text."""
        s = line.strip()
        if not s:
            return s
        for rule in self._rules:
            s = rule.apply(s)
        return s

    @property
    def rule_count(self) -> int:
        """Total number of loaded rules (base + distrito)."""
        return len(self._rules)

    @property
    def filas_esperadas(self) -> int:
        return self._config.get("filas_esperadas", 60)

    @property
    def codigos_escuela(self) -> list[str]:
        return self._config.get("codigos_escuela", [])

    @property
    def destinos_especiales(self) -> list[str]:
        return self._config.get("destinos_especiales", [])

    @property
    def distrito_name(self) -> str:
        return self._config.get("distrito_name", "unknown")
