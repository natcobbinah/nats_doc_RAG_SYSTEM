import io 
import logging
import os 
import sys 
from I_document_handler import IDocumentHandler
from typing import List, Dict
import openpyxl
from concurrent.futures import ThreadPoolExecutor, as_completed

if __package__:
    from ...logging_utils import configure_json_logging, log, LogLevel
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import configure_json_logging, log, LogLevel
    from app.utils import sanitize_and_standardize_doc_id

class TextFromExcel(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def _process_sheet(self, args):
        sheet, i, blob_name = args 
        text = "\n".join([
            "\t".join([str(cell.value) if cell.value is not None else "" for cell in row])
            for row in sheet.iter_rows()
        ]).strip()
        
        return i, text, sheet.title, blob_name
    
    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from EXCEL, one page per sheet"""
        try:
            wb = openpyxl.load_workbook(stream,data_only=True)
            props = wb.properties
            total_sheets = len(wb.worksheets)

            doc_metadata = {
                "source_filename": "",
                "title": props.title or "",
                "author": props.creator or "",
                "creation_date": props.created.isoformat() if props.created else "",
                "modification_date": props.modified.isoformat() if props.modified else "",
                "total_pages": total_sheets,
                "file_extension": "xlsx",
                "url": source_url
            }

            pages_data = []

            with ThreadPoolExecutor() as executor:
                futures = [executor.submit(self._process_sheet, (wb.worksheets[i], i, blob_name)) for i in range(total_sheets)]

                for future  in as_completed(futures):
                    i, text, title, blob_name = future.result()

                    page_content = {
                        "id": sanitize_and_standardize_doc_id(f"{blob_name}-sheet-{i+1}-{title}"),
                        "page_number": i + 1,
                        "content": text,
                        **doc_metadata
                    }

                    pages_data.append(page_content)

            pages_data = sorted(pages_data, key=lambda x: x["page_number"])

            return pages_data
        except Exception as e:
            log(
                type=LogLevel.ERROR,
                message = {
                    "message":f"Failed to extract  content from  excel file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e)
                }
            )
            raise
        
if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "demo.xlsx")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromExcel()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)