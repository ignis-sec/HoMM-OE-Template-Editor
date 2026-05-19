"""Read a .rmg.json file into a Template."""

from pathlib import Path

from templategen.model.template import Template


class TemplateLoader:
    def load(self, path: Path) -> Template:
        raise NotImplementedError
