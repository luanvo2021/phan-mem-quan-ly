# Hướng Dẫn Triển Khai Phần Mềm Quản Lý Văn Bản Lên Web (Google Drive Storage)

Dự án này sử dụng **Streamlit** làm giao diện Web và **Google Drive** làm nơi lưu trữ Database (`documents.db`) cùng các file tài liệu. Hệ thống sẽ tự động tạo thư mục con (VD: Cần Thơ, Đà Nẵng) bên trong thư mục Data gốc của bạn để lưu file.

## Bước 1: Lấy mã Google Service Account
Để web Streamlit có quyền đẩy file vào Google Drive, bạn phải lấy một "chìa khóa" dạng file JSON.
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/).
2. Đăng nhập và tạo một Project mới (Ví dụ: `VanBanApp`). Bấm **Create**.
3. Tại thanh tìm kiếm trên cùng của Google Cloud, gõ **"Google Drive API"** -> Chọn kết quả đầu tiên -> Bấm **Enable**.
4. Tiếp tục lên thanh tìm kiếm, gõ **"Service Accounts"** -> Chọn kết quả.
5. Bấm **+ CREATE SERVICE ACCOUNT**.
   - **Tên**: Ghi tùy ý (VD: `bot-drive`). Bấm Create and Continue -> Done.
6. Bạn sẽ nhìn thấy một địa chỉ email vừa được tạo ra (có đuôi dạng `@...iam.gserviceaccount.com`). **Hãy copy địa chỉ email này.**
7. Bấm vào dấu 3 chấm ở dòng đó -> Chọn **Manage keys**.
8. Bấm **ADD KEY** -> **Create new key** -> Chọn **JSON** -> Bấm **Create**.
9. Sẽ có một file `.json` tải về máy tính của bạn. Hãy mở file đó bằng Notepad, bạn sẽ copy toàn bộ nội dung bên trong ở bước sau.

## Bước 2: Cấp quyền thư mục Google Drive
1. Mở **Google Drive** của bạn. Tạo một thư mục mới (hoặc dùng thư mục Data hiện tại của bạn).
2. Nhấp chuột phải vào thư mục đó -> Chọn **Chia sẻ (Share)**.
3. Dán **địa chỉ email Service Account** (bạn đã copy ở Bước 1) vào ô mời người mới. Chú ý cấp cho nó quyền **Người chỉnh sửa (Editor)** -> Bấm **Gửi**.
4. Nhấp đúp mở thư mục đó ra. Nhìn lên thanh địa chỉ trang web (URL) trên trình duyệt, bạn sẽ thấy 1 đoạn mã dài. 
   *(VD: `https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ`) -> Đoạn `1aBcDeFgHiJkLmNoPqRsTuVwXyZ` chính là **Folder ID**. Hãy copy nó.*

## Bước 3: Triển khai Streamlit & Gắn khóa
1. Truy cập https://share.streamlit.io/.
2. Kéo toàn bộ code `phan_mem_quan_ly` này thả lên một kho GitHub Public của bạn (Không dùng GitHub làm kho lưu file nữa, nhưng Streamlit vẫn cần lấy code giao diện từ GitHub).
3. Tại Streamlit, bấm **New app**, chọn Repository đó, nhập `app_streamlit.py` vào mục Main file path.
4. Bấm **Advanced settings...**. Ở phần **Secrets**, bạn dán nội dung sau vào:
   ```toml
   DRIVE_FOLDER_ID = "DÁN_MÃ_FOLDER_ID_VỪA_COPY_Ở_BƯỚC_2_VÀO_ĐÂY"

   [gcp_service_account]
   type = "service_account"
   project_id = "..."
   private_key_id = "..."
   private_key = "..."
   client_email = "..."
   client_id = "..."
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "..."
   ```
   *(Chú ý: Nguyên cụm `[gcp_service_account]` bên dưới bạn phải copy chính xác 100% nội dung từ trong file `.json` ở Bước 1 dán đè vào)*
5. Bấm **Save** rồi **Deploy!**

Xong! Giờ đây khi bạn thêm văn bản "Cần Thơ", hệ thống sẽ tự tìm thư mục Cần Thơ trên Drive của bạn, nếu chưa có nó sẽ tự tạo rồi nhét file PDF vào!
