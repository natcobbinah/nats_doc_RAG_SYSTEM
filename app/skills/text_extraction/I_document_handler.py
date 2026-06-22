"""Abstract base interface for document content extraction handlers"""

from abc import ABC, abstractmethod
import io 
from typing import List, Dict 

class IDocumentHandler(ABC):

    @abstractmethod
    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        pass