"""CatalogExplorer — browse content lists, content pools, SIDs, and meta objects."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING, Any, Final

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from templategen.catalog.game_data import GameDataCatalog

_CATEGORY_LABELS: Final[dict[str, str]] = {
    "lists": "Content Lists",
    "pools": "Content Pools",
    "sids": "SIDs",
    "meta": "Meta Objects",
    "artifacts": "Artifacts",
    "spells": "Spells",
}
_CATEGORY_ORDER: Final[list[str]] = ["lists", "pools", "sids", "meta", "artifacts", "spells"]


class CatalogExplorer(QWidget):
    def __init__(self, catalog: GameDataCatalog) -> None:
        super().__init__()
        self._catalog = catalog

        self.setMinimumHeight(280)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        self._tabs = QTabWidget()
        outer.addWidget(self._tabs)

        self._tabs_by_category: dict[str, _CategoryTab] = {}
        for category in _CATEGORY_ORDER:
            tab = _CategoryTab(category, catalog, self._navigate)
            self._tabs.addTab(tab, _CATEGORY_LABELS[category])
            self._tabs_by_category[category] = tab

        catalog.changed.connect(self._refresh_all)
        self._refresh_all()

    def reveal(self, category: str, name: str) -> None:
        self._navigate(category, name)

    def _navigate(self, category: str, name: str) -> None:
        tab = self._tabs_by_category.get(category)
        if tab is None:
            return
        self._tabs.setCurrentWidget(tab)
        tab.select(name)

    def _refresh_all(self) -> None:
        for tab in self._tabs_by_category.values():
            tab.refresh()


class _CategoryTab(QWidget):
    def __init__(
        self,
        category: str,
        catalog: GameDataCatalog,
        navigate: Callable[[str, str], None],
    ) -> None:
        super().__init__()
        self._category = category
        self._catalog = catalog
        self._navigate = navigate
        self._all_names: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #888;")
        outer.addWidget(self._count_label)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter…")
        self._search.textChanged.connect(self._apply_filter)
        outer.addWidget(self._search)

        splitter = QSplitter(Qt.Orientation.Vertical)
        outer.addWidget(splitter, stretch=1)

        self._list = QListWidget()
        self._list.currentTextChanged.connect(self._show_detail)
        splitter.addWidget(self._list)

        self._detail = QTextBrowser()
        self._detail.setOpenLinks(False)
        self._detail.anchorClicked.connect(self._on_anchor)
        splitter.addWidget(self._detail)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

    def refresh(self) -> None:
        self._all_names = self._fetch_names()
        self._count_label.setText(f"{len(self._all_names)} entries")
        self._apply_filter(self._search.text())

    def select(self, name: str) -> None:
        items = self._list.findItems(name, Qt.MatchFlag.MatchExactly)
        if not items:
            self._search.clear()
            items = self._list.findItems(name, Qt.MatchFlag.MatchExactly)
        if items:
            self._list.setCurrentItem(items[0])
            self._list.scrollToItem(items[0])

    def _fetch_names(self) -> list[str]:
        if self._category == "lists":
            return sorted(self._catalog.known_content_lists())
        if self._category == "pools":
            return sorted(self._catalog.known_content_pools())
        if self._category == "sids":
            return sorted(self._catalog.known_sids())
        if self._category == "meta":
            return sorted(self._catalog.known_meta_object_sids())
        if self._category == "artifacts":
            return sorted(self._catalog.known_artifact_sids())
        if self._category == "spells":
            return sorted(self._catalog.known_spell_sids())
        return []

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        self._list.clear()
        for name in self._all_names:
            if not needle or needle in name.lower():
                self._list.addItem(name)

    def _show_detail(self, name: str) -> None:
        if not name:
            self._detail.clear()
            return
        if self._category == "lists":
            html = self._render_list(name)
        elif self._category == "pools":
            html = self._render_pool(name)
        elif self._category == "sids":
            html = self._render_sid(name)
        elif self._category == "meta":
            html = self._render_meta(name)
        elif self._category in ("artifacts", "spells"):
            html = self._render_artifact_or_spell(name)
        else:
            html = ""
        self._detail.setHtml(html)

    def _on_anchor(self, url: QUrl) -> None:
        target = url.toString()
        if ":" not in target:
            return
        kind, name = target.split(":", 1)
        category = {
            "list": "lists",
            "pool": "pools",
            "sid": "sids",
            "meta": "meta",
            "artifact": "artifacts",
            "spell": "spells",
        }.get(kind)
        if category is not None:
            self._navigate(category, name)

    # ── renderers ────────────────────────────────────────────────────────

    def _render_list(self, name: str) -> str:
        data = self._catalog.get_content_list(name)
        if data is None:
            return _not_found(name)
        rows = [
            _format_list_entry(entry)
            for entry in (data.get("content") or [])
            if isinstance(entry, dict)
        ]
        used_by = self._catalog.pools_using_list(name)
        used_html = _link_list("pool", used_by) if used_by else "<em>none</em>"
        return f"""
            <h3>{escape(name)}</h3>
            <p><b>{len(rows)}</b> content item(s)</p>
            <ol>{''.join(f"<li>{r}</li>" for r in rows)}</ol>
            <h4>Used by pools</h4>
            <p>{used_html}</p>
        """

    def _render_pool(self, name: str) -> str:
        data = self._catalog.get_content_pool(name)
        if data is None:
            return _not_found(name)

        parts = [f"<h3>{escape(name)}</h3>"]

        value_dist = data.get("valueDistribution")
        if isinstance(value_dist, dict):
            parts.append(_render_value_distribution(value_dist))

        for key in ("priceBounds", "weights"):
            if key in data:
                parts.append(f"<p><b>{key}:</b> {escape(str(data[key]))}</p>")

        groups = data.get("groups") or []
        parts.append(f"<h4>Groups ({len(groups)})</h4>")
        for i, group in enumerate(groups):
            parts.append(_render_pool_group(i, group))

        bans = data.get("bans") or []
        parts.append(f"<h4>Bans ({len(bans)})</h4>")
        if bans:
            sids = [b.get("sid") for b in bans if isinstance(b, dict) and isinstance(b.get("sid"), str)]
            parts.append("<p>" + _link_list("sid", sids) + "</p>")
        else:
            parts.append("<p><em>none</em></p>")

        return "".join(parts)

    def _render_sid(self, name: str) -> str:
        parts = [f"<h3>{escape(name)}</h3>"]

        meta = self._catalog.get_meta_object(name)
        if meta is not None:
            parts.append("<h4>Meta object</h4>")
            parts.append(_render_kv_table(meta))

        resource = self._catalog.resource_for_mine(name)
        if resource is not None:
            parts.append(
                f"<p>Mine produces: <a href='sid:{escape(resource)}'>{escape(resource)}</a></p>"
            )

        for label, names, link_kind in (
            ("Lists containing it", self._catalog.lists_containing(name), "list"),
            ("Pools that include it directly", self._catalog.pools_with_direct_sid(name), "pool"),
            ("Pools that can produce it (transitive)", self._catalog.pools_producing(name), "pool"),
            ("Pools banning it", self._catalog.pools_banning(name), "pool"),
        ):
            parts.append(f"<h4>{escape(label)} ({len(names)})</h4>")
            parts.append("<p>" + (_link_list(link_kind, names) if names else "<em>none</em>") + "</p>")

        return "".join(parts)

    def _render_artifact_or_spell(self, name: str) -> str:
        kind_label = "Artifact" if self._category == "artifacts" else "Spell"
        parts = [
            f"<h3>{escape(name)}</h3>",
            f"<p><em>{kind_label} SID</em></p>",
        ]
        for label, names, link_kind in (
            ("Lists containing it", self._catalog.lists_containing(name), "list"),
            ("Pools that include it directly", self._catalog.pools_with_direct_sid(name), "pool"),
            ("Pools that can produce it (transitive)", self._catalog.pools_producing(name), "pool"),
            ("Pools banning it", self._catalog.pools_banning(name), "pool"),
        ):
            parts.append(f"<h4>{escape(label)} ({len(names)})</h4>")
            parts.append("<p>" + (_link_list(link_kind, names) if names else "<em>none</em>") + "</p>")
        return "".join(parts)

    def _render_meta(self, name: str) -> str:
        data = self._catalog.get_meta_object(name)
        if data is None:
            return _not_found(name)
        parts = [
            f"<h3>{escape(name)}</h3>",
            _render_kv_table(data),
        ]
        used_in_lists = self._catalog.lists_containing(name)
        used_in_pools = self._catalog.pools_producing(name)
        parts.append(
            f"<h4>Lists containing it ({len(used_in_lists)})</h4>"
            + "<p>" + (_link_list("list", used_in_lists) if used_in_lists else "<em>none</em>") + "</p>"
        )
        parts.append(
            f"<h4>Pools producing it ({len(used_in_pools)})</h4>"
            + "<p>" + (_link_list("pool", used_in_pools) if used_in_pools else "<em>none</em>") + "</p>"
        )
        return "".join(parts)


def _format_list_entry(entry: dict[str, Any]) -> str:
    sid = entry.get("sid")
    bits = []
    if isinstance(sid, str):
        bits.append(f"<a href='sid:{escape(sid)}'>{escape(sid)}</a>")
    if "variant" in entry:
        bits.append(f"variant={escape(str(entry['variant']))}")
    if "biome" in entry:
        bits.append(f"biome={escape(str(entry['biome']))}")
    if "weight" in entry:
        bits.append(f"<em>weight {escape(str(entry['weight']))}</em>")
    return " · ".join(bits) if bits else escape(str(entry))


def _render_pool_group(index: int, group: dict[str, Any]) -> str:
    weight = group.get("weight", "?")
    parts = [f"<p><b>Group [{index}]</b> · weight {escape(str(weight))}</p>"]

    include_lists = group.get("includeLists") or []
    if include_lists:
        parts.append("<p style='margin-left: 14px;'>includes: " + _link_list("list", include_lists) + "</p>")

    direct = group.get("content") or []
    if direct:
        parts.append(f"<p style='margin-left: 14px;'>direct content ({len(direct)}):</p>")
        items = [
            f"<li>{_format_list_entry(entry)}</li>"
            for entry in direct
            if isinstance(entry, dict)
        ]
        parts.append(f"<ol style='margin-left: 30px;'>{''.join(items)}</ol>")

    return "".join(parts)


def _render_value_distribution(dist: dict[str, Any]) -> str:
    bounds = dist.get("priceBounds")
    weights = dist.get("weights")
    return (
        "<p><b>Value distribution:</b> "
        f"priceBounds={escape(str(bounds))}, weights={escape(str(weights))}</p>"
    )


def _render_kv_table(data: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td><b>{escape(str(k))}</b></td><td>{escape(str(v))}</td></tr>"
        for k, v in data.items()
    )
    return f"<table cellspacing='4'>{rows}</table>"


def _link_list(kind: str, names: Sequence[str]) -> str:
    return ", ".join(f"<a href='{kind}:{escape(n)}'>{escape(n)}</a>" for n in names)


def _not_found(name: str) -> str:
    return f"<h3>{escape(name)}</h3><p><em>Not found in catalog.</em></p>"
