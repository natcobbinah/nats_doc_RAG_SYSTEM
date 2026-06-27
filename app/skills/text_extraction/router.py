"""
Document extraction router that delegates to appropriate format specific-extractors
"""
import os 
import sys 
import io
from ocr_handler import OcrHandler
from language_detector import detect_language, detect_language_from_pages
import json

from csv_extractor import TextFromCsv
from epub_extractor import TextFromEpub
from excel_extractor import TextFromExcel
from gdoc_extractor import TextFromGoogleDocShortcut
from html_extractor import TextFromHtml
from image_extractor import TextFromImage
from kpub_extractor import TextFromKpub
from markdown_extractor import TextFromMarkdown
from mobi_extractor import TextFromMobi
from pdf_extractor import TextFromPdf
from powerpoint_extractor import TextFromPowerPoint
from rar_extractor import TextFromRarArchive
from sevenz_extractor import TextFromSevenZipArchive
from txt_extractor import TextFromText
from word_extractor import TextFromDocument
from xml_extractor import TextFromXml
from xps_extractor import TextFromXps
from zip_extractor import TextFromZipArchive
from app.services.generate_embeddings import preprocess_incoming_data, get_embedding
from app.services.embeddings_storage import store_processed_documents, search_documents_by_query
from app.services.google_drive_processor import upload_bytes_to_drive
from app.services.thumbnail_generator import ThumbnailGenerator


from typing import List, Dict 
import psutil
if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
    from ...utils import get_mimetype, extract_filename
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log
    from app.utils import get_mimetype, extract_filename


configure_json_logging()


def log_memory_usage():
    """
    Log the current memory usage for the project
    """
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    memory_used_mb = mem_info.rss / (1024 * 1024)
    log(
        type=LogLevel.ERROR,
        message={
            "message": f"Memory used for processing",
            "fileline": sys._getframe().f_lineno,
            "message_data": {"RSS": memory_used_mb},
        },
    )

# create singleton instances of handlers to avoid repated initialization
_ocr_handler = None 

def get_handlers():
    """
    Get singleton instances of handlers
    """
    global _ocr_handler
    if _ocr_handler is None: 
        _ocr_handler = OcrHandler()

    return _ocr_handler


def extract_text_and_metadata(stream: io.BytesIO, blob_name: str, source_url:str ) -> List[Dict]:
    _, ext  = os.path.splitext(blob_name.lower())
    ext = ext.lstrip(".")

    image_extensions = ["png", "jpg", "jpeg", "bmp", "tiff"]

    # get singleton handler instances
    _ocr_handler = get_handlers() 

    extraction_functions = {
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
        "pdf": TextFromPdf(ocr_handler=_ocr_handler).extract_content_from_document,
        "pptx": TextFromPowerPoint().extract_content_from_document,
        "ppt": TextFromPowerPoint().extract_content_from_document,
        "rar": TextFromRarArchive().extract_content_from_document,
        "7z": TextFromSevenZipArchive().extract_content_from_document,
        "txt": TextFromText().extract_content_from_document,
        "docx": TextFromDocument().extract_content_from_document,
        "doc": TextFromDocument().extract_content_from_document,
        "xml": TextFromXml().extract_content_from_document,
        "xps": TextFromXps().extract_content_from_document,
        "zip": TextFromZipArchive().extract_content_from_document,
    }

    extract_from_image = TextFromImage(ocr_handler=_ocr_handler)

    for image_ext in image_extensions:
        extraction_functions[image_ext] = extract_from_image.extract_content_from_document

    # log memory usage before processing
    log_memory_usage()

    # extract blob path
    # functionality yet to be written

    if ext in extraction_functions:
        result = extraction_functions[ext](stream,blob_name,source_url)

        # all extractors return pages_data
        if len(result):
            pages_data = result 

            # detect language from document
            detected_language = None 
            if pages_data:
                import time 
                lang_start_time = time.time()
                detected_language = detect_language_from_pages(pages_data)
                lang_elapsed = time.time() - lang_start_time

                log(
                    type=LogLevel.INFO,
                    message={
                        "message": "language extraction duration",
                        "fileline": sys._getframe().f_lineno,
                        "message_data": {"duration_seconds": lang_elapsed, "detected_language": detected_language},
                    },
                )
            
            for item in pages_data:
                item["language"] = detected_language

    return pages_data


if __name__ == "__main__":

    documents = [
        "examples/aroundtheworld.mobi",
        "examples/PCA_PRA_final.docx",
        "examples/diapo.pptx",
    ]

    thumbnail_generator = ThumbnailGenerator()

    for doc_file_path in documents:
        dummy_file_path = os.path.join(os.path.dirname(__file__), doc_file_path)
        with open(dummy_file_path, "rb") as file_stream:
            file_bytes = file_stream.read()
            result = extract_text_and_metadata(
                stream=io.BytesIO(file_bytes),
                blob_name=extract_filename(doc_file_path),
                source_url=""
            )

            # preprocess incoming data
            preprocessed_results= preprocess_incoming_data(result)

            # generating embeddings of preporocessed incoming data 
            embeddings = get_embedding(preprocessed_results)

            # extend preprocessed data to including processed embedding values
            preprocessed_results.update({"embeddings": embeddings.tolist()})
            
            # store file in google drive folder so it can be previewed in the frontend by accessing its url
            upload_to_drive_response = upload_bytes_to_drive(
                file_bytes=file_bytes,
                filename=extract_filename(doc_file_path),
                mime_type=get_mimetype(doc_file_path),
                folder_name="RAG_documents"
            )

            # update the url field of the preprocessed data
            if not upload_to_drive_response:
                print("failed to upload to google drive")
            else:
                generated_url_after_upload_to_drive = upload_to_drive_response.get('url')
                preprocessed_results.update({"url": generated_url_after_upload_to_drive})

                # generate and upload a thumbnail for the uploaded document
                thumbnail_url = thumbnail_generator.generate_thumbnail(
                    file_content=file_bytes,
                    document_id=upload_to_drive_response.get("id", ""),
                    filename=extract_filename(doc_file_path),
                )

                if thumbnail_url:
                    preprocessed_results.update({"thumbnail_url": thumbnail_url})

            # store in vector database
            store_processed_documents(preprocessed_results)

            with open('combined_docs.json', 'a+') as output:
                output.write(json.dumps(preprocessed_results))

        # query and and search through the document
        query = "What is an escooter"
        results = search_documents_by_query(query)

        # write results to output
        with open('results_search.json', 'w') as output:
            output.write(json.dumps(results))
        


        


    