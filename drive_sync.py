import os
import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """Tạo kết nối tới Google Drive API thông qua Service Account."""
    try:
        # Đọc thông tin Service Account từ st.secrets
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Lỗi xác thực Google Drive: {str(e)}\nVui lòng kiểm tra lại cấu hình gcp_service_account trong Secrets.")
        return None

def get_root_folder_id():
    """Lấy ID của thư mục Data gốc trên Drive từ Secrets."""
    try:
        return st.secrets["DRIVE_FOLDER_ID"]
    except:
        st.error("Chưa cấu hình DRIVE_FOLDER_ID trong Secrets.")
        return None

def find_file_in_drive(service, name, parent_folder_id, is_folder=False):
    """Tìm file hoặc thư mục theo tên trong một thư mục cụ thể."""
    mime_query = " and mimeType='application/vnd.google-apps.folder'" if is_folder else ""
    query = f"name='{name}' and '{parent_folder_id}' in parents and trashed=false{mime_query}"
    
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    if items:
        return items[0]['id']
    return None

def get_or_create_subfolder(service, parent_id, folder_name):
    """Tìm thư mục con theo tên, nếu không có thì tự động tạo mới."""
    folder_id = find_file_in_drive(service, folder_name, parent_id, is_folder=True)
    if folder_id:
        return folder_id
        
    # Tạo thư mục mới nếu chưa có
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')

def upload_file_to_drive(local_file_path, file_name, target_folder_id):
    """Tải file lên một thư mục cụ thể trên Google Drive, ghi đè nếu đã tồn tại."""
    service = get_drive_service()
    if not service:
        return False
        
    try:
        file_id = find_file_in_drive(service, file_name, target_folder_id)
        media = MediaFileUpload(local_file_path, resumable=True)
        
        if file_id:
            # Update existing file
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
        else:
            # Create new file
            file_metadata = {
                'name': file_name,
                'parents': [target_folder_id]
            }
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
        return True
    except Exception as e:
        st.error(f"Lỗi khi upload lên Drive: {str(e)}")
        return False

def download_db_from_drive(local_db_path):
    """Tải file documents.db từ thư mục Data gốc về máy lúc khởi động."""
    service = get_drive_service()
    root_id = get_root_folder_id()
    if not service or not root_id:
        return False
        
    try:
        file_id = find_file_in_drive(service, "documents.db", root_id)
        if not file_id:
            # Nếu chưa có DB trên Drive, upload DB local hiện tại lên gốc
            if os.path.exists(local_db_path):
                upload_file_to_drive(local_db_path, "documents.db", root_id)
            return False
            
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_db_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return True
    except Exception as e:
        return False

def download_file_bytes_from_drive(file_name, dia_phuong):
    """Tìm thư mục địa phương trên Drive, lấy file PDF/Docx dưới dạng bytes."""
    service = get_drive_service()
    root_id = get_root_folder_id()
    if not service or not root_id:
        return None
        
    try:
        # Lấy ID thư mục địa phương
        subfolder_id = get_or_create_subfolder(service, root_id, dia_phuong)
        
        # Lấy ID file tài liệu
        file_id = find_file_in_drive(service, file_name, subfolder_id)
        if not file_id:
            return None
            
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
    except Exception as e:
        st.error(f"Lỗi tải file từ Drive: {str(e)}")
        return None
