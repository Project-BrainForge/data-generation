import os
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from googleapiclient.discovery import build


def upload_file_to_drive(file_path, parent_folder_id, drive_service):
    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [parent_folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    print(f"📁 Uploaded: {file_path}")
    return uploaded.get('id')

def upload_folder_to_drive(local_folder, parent_folder_id, drive_service):
    folder_name = os.path.basename(local_folder)
    
    # Create a new folder in Drive
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    new_folder_id = folder.get('id')
    print(f"📂 Created folder: {folder_name}")

    # Loop through items
    for item in os.listdir(local_folder):
        item_path = os.path.join(local_folder, item)
        if os.path.isfile(item_path):
            upload_file_to_drive(item_path, new_folder_id, drive_service)
        elif os.path.isdir(item_path):
            upload_folder_to_drive(item_path, new_folder_id, drive_service)
    return new_folder_id


def create_drive_service():
    # Load individual environment variables
    service_account_info = {
        "type": os.getenv("SERVICE_ACCOUNT_TYPE"),
        "project_id": os.getenv("SERVICE_ACCOUNT_PROJECT_ID"),
        "private_key_id": os.getenv("SERVICE_ACCOUNT_PRIVATE_KEY_ID"),
        "private_key": os.getenv("SERVICE_ACCOUNT_PRIVATE_KEY"),
        "client_email": os.getenv("SERVICE_ACCOUNT_CLIENT_EMAIL"),
        "client_id": os.getenv("SERVICE_ACCOUNT_CLIENT_ID"),
        "auth_uri": os.getenv("SERVICE_ACCOUNT_AUTH_URI"),
        "token_uri": os.getenv("SERVICE_ACCOUNT_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("SERVICE_ACCOUNT_CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("SERVICE_ACCOUNT_UNIVERSE_DOMAIN")
    }

    # Check if all required fields are present
    required_fields = ["type", "project_id", "private_key", "client_email"]
    missing_fields = [
        field for field in required_fields if not service_account_info[field]]

    if missing_fields:
        raise ValueError(
            f"❌ Missing required environment variables: {missing_fields}")

    # Create service account credentials
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"]
    )

    # Build the Drive API service
    drive_service = build('drive', 'v3', credentials=creds)
    print("✅ Google Drive service created successfully!")
    return drive_service
