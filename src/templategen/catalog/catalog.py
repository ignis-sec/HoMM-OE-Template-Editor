"""ReferenceCatalog — abstract source of names and details used in the editor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


class ReferenceCatalog:
    # ── flat name lookups (for autocomplete) ─────────────────────────────
    def known_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def known_content_lists(self) -> Sequence[str]:
        raise NotImplementedError

    def known_content_pools(self) -> Sequence[str]:
        raise NotImplementedError

    def known_biomes(self) -> Sequence[str]:
        raise NotImplementedError

    def known_bonus_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def known_building_constructions(self) -> Sequence[str]:
        raise NotImplementedError

    def known_portals(self) -> Sequence[str]:
        raise NotImplementedError

    def known_meta_object_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def known_artifact_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def known_spell_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def get_artifact(self, sid: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def get_spell(self, sid: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def known_interactable_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def get_interactable(self, sid: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def known_resource_sids(self) -> Sequence[str]:
        raise NotImplementedError

    def get_resource(self, sid: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def known_fractions(self) -> Sequence[str]:
        raise NotImplementedError

    # ── detail lookups (for the explorer) ────────────────────────────────
    def get_content_list(self, name: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def get_content_pool(self, name: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def get_meta_object(self, sid: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def resource_for_mine(self, mine_sid: str) -> str | None:
        raise NotImplementedError

    def water_for_biome(self, biome: str) -> str | None:
        raise NotImplementedError

    # ── reverse lookups (for the explorer) ───────────────────────────────
    def lists_containing(self, sid: str) -> Sequence[str]:
        raise NotImplementedError

    def pools_with_direct_sid(self, sid: str) -> Sequence[str]:
        raise NotImplementedError

    def pools_producing(self, sid: str) -> Sequence[str]:
        raise NotImplementedError

    def pools_banning(self, sid: str) -> Sequence[str]:
        raise NotImplementedError

    def pools_using_list(self, list_name: str) -> Sequence[str]:
        raise NotImplementedError
