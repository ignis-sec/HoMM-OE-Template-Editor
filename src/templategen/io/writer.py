"""Serialize a Template back to .rmg.json, preserving fields the model didn't claim."""

from pathlib import Path

from templategen.io.json_format import dumps
from templategen.model.template import Template


class TemplateWriter:
    def write(self, template: Template, path: Path) -> None:
        data = template.model_dump(by_alias=True, exclude_unset=True)
        path.write_text(dumps(data), encoding="utf-8")
