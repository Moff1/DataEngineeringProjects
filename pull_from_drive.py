import os
import json
import io
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ===================== CONFIG =====================
fileswanted = [
    'StreamingHistory_podcast_0.json', 'StreamingHistory_audiobook_0.json',
    'StreamingHistory_music_5.json', 'StreamingHistory_music_4.json',
    'StreamingHistory_music_3.json', 'StreamingHistory_music_2.json',
    'StreamingHistory_music_1.json', 'StreamingHistory_music_0.json',
    'Wrapped2024.json', 'YourSoundCapsule.json', 'YourLibrary.json', 'Playlist1.json'
]

SAVE_FOLDER = './gdrivedownload'   # Relative path - works in GitHub Actions
# ================================================

def authenticate_gdrive():
    """Authenticate using credentials from GitHub Secrets"""
    creds_json = os.getenv('GDRIVE_CREDENTIALS')
    if not creds_json:
        raise ValueError("GDRIVE_CREDENTIALS environment variable not found!")

    credentials = service_account.Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=['https://www.googleapis.com/auth/drive']
    )
    
    print("✅ Successfully authenticated with Google Drive service account")
    return build('drive', 'v3', credentials=credentials)


def get_folder_id(service, folder_name):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if not items:
        print(f"❌ No folder found with name: {folder_name}")
        return None
    print(f"✅ Found folder '{folder_name}' with ID: {items[0]['id']}")
    return items[0]['id']


def list_files_in_folder(service, folder_id):
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        pageSize=100
    ).execute()
    return results.get('files', [])


def download_and_save(service, file_id, file_name, selected_files):
    """Download file and save if it's in the selected list"""
    request = service.files().get_media(fileId=file_id)
    file_buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(file_buffer, request)
    
    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Downloading {file_name}: {int(status.progress() * 100)}%")

    file_buffer.seek(0)

    if file_name in selected_files:
        os.makedirs(SAVE_FOLDER, exist_ok=True)
        file_path = os.path.join(SAVE_FOLDER, file_name)
        
        with open(file_path, 'wb') as f:
            f.write(file_buffer.read())
        
        print(f"✅ Saved: {file_name} → {file_path}")
        file_buffer.seek(0)  # Reset for potential further use

    return file_buffer


def run_pipeline(folder_name, selected_files):
    """Main pipeline"""
    print(f"🚀 Starting Google Drive sync - Folder: {folder_name}")
    
    service = authenticate_gdrive()
    folder_id = get_folder_id(service, folder_name)
    
    if not folder_id:
        return None

    files = list_files_in_folder(service, folder_id)
    print(f"Found {len(files)} files in folder")

    for file in files:
        print(f"\nProcessing: {file['name']}")
        download_and_save(service, file['id'], file['name'], selected_files)

    print("\n✅ Pipeline completed successfully!")
    return True


# ===================== MAIN EXECUTION =====================
if __name__ == "__main__":
    year_of_music = str(datetime.now().year - 1)
    folder_name = f'my_spotify_data_{year_of_music}'
    
    try:
        run_pipeline(folder_name, fileswanted)
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        raise
