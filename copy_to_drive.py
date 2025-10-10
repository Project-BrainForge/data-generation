import os
from googleapiclient.http import MediaFileUpload


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


