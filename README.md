# Hướng Dẫn Triển Khai Phần Mềm Quản Lý Văn Bản Lên Web (Streamlit Cloud & GitHub)

Dự án này đã được chuyển đổi thành Web App sử dụng **Streamlit** và đồng bộ dữ liệu thông qua **GitHub**. 
Hệ thống sẽ tự động tạo thư mục con (VD: Data/Cần Thơ, Data/Đà Nẵng) trên GitHub của bạn y hệt như trên máy tính.

## Bước 1: Đẩy mã nguồn lên GitHub
1. Tạo một repository **Public** (hoặc Private) trên GitHub (VD: `phan-mem-quan-ly-van-ban`).
2. Tải toàn bộ thư mục này (bao gồm `app_streamlit.py`, `documents.db`, `github_sync.py`, `requirements.txt`...) lên Repository đó.

## Bước 2: Lấy mã GITHUB_TOKEN
Mã này giúp ứng dụng Streamlit có quyền đẩy file mới (PDF/Docx) vào kho lưu trữ GitHub của bạn.
1. Vào GitHub.com -> Click vào Avatar góc phải trên -> **Settings**.
2. Cuộn xuống dưới cùng bên trái chọn **Developer settings**.
3. Chọn **Personal access tokens** -> **Tokens (classic)**.
4. Bấm **Generate new token (classic)**.
5. Phần **Note**: Điền "Streamlit App Sync".
6. Phần **Expiration**: Chọn `No expiration`.
7. Phần **Select scopes**: Tích chọn ô `repo` (để cấp quyền đọc/ghi repository).
8. Bấm **Generate token** và **COPY MÃ TOKEN NÀY LẠI** (nó chỉ hiện 1 lần duy nhất).

## Bước 3: Triển khai lên Streamlit Community Cloud
1. Truy cập https://share.streamlit.io/ và đăng nhập bằng tài khoản GitHub.
2. Bấm **New app**.
3. Chọn Repository mà bạn vừa tạo ở Bước 1.
4. **Branch**: `main` (hoặc `master`).
5. **Main file path**: Điền `app_streamlit.py`.
6. Bấm **Advanced settings**:
   Tại phần `Secrets`, dán cấu hình sau vào và thay thế bằng mã thật của bạn:
   ```toml
   GITHUB_TOKEN = "MÃ_TOKEN_BẠN_VỪA_COPY_Ở_BƯỚC_2"
   REPO_NAME = "tên-user-của-bạn/tên-repository-của-bạn"
   ```
   *(Ví dụ: `REPO_NAME = "MrLuan/phan-mem-quan-ly-van-ban"`)*
7. Bấm **Save** rồi bấm **Deploy!**

## Bước 4: Cài đặt Keep-alive (Chạy 24/7)
1. Sau khi Deploy thành công, copy đường link trang web Streamlit của bạn (VD: `https://phan-mem-quan-ly.streamlit.app`).
2. Vào lại kho lưu trữ trên GitHub -> Chọn tab **Settings** -> **Secrets and variables** -> **Actions**.
3. Bấm **New repository secret**.
4. **Name**: Điền `STREAMLIT_APP_URL`
5. **Secret**: Dán đường link trang web của bạn vào.
6. Bấm **Add secret**.
7. Tiếp theo, chuyển sang tab **Actions** trên GitHub, tìm Workflow có tên "Keep Streamlit App Alive" bên trái, bấm vào nó và chọn **Enable workflow**.
