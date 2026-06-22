import json
import re
from pathlib import Path
from typing import Any, Dict, List

import numpy as np 
from sklearn.neighbors import NearestNeighbors
from transformers import BertTokenizer, BertModel
import string 
import nltk 
import torch 
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


has_nltk_stopwords = True
has_punktable_english = True
nltk_languages_from_config = []
all_configured_stopwords = set()
lemmatizer = WordNetLemmatizer()

LANGUAGE_NAMES_PATH = Path(__file__).resolve().parents[2] / "language_names.json"

_LANGUAGE_NAME_ALIASES = {
    "slovenian": "slovene",
    "chinese simplified": "chinese",
    "chinese traditional": "chinese",
}


def _normalize_language_name(language_name: str) -> str:
    # Remove optional labels in parentheses, e.g., "Chinese (Simplified)".
    normalized_name = re.sub(r"\s*\(.*?\)", "", language_name)
    return normalized_name.strip().lower()


# Check whether NLTK resources are already installed and download only when missing.
try:
    try:
        nltk.data.find('corpora/stopwords')
        print("NLTK stopwords already available")
    except LookupError:
        has_nltk_stopwords = nltk.download('stopwords')
        if has_nltk_stopwords:
            print("downloaded nltk stopwords successfully")
        else:
            print("unable to download nltk stopwords")

    try:
        nltk.data.find('tokenizers/punkt')
        print("NLTK punkt tokenizer already available")
    except LookupError:
        has_punktable_english = nltk.download('punkt')
        if has_punktable_english:
            print("downloaded nltk punkt tokenizer successfully")
        else:
            print("unable to download nltk punkt tokenizer")

    configured_languages = {}
    if LANGUAGE_NAMES_PATH.exists():
        with open(LANGUAGE_NAMES_PATH, "r", encoding="utf-8") as language_file:
            configured_languages = json.load(language_file)

    available_nltk_languages = set(stopwords.fileids())
    selected_nltk_languages = set()

    for language_code, language_name in configured_languages.items():
        normalized_name = _normalize_language_name(language_name)
        candidate_names = {
            normalized_name,
            _LANGUAGE_NAME_ALIASES.get(normalized_name),
            language_code.lower(),
        }
        candidate_names.discard(None)

        matched_language = next(
            (candidate for candidate in candidate_names if candidate in available_nltk_languages),
            None,
        )

        if matched_language:
            selected_nltk_languages.add(matched_language)

    nltk_languages_from_config = sorted(selected_nltk_languages)

    for language_id in nltk_languages_from_config:
        all_configured_stopwords.update(stopwords.words(language_id))

    print(
        f"Loaded {len(all_configured_stopwords)} unique stopwords "
        f"from {len(nltk_languages_from_config)} NLTK language packs"
    )
except Exception as e:
    print(f"Error checking/downloading NLTK data: {e}")


