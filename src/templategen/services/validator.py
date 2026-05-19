"""Validator — checks graph integrity and dangling references in a Template."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from templategen.model.template import Template


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    message: str
    target: object | None


class Validator:
    def validate(self, template: Template) -> list[ValidationIssue]:
        raise NotImplementedError
