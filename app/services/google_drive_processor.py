import io
import os
from typing import Dict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "desktop_ragsystem.json")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "token.json")

# Drive write scope is required for creating folders and uploading thumbnails.
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _escape_query_value(value: str) -> str:
  return value.replace("'", "\\'")


def _get_credentials() -> Credentials:
  creds = None

  if os.path.exists(TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
      creds = flow.run_local_server(port=0)

    with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
      token_file.write(creds.to_json())

  return creds


def get_drive_service():
  creds = _get_credentials()
  return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, folder_name: str) -> str:
  safe_folder_name = _escape_query_value(folder_name)
  query = (
    "mimeType='application/vnd.google-apps.folder' "
    f"and name='{safe_folder_name}' and trashed=false"
  )

  response = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
  files = response.get("files", [])
  if files:
    return files[0]["id"]

  folder_metadata = {
    "name": folder_name,
    "mimeType": "application/vnd.google-apps.folder",
  }
  created = service.files().create(body=folder_metadata, fields="id").execute()
  return created["id"]


def build_drive_file_url(file_id: str) -> str:
  return f"https://drive.google.com/file/d/{file_id}/view?usp=drive_link"


def upload_bytes_to_drive(
  *,
  file_bytes: bytes,
  filename: str,
  mime_type: str,
  folder_name: str,
) -> Dict[str, str]:
  try:
    service = get_drive_service()
    folder_id = get_or_create_folder(service, folder_name)

    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    file_metadata = {
      "name": filename,
      "parents": [folder_id],
    }

    created = (
      service.files()
      .create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink",
      )
      .execute()
    )

    file_id = created["id"]

    # Ensure returned URL can be accessed without authentication.
    service.permissions().create(
      fileId=file_id,
      body={"type": "anyone", "role": "reader"},
    ).execute()

    url = created.get("webViewLink") or created.get("webContentLink") or build_drive_file_url(file_id)

    return {
      "id": file_id,
      "name": created.get("name", filename),
      "url": url,
    }
  except HttpError as error:
    raise RuntimeError(f"Google Drive upload failed: {error}") from error