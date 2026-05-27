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
        issues: list[ValidationIssue] = []

        layout_names = {zl.name for zl in template.zoneLayouts}
        bundle_names = {b.name for b in template.mandatoryContent}
        limit_names = {c.name for c in template.contentCountLimits}

        for v_idx, variant in enumerate(template.variants):
            v_label = f"Variant {v_idx + 1}"
            zone_names: set[str] = set()
            connection_names: set[str] = set()

            for zone in variant.zones:
                if zone.name in zone_names:
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR, f"{v_label}: duplicate zone name '{zone.name}'", zone
                        )
                    )
                zone_names.add(zone.name)

                if zone.layout and zone.layout not in layout_names:
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            f"{v_label}: zone '{zone.name}' uses unknown layout '{zone.layout}'",
                            zone,
                        )
                    )

                for ref in zone.mandatoryContent or []:
                    if ref not in bundle_names:
                        issues.append(
                            ValidationIssue(
                                Severity.WARNING,
                                f"{v_label}: zone '{zone.name}' references unknown bundle '{ref}'",
                                zone,
                            )
                        )

                refs = zone.contentCountLimits
                ref_list = [refs] if isinstance(refs, str) else (refs or [])
                for ref in ref_list:
                    if ref not in limit_names:
                        issues.append(
                            ValidationIssue(
                                Severity.WARNING,
                                f"{v_label}: zone '{zone.name}' references unknown count limit '{ref}'",
                                zone,
                            )
                        )

            # Named connections that touch each zone — used to cross-check roads.
            connections_by_zone: dict[str, set[str]] = {n: set() for n in zone_names}
            for conn in variant.connections:
                label = conn.name or f"({conn.from_}→{conn.to})"
                if conn.name:
                    if conn.name in connection_names:
                        issues.append(
                            ValidationIssue(
                                Severity.WARNING,
                                f"{v_label}: duplicate connection name '{conn.name}'",
                                conn,
                            )
                        )
                    connection_names.add(conn.name)
                    for endpoint in (conn.from_, conn.to):
                        if endpoint in connections_by_zone:
                            connections_by_zone[endpoint].add(conn.name)
                if conn.from_ not in zone_names:
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            f"{v_label}: connection {label} from='{conn.from_}' refers to unknown zone",
                            conn,
                        )
                    )
                if conn.to not in zone_names:
                    issues.append(
                        ValidationIssue(
                            Severity.ERROR,
                            f"{v_label}: connection {label} to='{conn.to}' refers to unknown zone",
                            conn,
                        )
                    )

            for zone in variant.zones:
                touching = connections_by_zone.get(zone.name, set())
                referenced: set[str] = set()
                for road in zone.roads or []:
                    for anchor in (road.from_, road.to):
                        if anchor.type != "Connection" or not anchor.args:
                            continue
                        ref = str(anchor.args[0])
                        referenced.add(ref)
                        if ref not in touching:
                            issues.append(
                                ValidationIssue(
                                    Severity.ERROR,
                                    f"{v_label}: zone '{zone.name}' has a road pointing to "
                                    f"connection '{ref}', which does not touch this zone",
                                    zone,
                                )
                            )
                for conn_name in sorted(touching - referenced):
                    issues.append(
                        ValidationIssue(
                            Severity.WARNING,
                            f"{v_label}: zone '{zone.name}' has connection '{conn_name}' but no "
                            f"road leading to it",
                            zone,
                        )
                    )

        return issues
