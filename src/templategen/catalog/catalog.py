"""ReferenceCatalog — autocomplete/validation source for external string identifiers."""

from collections.abc import Iterable


class ReferenceCatalog:
    def known_sids(self) -> Iterable[str]:
        raise NotImplementedError

    def known_content_pools(self) -> Iterable[str]:
        raise NotImplementedError

    def known_content_lists(self) -> Iterable[str]:
        raise NotImplementedError

    def known_biomes(self) -> Iterable[str]:
        raise NotImplementedError

    def known_factions(self) -> Iterable[str]:
        raise NotImplementedError

    def known_building_constructions(self) -> Iterable[str]:
        raise NotImplementedError
