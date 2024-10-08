from typing import Optional

from core.rag.extractor.extractor_base import BaseExtractor
from core.rag.models.document import Document


class StringExtractor(BaseExtractor):
    """
    Extracts string features from a given text.
    """

    def __init__(self, string: str, encoding: Optional[str] = None, autodetect_encoding: bool = False):
        self.string = string
        self.encoding = encoding
        self.autodetect_encoding = autodetect_encoding

    def extract(self) -> list[Document]:
        """ Extracts string features from a given text. """
        text = self.string
        metadata = {"source": "string"}
        return [Document(page_content=text, metadata=metadata)]
