import io
import os
import shutil
import tempfile
import sys
from typing import Callable, Dict, List

import rarfile

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromRarArchive(IDocumentHandler):
    def __init__(self):
        self._handler_map = None
        configure_json_logging()

    @staticmethod
    def _safe_decode(raw: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore")

    def _extract_plain_text_entry(self, content_bytes: bytes, page_number: int, entry_name: str, blob_name: str) -> Dict:
        return {
            "id": sanitize_and_standardize_doc_id(f"{blob_name}-entry-{entry_name}-page-{page_number}"),
            "page_number": page_number,
            "entry_name": entry_name,
            "content": self._safe_decode(content_bytes).strip(),
        }

    def _get_handler_map(self) -> Dict[str, Callable]:
        if self._handler_map is not None:
            return self._handler_map

        from csv_extractor import TextFromCsv
        from epub_extractor import TextFromEpub
        from excel_extractor import TextFromExcel
        from gdoc_extractor import TextFromGoogleDocShortcut
        from html_extractor import TextFromHtml
        from image_extractor import TextFromImage
        from kpub_extractor import TextFromKpub
        from markdown_extractor import TextFromMarkdown
        from mobi_extractor import TextFromMobi
        from ocr_handler import OcrHandler
        from pdf_extractor import TextFromPdf
        from powerpoint_extractor import TextFromPowerPoint
        from sevenz_extractor import TextFromSevenZipArchive
        from txt_extractor import TextFromText
        from word_extractor import TextFromDocument
        from xml_extractor import TextFromXml
        from xps_extractor import TextFromXps
        from zip_extractor import TextFromZipArchive

        ocr_handler = OcrHandler()
        extract_from_image = TextFromImage(ocr_handler=ocr_handler)

        handler_map = {
            "csv": TextFromCsv().extract_content_from_document,
            "epub": TextFromEpub().extract_content_from_document,
            "xlsx": TextFromExcel().extract_content_from_document,
            "xls": TextFromExcel().extract_content_from_document,
            "gdoc": TextFromGoogleDocShortcut().extract_content_from_document,
            "html": TextFromHtml().extract_content_from_document,
            "htm": TextFromHtml().extract_content_from_document,
            "kpub": TextFromKpub().extract_content_from_document,
            "md": TextFromMarkdown().extract_content_from_document,
            "mobi": TextFromMobi().extract_content_from_document,
            "pdf": TextFromPdf(ocr_handler=ocr_handler).extract_content_from_document,
            "pptx": TextFromPowerPoint().extract_content_from_document,
            "ppt": TextFromPowerPoint().extract_content_from_document,
            "rar": self.extract_content_from_document,
            "7z": TextFromSevenZipArchive().extract_content_from_document,
            "txt": TextFromText().extract_content_from_document,
            "docx": TextFromDocument().extract_content_from_document,
            "doc": TextFromDocument().extract_content_from_document,
            "xml": TextFromXml().extract_content_from_document,
            "xps": TextFromXps().extract_content_from_document,
            "zip": TextFromZipArchive().extract_content_from_document,
        }

        for image_ext in ("png", "jpg", "jpeg", "bmp", "tiff"):
            handler_map[image_ext] = extract_from_image.extract_content_from_document

        self._handler_map = handler_map
        return self._handler_map

    def _extract_entry_with_registered_handler(
        self, content_bytes: bytes, entry_name: str, source_url: str
    ) -> List[Dict]:
        ext = os.path.splitext(entry_name.lower())[1].lstrip(".")
        handler = self._get_handler_map().get(ext)

        if not handler:
            return [self._extract_plain_text_entry(content_bytes, 1, entry_name, os.path.basename(entry_name))]

        try:
            extracted = handler(io.BytesIO(content_bytes), os.path.basename(entry_name), source_url)
            if not extracted:
                return [self._extract_plain_text_entry(content_bytes, 1, entry_name, os.path.basename(entry_name))]
            return extracted
        except Exception as e:
            log(
                type=LogLevel.WARNING,
                message={
                    "message": f"Failed to extract nested entry with typed extractor: {entry_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e), "entry_name": entry_name},
                    "reason": "Falling back to plain text decode",
                },
            )
            return [self._extract_plain_text_entry(content_bytes, 1, entry_name, os.path.basename(entry_name))]

    @staticmethod
    def _configure_rar_backend() -> None:
        # rarfile requires an external tool (for example unrar/unar/7z) for most archives.
        if getattr(rarfile, "UNRAR_TOOL", None) and shutil.which(rarfile.UNRAR_TOOL):
            return

        candidates = [
            ("UNRAR_TOOL", "unrar"),
            ("UNAR_TOOL", "unar"),
            ("BSDTAR_TOOL", "bsdtar"),
            ("SEVENZIP_TOOL", "7z"),
        ]

        for attr_name, executable in candidates:
            resolved = shutil.which(executable)
            if resolved:
                setattr(rarfile, attr_name, resolved)
                return

        # Common Windows install locations when the tool is not on PATH.
        windows_candidates = [
            ("UNRAR_TOOL", r"C:\Program Files\WinRAR\UnRAR.exe"),
            ("UNRAR_TOOL", r"C:\Program Files (x86)\WinRAR\UnRAR.exe"),
            ("SEVENZIP_TOOL", r"C:\Program Files\7-Zip\7z.exe"),
            ("SEVENZIP_TOOL", r"C:\Program Files (x86)\7-Zip\7z.exe"),
        ]

        for attr_name, path in windows_candidates:
            if os.path.exists(path):
                setattr(rarfile, attr_name, path)
                return

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text from RAR entries and delegate to typed extractors per entry."""
        temp_path = ""
        try:
            self._configure_rar_backend()
            stream.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".rar") as temp_file:
                temp_file.write(stream.read())
                temp_path = temp_file.name

            with rarfile.RarFile(temp_path) as archive:
                members = [m for m in archive.infolist() if not m.isdir()]

                doc_metadata = {
                    "source_filename": blob_name,
                    "title": blob_name,
                    "author": "",
                    "creation_date": "",
                    "modification_date": "",
                    "total_pages": 0,
                    "file_extension": "rar",
                    "url": source_url,
                }

                pages_data: List[Dict] = []
                running_page_number = 1

                for member in members:
                    try:
                        data = archive.read(member.filename)
                    except rarfile.RarCannotExec as e:
                        log(
                            type=LogLevel.ERROR,
                            message={
                                "message": "RAR extraction tool is not available",
                                "fileline": sys._getframe().f_lineno,
                                "message_data": {
                                    "error": str(e),
                                    "entry_name": member.filename,
                                    "hint": "Install WinRAR/UnRAR or 7-Zip, or add the tool to PATH",
                                },
                                "reason": "rarfile needs an external backend tool",
                            },
                        )
                        raise RuntimeError(
                            "Cannot extract RAR entries because no backend tool is available. "
                            "Install WinRAR/UnRAR or 7-Zip and ensure it is on PATH."
                        ) from e

                    extracted_pages = self._extract_entry_with_registered_handler(
                        data, member.filename, source_url
                    )

                    for extracted_page in extracted_pages:
                        merged_page = {
                            **extracted_page,
                            **doc_metadata,
                            "id": sanitize_and_standardize_doc_id(
                                f"{blob_name}-entry-{member.filename}-page-{running_page_number}"
                            ),
                            "page_number": running_page_number,
                            "entry_name": member.filename,
                            "entry_page_number": extracted_page.get("page_number", 1),
                            "contained_source_filename": extracted_page.get(
                                "source_filename", os.path.basename(member.filename)
                            ),
                            "contained_file_extension": extracted_page.get(
                                "file_extension", os.path.splitext(member.filename)[1].lstrip(".")
                            ),
                        }
                        pages_data.append(merged_page)
                        running_page_number += 1

                for item in pages_data:
                    item["total_pages"] = len(pages_data)

                return pages_data
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message={
                    "message": f"Failed to extract content from RAR archive, {blob_name}",
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
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/compressed.rar")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromRarArchive()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.rar",
            source_url=""
        )
        print(result)