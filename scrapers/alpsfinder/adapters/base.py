from abc import ABC, abstractmethod
from collections.abc import Iterator

from ..models import RawListing


class SourceAdapter(ABC):
    code: str
    name: str
    base_url: str

    @abstractmethod
    def fetch(self, communes: list[dict]) -> Iterator[RawListing]:
        """Yield RawListings for the given commune rows (dicts from the communes table)."""