#1
def preprocess_incoming_data(pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pages data structure
    [
        {
            "id":"",
            "page_number":1,
            "content": "sample content"
            "source_filename":"aroundtheworld.mobi",
            "title":"aroundtheworld.mobi",
            "author":"",
            "creation_date":"",
            "modification_date":"",
            "total_pages":1,
            "file_extension":"mobi",
            "url":"",
            "language":"English"
        }
    ]
    """
    if not isinstance(pages_data, list):
        return {
            "processed_pages": [],
            "combined_processed_text": "",
            "confidence_score": 0.0,
            "metrics": {
                "total_input_pages": 0,
                "valid_page_dicts": 0,
                "pages_with_content": 0,
                "processed_pages": 0,
            },
        }

    stopword_set = all_configured_stopwords if all_configured_stopwords else set(stopwords.words("english"))

    processed_pages: List[Dict[str, Any]] = []
    total_input_pages = len(pages_data)
    valid_page_dicts = 0
    pages_with_content = 0

    for page in pages_data:
        if not isinstance(page, dict):
            continue

        valid_page_dicts += 1
        raw_content = page.get("content", "")

        if raw_content is None:
            raw_content = ""
        if not isinstance(raw_content, str):
            raw_content = str(raw_content)

        normalized_text = raw_content.strip()
        if not normalized_text:
            continue

        pages_with_content += 1
        tokens = word_tokenize(normalized_text.lower())

        # Keep only content-bearing tokens after punctuation/stopword filtering and lemmatization.
        cleaned_tokens = [
            lemmatizer.lemmatize(token)
            for token in tokens
            if token not in stopword_set and token not in string.punctuation
        ]

        processed_text = " ".join(cleaned_tokens)
        enriched_page = dict(page)
        enriched_page["processed_content"] = processed_text
        processed_pages.append(enriched_page)

    combined_processed_text = " ".join(
        page.get("processed_content", "") for page in processed_pages if page.get("processed_content")
    )

    if total_input_pages == 0:
        confidence_score = 0.0
    else:
        validity_ratio = valid_page_dicts / total_input_pages
        content_ratio = pages_with_content / total_input_pages
        # Weighted toward content presence because embeddings depend primarily on usable text.
        confidence_score = round((0.4 * validity_ratio + 0.6 * content_ratio) * 10, 2)

    return {
        "processed_pages": processed_pages,
        "combined_processed_text": combined_processed_text,
        "confidence_score": confidence_score,
        "metrics": {
            "total_input_pages": total_input_pages,
            "valid_page_dicts": valid_page_dicts,
            "pages_with_content": pages_with_content,
            "processed_pages": len(processed_pages),
        },
    }

#2 - Tokenize using  bert-tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

def get_embedding(preprocessed_data):
    # preprocessed data format
    """
    {
    "processed_pages":[
        {
            "id":"",
            "page_number":1,
            "content": "sample data here",
            "source_filename":"aroundtheworld.mobi",
            "title":"aroundtheworld.mobi",
            "author":"",
            "creation_date":"",
            "modification_date":"",
            "total_pages":1,
            "file_extension":"mobi",
            "url":"",
            "language":"English",
            "processed_content": "sample processed content here",
        }
    ],
    "combined_processed_text": "sample combined processed text  from individual pages",
    "confidence_score":10.0,
    "metrics":{
        "total_input_pages":1,
        "valid_page_dicts":1,
        "pages_with_content":1,
        "processed_pages":1
    }
    }
    """
    combined_text = preprocessed_data.get("combined_processed_text", "") if isinstance(preprocessed_data, dict) else ""
    if combined_text is None:
        combined_text = ""
    if not isinstance(combined_text, str):
        combined_text = str(combined_text)

    combined_text = combined_text.strip()
    hidden_size = model.config.hidden_size
    if not combined_text:
        return np.zeros(hidden_size, dtype=np.float32)

    max_sequence_length = int(getattr(model.config, "max_position_embeddings", 512))

    # Split at the word level to avoid encoding the full document in one call.
    # BERT averages ~1.3 subword tokens per English word; 300 words stays safely
    # under the 512-token limit even after [CLS]/[SEP] are added by the tokenizer.
    words = combined_text.split()
    word_chunk_size = 300
    text_chunks = [
        " ".join(words[i:i + word_chunk_size])
        for i in range(0, len(words), word_chunk_size)
    ]

    if not text_chunks:
        return np.zeros(hidden_size, dtype=np.float32)

    chunk_embeddings = []

    # BERT supports sequences up to 512 tokens, so embed long documents chunk-by-chunk.
    with torch.no_grad():
        for text_chunk in text_chunks:
            inputs = tokenizer(
                text_chunk,
                return_tensors="pt",
                truncation=True,
                max_length=max_sequence_length,
            )
            outputs = model(**inputs)

            # Mean-pool token embeddings to get one fixed-size vector per chunk.
            word_embeddings = outputs.last_hidden_state.squeeze(0)
            chunk_embeddings.append(word_embeddings.mean(dim=0))

    sentence_embedding = torch.stack(chunk_embeddings, dim=0).mean(dim=0)
    return sentence_embedding.numpy()
