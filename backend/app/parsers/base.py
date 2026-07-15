from abc import ABC, abstractmethod


class DocumentParser(ABC):

    @abstractmethod
    def parse(self, content: bytes) -> tuple[str, int, str]:
        """
        Parses the document content and returns a tuple containing:
        - extracted_text: str
        - page_count: int
        - parser_name: str
        """
        pass
