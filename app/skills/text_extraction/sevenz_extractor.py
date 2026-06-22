import io
import os
import shutil
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import py7zr

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromSevenZipArchive(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    @staticmethod
    def _safe_decode(raw: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    def _extract_entry(self, args: Tuple[Path, int, str, str]) -> Dict:
        file_path, page_number, entry_name, blob_name = args
        with open(file_path, "rb") as f:
            data = f.read()

        return {
            "id": sanitize_and_standardize_doc_id(f"{blob_name}-entry-{entry_name}-page-{page_number}"),
            "page_number": page_number,
            "entry_name": entry_name,
            "content": self._safe_decode(data).strip(),
        }

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text from 7Z archive entries."""
        temp_archive = ""
        extract_dir = ""
        try:
            stream.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".7z") as temp_file:
                temp_file.write(stream.read())
                temp_archive = temp_file.name

            extract_dir = tempfile.mkdtemp(prefix="seven_zip_extract_")
            with py7zr.SevenZipFile(temp_archive, mode="r") as archive:
                archive.extractall(path=extract_dir)

            extracted_files = [
                path
                for path in Path(extract_dir).rglob("*")
                if path.is_file()
            ]

            doc_metadata = {
                "source_filename": blob_name,
                "title": blob_name,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": len(extracted_files),
                "file_extension": "7z",
                "url": source_url,
            }

            pages_data: List[Dict] = []
            with ThreadPoolExecutor() as executor:
                futures = []
                for i, file_path in enumerate(extracted_files):
                    entry_name = str(file_path.relative_to(extract_dir)).replace("\\", "/")
                    futures.append(executor.submit(self._extract_entry, (file_path, i + 1, entry_name, blob_name)))

                for future in as_completed(futures):
                    pages_data.append({**future.result(), **doc_metadata})

            return sorted(pages_data, key=lambda item: int(item["page_number"]))
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from 7Z archive, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise
        finally:
            if temp_archive and os.path.exists(temp_archive):
                os.remove(temp_archive)
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.7z")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromSevenZipArchive()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)
