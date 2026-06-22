import io
import os
import shutil
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

import fitz


if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log

OCR_MIN_CHARACTERS_PER_PAGE = 200 # minimum number of characters required to skip OCR for a page
OC_MIN_CHARACTERS_THRESHOLD = 1000 # minimum number of characters required to skip OCR for entire document


class OcrHandler:
    def __init__(self):
        configure_json_logging()
    
    def get_pages_needing_ocr(self, pdf_stream: io.BytesIO) -> dict:
        """
        Analyze each page of a PDF to determine which pages need OCR.
        Returns a dictionary with page analysis results

        Args:
            pdf_stream (io.BytesIO) The pdf stream

        Returns:
            dict: Contains 'needs_ocr' (list of page numbers needing OCR).
            'has_text' (list of page numbers with sufficient text)
            'page_texts' (dict mapping page numbers to their extracted text)
        """

        result = {
            'needs_ocr': [],
            'has_text': [],
            'page_texts': {}
        }

        try:
            pdf_stream.seek(0)
            doc = fitz.open(stream=pdf_stream, filetype='pdf')

            if not len(doc):
                log(
                    type=LogLevel.WARNING,
                    message={
                        "message":"PDF document has no pages",
                        "fileline": sys._getframe().f_lineno,
                        "message_data": {"error": "PDF is empty or corrupted"},
                        "reason": "PDF document contains no pages",
                    },
                )
                return result

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                if text.strip():
                    # count characters excluding whitespace
                    char_count = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

                    if char_count >= OCR_MIN_CHARACTERS_PER_PAGE:
                        result['has_text'].append(page_num + 1)
                        result['page_texts'][page_num + 1] = text 
                    else:
                        result['needs_ocr'].append(page_num + 1)
                else:
                    result['needs_ocr'].append(page_num + 1)
        except Exception as e:
            log(
                type=LogLevel.EXCEPTION,
                message={
                    "message":"Exception occured while analyzing pdf pages",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": "PDF is empty or corrupted"},
                    "reason": "Error analyziing pdf pages",
                },
            )
        
        return result
    

    # kept for backward compatibility
    def document_needs_ocr(self, pdf_stream: io.BytesIO) -> bool:
        """
        Determines if a PDF document needs any OCR processing.
        Returns True if at least one page needs OCR

        Args:
            pdf_stream(io.BytesIO) The pdf stream

        Returns
            bool: True if OCR is necessary, False otherwise
        """
        page_analysis = self.get_pages_needing_ocr(pdf_stream)
        return len(page_analysis['needs_ocr']) > 0
    
    def perform_ocr_on_pages(self, stream: io.BytesIO, blob_name: str, content_type: str, pages_to_ocr: list) -> dict:
        """
        Performs OCR only on specified pages using  free ocr library

        Args:
            stream(io.BytesIO) The document stream (PDF or image)
            blob_name(str) : Document name (for metadata)
            content_type (str): The content type of the stream
            pages_to_ocr(list): List of page numbers (1-indexed) that needs OCR

        Returns:
            dict: Dictionary mapping page_numbers to their OCR'd content
        """
        ocr_results = {}

        if not pages_to_ocr:
            log(
                type=LogLevel.INFO,
                message={
                    "message":"Pages to OCR list is empty",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"pages_to_ocr list is empty"},
                    "reason": "No pages requires OCR",
                },
            )

            return ocr_results
        
        try:
            import pytesseract
            from PIL import Image

            stream.seek(0)
            normalized_content_type = (content_type or "").lower()
            unique_pages = sorted(set(pages_to_ocr))

            if normalized_content_type == "application/pdf" or blob_name.lower().endswith(".pdf"):
                with fitz.open(stream=stream, filetype="pdf") as doc:
                    for page_num in unique_pages:
                        if page_num < 1 or page_num > len(doc):
                            log(
                                type=LogLevel.WARNING,
                                message={
                                    "message": "Invalid page number requested for OCR",
                                    "fileline": sys._getframe().f_lineno,
                                    "message_data": {"page_num": page_num, "total_pages": len(doc)},
                                    "reason": "Requested page is out of range",
                                },
                            )
                            continue

                        # Render with a higher zoom to improve OCR quality.
                        page = doc[page_num - 1]
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        ocr_results[page_num] = pytesseract.image_to_string(image).strip()
            else:
                image = Image.open(stream)
                extracted_text = pytesseract.image_to_string(image).strip()
                for page_num in unique_pages:
                    if page_num == 1:
                        ocr_results[page_num] = extracted_text
                    else:
                        log(
                            type=LogLevel.WARNING,
                            message={
                                "message": "Ignoring non-first page for non-pdf OCR input",
                                "fileline": sys._getframe().f_lineno,
                                "message_data": {"page_num": page_num, "content_type": content_type},
                                "reason": "Image stream has a single page",
                            },
                        )
        except Exception as e:
             log(
                type=LogLevel.INFO,
                message={
                    "message":"Unexpected error occured during ocr processing",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": "Unexpected error in processing ocr",
                },
            )
             
        return ocr_results
    

    def process_mixed_document(
        self, pdf_stream: io.BytesIO, blob_name, content_type: str ="application/pdf"
    ):
        """
        Processes a PDF that may ave mixed scanned and searchable pages
        Extracts texts directly from searchable pages and uses OCR for scanned pages

        Args
            pdf_stream (io.BytesIO) The PDF stream
            blob_name (str): Document name for (metadata)
            content_type (str) The content type (default: application/pdf)

        Returns 
            list: A list of dictionaries containing text and metadata for each page
        """
        results = []

        # analyze which page needs OCR
        page_analysis = self.get_pages_needing_ocr(pdf_stream)

        # perform OCR ON pages which needs it
        ocr_results = {}
        if page_analysis['needs_ocr']:
            ocr_results = self.perform_ocr_on_pages(
                pdf_stream, blob_name,content_type, page_analysis['needs_ocr']
            )

        # reconstrcut full document with all pages
        pdf_stream.seek(0)
        doc = fitz.open(stream=pdf_stream, filetype='pdf')

        for page_num in range(1, len(doc) + 1):
            if page_num in page_analysis['page_texts']:
                # use extracted text from pymupdf
                content = page_analysis['page_texts'][page_num]
                source = 'pymupdf'
            elif page_num in ocr_results:
                # use ocr'd text
                content = ocr_results[page_num]
                source = 'ocr'
            else:
                # empty or failed ocr
                content = ""
                source="empty"

            results.append({
                "id": "",
                "page_number": page_num,
                "content": content, 
                "source_filename": blob_name,
                "source": source
            })
        
        return results

    def perform_ocr(self, stream: io.BytesIO, blob_name: str, content_type: str):
        """
        Performs OCR on a document stream. For PDFs, uses mixed processing
        For images, performs full OCR

        Args:
            stream(io.BytesIO) The document stream (pdf or image)
            blob_name(str) Document name for metadata
            content_type (str) The content type of the stream

        Returns
            list: A list of dictionaries containing texts and metadata
        """
        if content_type == "application/pdf":
            return self.process_mixed_document(stream, blob_name, content_type)
        else:
            # for images, perform full OCR using the original logic
            return self._perform_full_ocr(stream, blob_name, content_type)
        
    
    def _perform_full_ocr(self, stream: io.BytesIO, blob_name: str, content_type: str) -> list: 
        """
        Performs full OCR on entire document (used for images)
        """
        results = []

        try:
            import pytesseract
            from PIL import Image, ImageSequence

            stream.seek(0)
            image = Image.open(stream)

            # Support multi-frame images (for example TIFF) while keeping page-like output.
            frames = list(ImageSequence.Iterator(image))
            if not frames:
                frames = [image]

            for frame_index, frame in enumerate(frames, start=1):
                frame_rgb = frame.convert("RGB")

                # Use a page segmentation mode tuned for block text and retry with default config if needed.
                extracted_text = pytesseract.image_to_string(
                    frame_rgb, config="--oem 3 --psm 6"
                ).strip()
                if not extracted_text:
                    extracted_text = pytesseract.image_to_string(frame_rgb).strip()

                results.append(
                    {
                        "id": "",
                        "page_number": frame_index,
                        "content": extracted_text,
                        "source_filename": blob_name,
                        "source": "ocr",
                    }
                )

            return results
        except Exception as e:
            log(
                type=LogLevel.INFO,
                message={
                    "message": "Unexpected error occured during full ocr processing",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e), "filename": blob_name, "content_type": content_type},
                    "reason": "Unexpected error in full image OCR",
                },
            )


