"""Base extractor interface."""

from abc import ABC, abstractmethod
from models.rfq_data import RFQData


class BaseExtractor(ABC):
    """Abstract base class for all file format extractors."""

    @abstractmethod
    def extract(self, file_path: str) -> RFQData:
        """
        Extract RFQ data from the given file.

        Returns a partially-filled RFQData object.
        Fields that could not be extracted are left at their defaults.
        The GUI will allow the user to review and complete them.
        """
        pass

    @staticmethod
    def can_handle(file_path: str) -> bool:
        """Check if this extractor can handle the given file type."""
        return False
