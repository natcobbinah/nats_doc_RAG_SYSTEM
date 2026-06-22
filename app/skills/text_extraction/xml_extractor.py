import io
import os
import sys
from typing import Dict, List

from lxml import etree

from I_document_handler import IDocumentHandler

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import sanitize_and_standardize_doc_id
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import sanitize_and_standardize_doc_id


class TextFromXml(IDocumentHandler):
    def __init__(self):
        configure_json_logging()

    def extract_content_from_document(self, stream: io.BytesIO, blob_name: str, source_url: str) -> List[Dict]:
        """Extract text and metadata from XML."""
        try:
            stream.seek(0)
            parser = etree.XMLParser(recover=True)
            root = etree.fromstring(stream.read(), parser=parser)
            text_nodes = [node.strip() for node in root.xpath("//text()") if node and node.strip()]
            content = "\n".join(text_nodes)

            doc_metadata = {
                "source_filename": blob_name,
                "title": root.tag if root is not None else blob_name,
                "author": "",
                "creation_date": "",
                "modification_date": "",
                "total_pages": 1,
                "file_extension": "xml",
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
                    "message": f"Failed to extract content from XML file, {blob_name}",
                    "fileline": sys._getframe().f_lineno,
                    "message_data": {"error": str(e)},
                    "reason": str(e),
                },
            )
            raise

if __name__ == "__main__":
    dummy_file_path = os.path.join(os.path.dirname(__file__), "examples/sample.xml")
    with open(dummy_file_path, "rb") as file_stream:
        tft = TextFromXml()
        result = tft.extract_content_from_document(
            stream=io.BytesIO(file_stream.read()),
            blob_name="demo.excel",
            source_url=""
        )
        print(result)

