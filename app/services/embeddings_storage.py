from typing import Any, Dict, List, TypedDict
import chromadb
from chromadb.api.types import EmbeddingFunction
from app.services.generate_embeddings import get_embedding


DOCUMENT_METADATA_FIELDS = (
    "source_filename",
    "title",
    "author",
    "creation_date",
    "modification_date",
    "total_pages",
    "file_extension",
    "url",
)

class ProcessedDocumentPayload(TypedDict, total=False):
    processed_pages: List[Dict[str, Any]]
    combined_processed_text: str
    confidence_score: float
    metrics: Dict[str, Any]


class BertEmbeddingFunction(EmbeddingFunction[ProcessedDocumentPayload]):
    def __call__(self, input: List[ProcessedDocumentPayload]) -> List[List[float]]:
        embeddings: List[List[float]] = []

        for document in input:
            embedding_payload: ProcessedDocumentPayload
            if isinstance(document, dict):
                embedding_payload = document
            else:
                embedding_payload = {"combined_processed_text": str(document)}

            embedding = get_embedding(
                {"combined_processed_text": embedding_payload.get("combined_processed_text", "")}
            )
            embeddings.append(embedding.astype("float32").tolist())

        return embeddings


embedding_function = BertEmbeddingFunction()

collection_name = "application_documents"
_client = None
_collection = None


def get_chroma_client():
    global _client

    if _client is None:
        _client = chromadb.Client()

    return _client


def get_document_collection():
    global _collection

    if _collection is None:
        client = get_chroma_client()
        _collection = client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    return _collection


def _build_document_metadata(processed_result: ProcessedDocumentPayload) -> Dict[str, Any]:
    processed_pages = processed_result.get("processed_pages") or []
    first_page = processed_pages[0] if processed_pages else {}

    metadata = {
        field: first_page.get(field, "")
        for field in DOCUMENT_METADATA_FIELDS
    }

    if first_page.get("language"):
        metadata["language"] = first_page["language"]

    return metadata


def _build_document_id(processed_result: ProcessedDocumentPayload, fallback_index: int) -> str:
    processed_pages = processed_result.get("processed_pages") or []

    for page in processed_pages:
        page_id = page.get("id")
        if page_id:
            return str(page_id)

    first_page = processed_pages[0] if processed_pages else {}
    source_filename = first_page.get("source_filename") or first_page.get("title")
    if source_filename:
        return str(source_filename)

    return f"document-{fallback_index}"


def store_processed_documents(preprocessed_results: Any) -> List[str]:
    if isinstance(preprocessed_results, dict):
        results_to_store = [preprocessed_results]
    elif isinstance(preprocessed_results, list):
        results_to_store = [result for result in preprocessed_results if isinstance(result, dict)]
    else:
        results_to_store = []

    if not results_to_store:
        return []

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, Any]] = []
    embeddings: List[List[float]] = []

    for index, processed_result in enumerate(results_to_store, start=1):
        combined_text = processed_result.get("combined_processed_text", "")
        if not isinstance(combined_text, str):
            combined_text = str(combined_text)

        combined_text = combined_text.strip()
        if not combined_text:
            continue

        ids.append(_build_document_id(processed_result, index))
        documents.append(combined_text)
        metadatas.append(_build_document_metadata(processed_result))

        existing_embedding = processed_result.get("embeddings")
        if isinstance(existing_embedding, list) and existing_embedding:
            embeddings.append(existing_embedding)
        else:
            embeddings.append(embedding_function([processed_result])[0])

    if not ids:
        return []

    collection = get_document_collection()
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return ids


def search_documents_by_query(
    query_text: str,
    n_results: int = 5,
) -> Dict[str, Any]:
    """
    Search for documents in the collection based on a user query string.
    
    Args:
        query_text: The user's search query as a string
        n_results: Number of results to return (default: 5)
    
    Returns:
        A dictionary containing search results with documents and metadata
    """
    if not query_text or not isinstance(query_text, str):
        return {
            "ids": [],
            "documents": [],
            "metadatas": [],
            "distances": [],
            "error": "Invalid query text provided"
        }
    
    # Restructure query into minimal payload format similar to ProcessedDocumentPayload
    query_payload: ProcessedDocumentPayload = {
        "combined_processed_text": query_text.strip()
    }
    
    # Generate embedding for the query
    query_embedding = embedding_function([query_payload])[0]
    
    # Query the collection
    collection = get_document_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    return {
        "ids": results.get("ids", [[]])[0] if results.get("ids") else [],
        "documents": results.get("documents", [[]])[0] if results.get("documents") else [],
        "metadatas": results.get("metadatas", [[]])[0] if results.get("metadatas") else [],
        "distances": results.get("distances", [[]])[0] if results.get("distances") else [],
    }
