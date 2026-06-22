import io
import os
import sys
import json
from typing import Dict, List, Tuple 
from langdetect import detect_langs, DetectorFactory, LangDetectException

# set seed for consistent language detection results
DetectorFactory.seed = 0 

# minimum confidence threshold for language detection (0.0 to 1.0)
# Higher threshold (0.9) helps filter false positives on technical documents with codes/numbers
CONFIDENCE_THRESHOLD = 0.9

if __package__:
    from ...logging_utils import LogLevel, configure_json_logging, log
else:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
    from app.logging_utils import LogLevel, configure_json_logging, log

# Load language names mapping from JSON file
def _load_language_names() -> Dict[str, str]:
    """Load language code to language name mapping from JSON file"""
    try:
        language_names_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '../../../language_names.json')
        )
        with open(language_names_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(
            type=LogLevel.ERROR,
            message={
                "message": "Failed to load language names mapping",
                "error": str(e)
            }
        )
        return {}

LANGUAGE_NAMES = _load_language_names()


def detect_language(text: str, min_text_length: int = 50, confidence_threshold: float = CONFIDENCE_THRESHOLD) -> str:
    """
    Detect the language of the given text content

    Args:
        text (str): The text content to analyze
        min_text_length: Minimum text length for detection (default to 50)
        confidence_threshold: Minimum confidence score (0.0-1.0) required for detection

    Returns:
        str: Language name (eg: English, French, German) defaults to English if confidence score is below threshold if detection fails
    """
    if not text or not isinstance(text, str):
        return "English"
    
    cleaned_text = text.strip()
    if len(cleaned_text) < min_text_length:
        return "English"

    try: 
        detected_languages = detect_langs(cleaned_text)

        if not detected_languages:
            return "English"
        
        # get the top detection language
        top_detection = detected_languages[0]
        lang_code = top_detection.lang
        confidence = top_detection.prob

        if confidence < confidence_threshold:
            return "English"
        
        language_name = LANGUAGE_NAMES.get(lang_code, None)

        if language_name:
            return language_name 
        else: 
            return "English"
    
    except LangDetectException as e:
        log(
            type=LogLevel.ERROR,
            message = {
                "message":"Unexpected error during language detection",
                "fileline": sys._getframe().f_lineno,
                "message_data": {"error": str(e)},
                "reason": str(e)
            }
        )
        return "English"
    

def detect_language_from_pages(pages_data: list, content_field: str ="content") -> str: 
    """
    Detect language from a list of page data by combining content from multiple pages

    Args:
        pages_data(list): List of page dictionaries containing content
        content_field(str): Nam eof the field containing text content  (default: 'content')

    Returns:
        str: Detected language name, defaults to 'English' if detection fails
    """

    if not pages_data or not isinstance(pages_data, list):
        return "English"
    
    # combine pages from multiple pages (up to first 5 pages for efficiency)
    combined_text = ""
    max_pages_to_check = min(5, len(pages_data))

    for i in range(max_pages_to_check):
        page = pages_data[i]
        if isinstance(page,dict) and content_field in page:
            page_content = page.get(content_field, "")
            if page_content: 
                combined_text += " " + str(page_content)

        
        if len(combined_text) > 1000:
            break 

    return detect_language(combined_text)