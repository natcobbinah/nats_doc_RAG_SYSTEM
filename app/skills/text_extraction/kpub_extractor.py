import io
import os
import sys
import tempfile
import zipfile
from typing import Dict, List

from bs4 import BeautifulSoup
from ebooklib import epub

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromKpub(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def _extract_with_epub_reader(self, temp_path: str, blob_name: str, source_url: str) -> List[Dict]:
        book = epub.read_epub(temp_path)
        pages_data = []
        docs = list(book.get_items())
        html_docs = [item for item in docs if item.get_name().endswith((".xhtml", ".html", ".htm"))]

        for i, item in enumerate(html_docs):
            text = BeautifulSoup(item.get_content(), "html.parser").get_text(separator="\n").strip()
            pages_data.append(
                {
                    "id": sanitize_and_standardize_doc_id(f"{blob_name}-page-{i + 1}-{item.get_name()}"),
                    "page_number": i + 1,
                    "entry_name": item.get_name(),
                    "content": text,
                    "source_filename": blob_name,
                    "title": blob_name,
                    "author": "",
                    "creation_date": "",
                    "modification_date": "",
                    "total_pages": len(html_docs),
                    "file_extension": "kpub",
                    "url": source_url,
                }
            )
        return pages_data

    def _extract_with_zip_fallback(self, temp_path: str, blob_name: str, source_url: str) -> List[Dict]:
        pages_data = []
        with zipfile.ZipFile(temp_path) as archive:
            html_names = [
                info.filename
                for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith((".xhtml", ".html", ".htm"))
            ]
            for i, name in enumerate(html_names):
                raw = archive.read(name)
                text = BeautifulSoup(raw, "html.parser").get_text(separator="\n").strip()
                pages_data.append(
                    {
                        "id": sanitize_and_standardize_doc_id(f"{blob_name}-page-{i + 1}-{name}"),
                        "page_number": i + 1,
                        "entry_name": name,
                        "content": text,
                        "source_filename": blob_name,
                        "title": blob_name,
                        "author": "",
                        "creation_date": "",
                        "modification_date": "",
                        "total_pages": len(html_names),
                        "file_extension": "kpub",
                        "url": source_url,
                    }
                )
        return pages_data

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from KPUB/Kobo EPUB-like packages."""
        temp_path = ""
        try:
            stream.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".kpub") as temp_file:
                temp_file.write(stream.read())
                temp_path = temp_file.name

            try:
                pages = self._extract_with_epub_reader(temp_path, blob_name, source_url)
                if pages:
                    return pages
            except Exception:
                pass

            return self._extract_with_zip_fallback(temp_path, blob_name, source_url)
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from KPUB file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.kpub")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromKpub()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)