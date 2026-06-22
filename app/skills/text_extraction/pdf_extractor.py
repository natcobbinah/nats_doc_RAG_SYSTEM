import io
import os
import shutil
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
from ocr_handler import OcrHandler

import  fitz

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromPdf(IDocumentHandler):
    def __init__(self, ocr_handler):
        self.ocr_hanlder = ocr_handler
        configure_json_logging()

    def _process_pdf_page(self, args):
        pdf_document, page_num, blob_name = args 
        page = pdf_document.load_page(page_num)
        text = page.get_text("text").strip()

        return page_num, text 
    
    def extract_content_from_document(self, stream, blob_name, source_url) -> List[Dict]:
        """
        Extracts texts from a PDF, uses OCR if necessary and anonymizes content
        """
        pages_data = []
        try:
            pdf_bytes = stream.read()
            pdf_stream_for_meta = io.BytesIO(pdf_bytes)
            pdf_document = fitz.open(stream=pdf_stream_for_meta, filetype='pdf')

            if not self._is_pdf_valid(pdf_bytes, blob_name):
                return self._extract_with_fallback(pdf_bytes, blob_name, source_url)
            
            pdf_document = None 
            try:
                pdf_document = fitz.open(stream=io.BytesIO(pdf_bytes), filetype='pdf')
            except Exception as e:
                log(
                    type=LogLevel.ERROR,
                    message = {
                        "message":f"Failed to open with pymupdf, {blob_name}",
                        "fileline": sys._getframe().f_lineno,
                        "message_data": {"error": str(e)},
                        "reason": str(e)
                    }
                )
                return self._extract_with_fallback(pdf_bytes, blob_name, source_url)
            
            # additional check - if document opened but has issues, use fallback
            try:
                total_pages = pdf_document.page_count
                if total_pages <= 0:
                    pdf_document.close()
                    return self._extract_with_fallback(pdf_bytes, blob_name, source_url)
            except Exception as e:
                if pdf_document:
                    pdf_document.close()
                return self._extract_with_fallback(pdf_bytes, blob_name, source_url)
            

            doc_metadata = {
                "source_filename": blob_name,
                "title": pdf_document.metadata.get("title", "") if pdf_document.metadata else "",
                "author": pdf_document.metadata.get("author", "") if pdf_document.metadata else "",
                "creation_date": pdf_document.metadata.get("creation_date", "") if pdf_document.metadata else "",
                "modification_date": pdf_document.metadata.get("modification_date", "") if pdf_document.metadata else "",
                "total_pages": total_pages,
                "file_extension": "pdf",
                "url": source_url
            }

            # check if OCR handler is available and process document with mixed approach
            use_ocr_handler = False 
            try:
                if self.ocr_hanlder:
                    log(
                        type=LogLevel.INFO,
                        message = {
                            "message":f"Processing document with mixed OCR/text extraction, {blob_name}",
                            "fileline": sys._getframe().f_lineno,
                        }
                    )

                    ocr_pages = self.ocr_hanlder.porcess_mixed_document(
                        io.BytesIO(pdf_bytes), blob_name, content_type="application/pdf"
                    )

                    if ocr_pages and len(ocr_pages) > 0:
                        for index, page in enumerate(ocr_pages, start=1):
                            page.update(doc_metadata)
                            page_number = page.get("page_number", index)
                            page["id"] = sanitize_and_standardize_doc_id(f"{blob_name}-page-{page_number}")
                        
                        pages_data = ocr_pages
                        use_ocr_handler = True 
                    else:
                        log(
                            type=LogLevel.INFO,
                            message = {
                                "message":f"Mixed processing returned no pages, falling back to standard extraction, {blob_name}",
                                "fileline": sys._getframe().f_lineno,
                            }
                        )
            except Exception as e:
                use_ocr_handler = False
                log(
                    type=LogLevel.INFO,
                    message = {
                        "message":f"Mixed processing for OCR failed, {blob_name}",
                        "fileline": sys._getframe().f_lineno,
                    }
                )

            
            if not use_ocr_handler:
                log(
                    type=LogLevel.INFO,
                    message = {
                        "message":f"Standard text extraction, {blob_name}",
                        "fileline": sys._getframe().f_lineno,
                    }
                )

                try:
                    with ThreadPoolExecutor() as executor:
                        futures = [executor.submit(self._process_pdf_page_safe, (pdf_document, i, blob_name, doc_metadata)) for i in range(total_pages)]
                        for future in as_completed(futures):
                            page_result = future.result()
                            if page_result: # only add successful page extractions
                                pages_data.append(page_result)
                    
                    if len(pages_data) < (total_pages * 0.5) and total_pages > 1:
                        log(
                            type=LogLevel.INFO,
                            message = {
                                "message":f"Had too many failed pages, using fallback, {blob_name}",
                                "fileline": sys._getframe().f_lineno,
                            }
                        )
                        pdf_document.close()
                        return self._extract_with_fallback(pdf_bytes, blob_name, source_url)

                
                except Exception as e:
                    pdf_document.close()
                    return self._extract_with_fallback(pdf_bytes, blob_name, source_url)
            pdf_document.close()


        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message = {
                    "message":f"Error processing pdf, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e)
                }
            )

    def _process_pdf_page_safe(self, args):
        """
        Safe page processing with error handling
        """
        pdf_document, page_num, blob_name, doc_metadata = args 
        try:
            page = pdf_document.load_page(page_num)
            text = page.get_text("text").strip()

            return {
                "id": sanitize_and_standardize_doc_id(f"{blob_name}-page-{page_num + 1}"),
                "page_number": page_num + 1, 
                "content": text,
                **doc_metadata
            }

        except (fitz.FileDataError, fitz.EmptyFileError, Exception):
            return None
        
    def _extract_with_fallback(self, pdf_bytes: bytes, blob_name: str, source_url: str) -> List[Dict]:
        """
        Fallback extraction using alternative pdf libraries
        """
        try:
            from pypdf import PdfReader
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))

            pages_data = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text().strip()

                    pages_data.append({
                        "id": sanitize_and_standardize_doc_id(f"{blob_name}-page-{page_num + 1}"),
                        "page_number": page_num + 1, 
                        "content": text, 
                        "source_filename": blob_name,
                        "title": "",
                        "author": "",
                        "creation_date": "",
                        "modification_date":"",
                        "total_pages": len(pdf_reader.pages),
                        "file_extension": "pdf",
                        "url": source_url
                    })
                except Exception as e:
                    continue
            
            return pages_data
        
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message = {
                    "message":f"Error processing pdf, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e)
                }
            )

    def _is_pdf_valid(self, pdf_bytes: bytes, blob_name: str) -> bool:
        """
        Quick validation to detect severely corrupted PDFs before using PyMUPDF processing
        """
        try:
            # basic pdf structure checks
            if len(pdf_bytes) < 1024: # too small to be a valid pdf
                return False 

            # check pdf header
            if not pdf_bytes.startswith(b'%PDF'):
                return False 
            
            # check for EOF marker (should be near the end)
            if b'%%EOF' not in pdf_bytes[-2048]:
                log(
                    type=LogLevel.WARNING,
                    message={
                        "message": f"Missing end of file marker in pdf, {blob_name}",
                        "fileline": sys._getframe().f_lineno,
                        "message_data": {"error": str(e)},
                        "reason": str(e),
                    },
                )
                return False 
            
            # look for signs of severe corruption in the structure
            pdf_str = pdf_bytes.decode('latin1', errors='ignore')

            # check for corrupted cross-reference table indicators
            corruption_indicators = [
                'object out of range',
                'non-page object in page tree',
                'object is not a stream',
                'invalid key in dict'
            ]

            for indicator in corruption_indicators:
                if indicator in pdf_str:
                    log(
                        type=LogLevel.WARNING,
                        message={
                            "message": f"Shows corruption indicator using fallback in pdf, {blob_name}",
                            "fileline": sys._getframe().f_lineno,
                            "message_data": {"error": str(e)},
                            "reason": str(e),
                        },
                    )
                return False
            
            return True

        except Exception as e:
            return False


if __name__ == "__main__":
    ocr_handler = OcrHandler()

    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.pdf")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromPdf(ocr_handler=ocr_handler)
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.pdf",
            source_url=""
        )
        print(result)