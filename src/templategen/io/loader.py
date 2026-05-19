"""Read a .rmg.json file into a Template."""

from pathlib import Path

from templategen.io.json_format import loads
from templategen.model.template import Template


class TemplateLoader:
    def load(self, path: Path) -> Template:
        return Template.model_validate(loads(path.read_text(encoding="utf-8")))
