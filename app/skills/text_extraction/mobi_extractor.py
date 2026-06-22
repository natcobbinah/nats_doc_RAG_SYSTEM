import io
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

import mobi
from bs4 import BeautifulSoup

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromMobi(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def _extract_text_from_path(self, content_path: str) -> str:
        with open(content_path, "rb") as file_stream:
            raw = file_stream.read()

        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            html = raw.decode("latin-1", errors="ignore")

        return BeautifulSoup(html, "html.parser").get_text(separator="\n").strip()

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from unencrypted MOBI files."""
        temp_mobi = ""
        unpack_dir = ""
        try:
            stream.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mobi") as temp_file:
                temp_file.write(stream.read())
                temp_mobi = temp_file.name

            unpack_dir, content_path = mobi.extract(temp_mobi)

            if os.path.isdir(content_path):
                html_candidates = list(Path(content_path).rglob("*.html")) + list(Path(content_path).rglob("*.xhtml"))
                content = "\n".join([self._extract_text_from_path(str(path)) for path in html_candidates]).strip()
            else:
                content = self._extract_text_from_path(content_path)

            doc_metadata = {
                "source_filename": blob_name,
                "title": blob_name,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": 1,
                "file_extension": "mobi",
                "url": source_url,
            }

            return [{
                "id": sanitize_and_standardize_doc_id(f"{blob_name}"),
                "page_number": 1,
                "content": content,
                **doc_metadata,
            }]
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from MOBI file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise
        finally:
            if temp_mobi and os.path.exists(temp_mobi):
                os.remove(temp_mobi)
            if unpack_dir and os.path.exists(unpack_dir):
                shutil.rmtree(unpack_dir, ignore_errors=True)

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/aroundtheworld.mobi")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromMobi()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)