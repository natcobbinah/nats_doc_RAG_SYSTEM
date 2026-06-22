import io
import os
import sys
import zipfile
from typing import Dict, List
import xml.etree.ElementTree as ET

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromXps(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    @staticmethod
    def _xml_to_text(xml_content: bytes) -> str:
        root = ET.fromstring(xml_content)
        texts = []
        for elem in root.iter():
            value = elem.attrib.get("UnicodeString")
            if value:
                texts.append(value)
        return " ".join(texts).strip()

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from XPS (ZIP-based) documents."""
        try:
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                page_files = [
                    info.filename
                    for info in archive.infolist()
                    if info.filename.lower().endswith((".fpage", ".xml"))
                ]

                pages_data: List[Dict] = []
                for i, page_name in enumerate(page_files):
                    raw = archive.read(page_name)
                    text = self._xml_to_text(raw)
                    pages_data.append(
                        {
                            "id": sanitize_and_standardize_doc_id(f"{blob_name}-page-{i + 1}-{page_name}"),
                            "page_number": i + 1,
                            "entry_name": page_name,
                            "content": text,
                            "source_filename": blob_name,
                            "title": blob_name,
                            "author": "",
                            "creation_date": "",
                            "modification_date": "",
                            "total_pages": len(page_files),
                            "file_extension": "xps",
                            "url": source_url,
                        }
                    )

                return pages_data
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from XPS file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.xps")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromXps()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)