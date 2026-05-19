"""JSON formatting helpers — tab indentation, trailing newline, UTF-8 passthrough."""

import json
from typing import Any, Final

INDENT: Final[str] = "\t"


def dumps(data: Any) -> str:
    return json.dumps(data, indent=INDENT, ensure_ascii=False) + "\n"


def loads(text: str) -> Any:
    return json.loads(text)
