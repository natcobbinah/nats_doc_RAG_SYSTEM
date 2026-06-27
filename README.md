# Nats Document RAG System

Nats Document RAG System is a Flask-based Retrieval Augmented Generation stack that:

- extracts text and metadata from many document types,
- generates BERT embeddings,
- indexes documents in Chroma,
- stores source files in Google Drive,
- generates and stores thumbnails in Google Drive,
- and serves a dashboard-style landing page for system overview.

## Current Scope

- Multi-format document extraction under `app/skills/text_extraction`
- Preprocessing and language-aware token cleaning using NLTK
- Embedding generation using `bert-base-uncased` from Hugging Face Transformers
- Chroma vector collection with cosine similarity retrieval
- Google Drive upload service for source files
- Google Drive upload service for generated thumbnails
- Flask app-factory structure with blueprint-based routes

## Architecture

### 1) Web App Layer

- `wsgi.py` is the application entry point (`app = create_app()`)
- `app/__init__.py` builds the Flask app, applies CSRF, registers blueprints, and injects security headers
- `app/routes/routes.py` exposes:
  - `GET /` (landing page)
  - `GET /health` (health probe)

### 2) Extraction Layer

- `app/skills/text_extraction/router.py` dispatches by extension to extractor implementations
- Supported extraction families include:
  - PDF, Office, text, markdown, HTML/XML, archive formats, ebooks, and image OCR paths

### 3) Embedding + Vector Store Layer

- `app/services/generate_embeddings.py`
  - preprocesses page content
  - loads BERT tokenizer/model
  - performs chunked embedding for long text
- `app/services/embeddings_storage.py`
  - persists embeddings/documents/metadata to Chroma
  - includes metadata fields such as `url` and `thumbnail_url`
  - supports semantic search via `search_documents_by_query`

### 4) Drive Storage + Thumbnails

- `app/services/google_drive_processor.py`
  - authenticates with OAuth token flow
  - creates folders on demand
  - uploads bytes and returns shareable URLs
- `app/services/thumbnail_generator.py`
  - generates filetype-specific thumbnails:
    - PDF via PyMuPDF
    - image files via Pillow
    - generic thumbnails for other formats
  - uploads thumbnails to Google Drive and returns `thumbnail_url`

## Project Structure

```text
nats_doc_rag_system/
├── app/
│   ├── __init__.py
│   ├── app_env_config.py
│   ├── extensions.py
│   ├── logging_utils.py
│   ├── routes/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── services/
│   │   ├── embeddings_storage.py
│   │   ├── generate_embeddings.py
│   │   ├── google_drive_processor.py
│   │   ├── thumbnail_generator.py
│   │   └── google_drive_folder_periodic_ingestion.py
│   ├── skills/text_extraction/
│   │   ├── router.py
│   │   └── *_extractor.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── thumbnail_config.py
│   ├── templates/
│   │   └── index.html
│   └── utils/
├── tests/
├── wsgi.py
├── requirements.txt
├── desktop_ragsystem.json
├── language_names.json
└── README.md
```

## Requirements

- Python 3.12+
- Virtual environment recommended
- Google API OAuth credentials file at project root:
  - `desktop_ragsystem.json`

## Setup

1. Create and activate virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Set environment variables (example values).

```bash
set FLASK_APP=wsgi.py
set FLASK_ENV=development
set FLASK_DEBUG=1
set FLASK_SECRET=change-me
```

4. Start the Flask app.

```bash
flask run
```

Health check:

```bash
curl http://127.0.0.1:5000/health
```

## Running the Extraction + RAG Flow (local script)

The script entry in `app/skills/text_extraction/router.py` demonstrates end-to-end flow:

1. extract text and metadata
2. preprocess and embed
3. upload source file to Drive
4. generate and upload thumbnail
5. store vectors and metadata in Chroma
6. query indexed data

Run from the text extraction directory:

```bash
cd app\skills\text_extraction
python router.py
```

Expected local outputs:

- `combined_docs.json`
- `results_search.json`

## Core Metadata Stored per Document

- `source_filename`
- `title`
- `author`
- `creation_date`
- `modification_date`
- `total_pages`
- `file_extension`
- `url`
- `thumbnail_url`
- `language` (when detected)

## Testing

```bash
pytest
```

Note: existing tests are from an earlier app version and may need alignment with the current Nats RAG landing page text.

## Troubleshooting

### ImportError while importing wsgi

If you see an import failure when running plain `python`, ensure you are using the project venv interpreter:

```bash
.venv\Scripts\python -c "import wsgi; print('wsgi import ok')"
```

On Windows, `python` may resolve to the Microsoft Store alias if the venv is not active.

### Google Drive authentication/upload issues

- Ensure `desktop_ragsystem.json` exists at repository root
- First run may open OAuth consent flow and create `app/services/token.json`
- Confirm Drive scope is enabled in credentials

### Missing thumbnails in metadata

- Verify file extension is supported in `app/config/thumbnail_config.py`
- Verify thumbnail upload folder permissions in Google Drive

## Deployment Notes

- `wsgi.py`, `Procfile`, and `runtime.txt` are present for process-based deployment targets
- Keep secrets and OAuth credentials out of source control

## License

MIT
