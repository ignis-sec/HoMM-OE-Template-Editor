"""Serialize a Template back to .rmg.json, preserving formatting and unknown fields."""

from pathlib import Path

from templategen.model.template import Template


class TemplateWriter:
    def write(self, template: Template, path: Path) -> None:
        raise NotImplementedError
