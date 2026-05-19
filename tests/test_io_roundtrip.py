"""Load every example template, write it back, assert structural equality."""

import json
from pathlib import Path

import pytest

from templategen.io.loader import TemplateLoader
from templategen.io.writer import TemplateWriter

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "example-templates"
EXAMPLES = sorted(EXAMPLES_DIR.glob("*.rmg.json"))

if not EXAMPLES:
    pytest.skip("no example-templates available", allow_module_level=True)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.stem)
def test_roundtrip(path: Path, tmp_path: Path) -> None:
    template = TemplateLoader().load(path)
    out = tmp_path / path.name
    TemplateWriter().write(template, out)
    assert json.loads(out.read_text(encoding="utf-8")) == json.loads(path.read_text(encoding="utf-8"))
