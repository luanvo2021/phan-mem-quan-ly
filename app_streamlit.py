import streamlit as st
import sqlite3
import pandas as pd
import os
import shutil
from drive_sync import (
    get_drive_service,
    get_root_folder_id,
    get_or_create_subfolder,
    upload_file_to_drive, 
    download_db_from_drive,
    download_file_bytes_from_drive
)

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Phần Mềm Quản Lý Văn Bản", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
DB_PATH = os.path.join(BASE_DIR, "documents.db")

# ---- ĐỒNG BỘ DỮ LIỆU TỪ DRIVE ----
if "db_synced" not in st.session_state:
    with st.spinner("Đang đồng bộ dữ liệu mới nhất từ Google Drive..."):
        download_db_from_drive(DB_PATH)
        st.session_state.db_synced = True

# Nút làm mới thủ công
st.sidebar.button("🔄 Làm mới dữ liệu", on_click=lambda: st.session_state.pop("db_synced", None))


# Khởi tạo CSDL
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_phuong TEXT,
            loai_van_ban TEXT,
            so_hieu TEXT,
            ngay_ban_hanh TEXT,
            co_quan TEXT,
            file_name TEXT,
            file_path TEXT,
            ten_van_ban TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Hàm lấy địa phương
def get_locations():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    
    locations = []
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        if os.path.isdir(item_path):
            locations.append(item)
    # Lấy thêm địa phương từ CSDL để phòng trường hợp máy cục bộ không có thư mục
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT dia_phuong FROM documents WHERE dia_phuong IS NOT NULL AND dia_phuong != ''")
        db_locs = [row[0] for row in cursor.fetchall()]
        conn.close()
        for loc in db_locs:
            if loc not in locations:
                locations.append(loc)
    except:
        pass

    return locations if locations else ["Chưa có thư mục nào"]

def get_distinct_types():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT loai_van_ban FROM documents WHERE loai_van_ban IS NOT NULL AND loai_van_ban != ''")
        types = [row[0] for row in cursor.fetchall()]
        conn.close()
        return types
    except:
        return []

init_db()

# ---- SIDEBAR: TÌM KIẾM ----
st.sidebar.header("🔍 BỘ LỌC TÌM KIẾM")

search_keyword = st.sidebar.text_input("Từ khóa chung...")

locations = ["Tất cả"] + get_locations()
search_location = st.sidebar.selectbox("Địa phương", locations)

search_title = st.sidebar.text_input("Tên văn bản (VD: V/v cấp phép...)")

types = ["Tất cả"] + get_distinct_types()
search_type = st.sidebar.selectbox("Loại văn bản", types)

search_number = st.sidebar.text_input("Số hiệu (VD: 123/QĐ)")
search_agency = st.sidebar.text_input("Cơ quan ban hành")

# ---- MAIN TABS ----
tab1, tab2, tab3 = st.tabs(["📄 Danh sách văn bản", "➕ Thêm văn bản", "✏️ Sửa văn bản"])

with tab1:
    st.header("Danh Sách Văn Bản")
    
    # Query Database
    conn = sqlite3.connect(DB_PATH)
    conn.create_function("py_lower", 1, lambda s: str(s).lower() if s is not None else "")
    
    query = "SELECT id, dia_phuong, so_hieu, loai_van_ban, ten_van_ban, ngay_ban_hanh, co_quan, file_name, file_path FROM documents WHERE 1=1"
    params = []

    if search_location != "Tất cả":
        query += " AND dia_phuong = ?"
        params.append(search_location)
    if search_title:
        query += " AND py_lower(IFNULL(ten_van_ban, '')) LIKE ?"
        params.append(f"%{search_title.lower()}%")
    if search_type != "Tất cả":
        query += " AND py_lower(IFNULL(loai_van_ban, '')) LIKE ?"
        params.append(f"%{search_type.lower()}%")
    if search_number:
        query += " AND py_lower(IFNULL(so_hieu, '')) LIKE ?"
        params.append(f"%{search_number.lower()}%")
    if search_agency:
        query += " AND py_lower(IFNULL(co_quan, '')) LIKE ?"
        params.append(f"%{search_agency.lower()}%")
    if search_keyword:
        query += """ AND (
            py_lower(IFNULL(dia_phuong, '')) LIKE ? OR
            py_lower(IFNULL(loai_van_ban, '')) LIKE ? OR
            py_lower(IFNULL(so_hieu, '')) LIKE ? OR
            py_lower(IFNULL(ten_van_ban, '')) LIKE ? OR
            py_lower(IFNULL(co_quan, '')) LIKE ? OR
            py_lower(IFNULL(file_name, '')) LIKE ?
        )"""
        params.extend([f"%{search_keyword.lower()}%"] * 6)

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    # Đổi tên cột cho đẹp
    df.columns = ["ID", "Địa Phương", "Số Hiệu", "Loại VB", "Tên Văn Bản", "Ngày", "Cơ Quan", "Tên File", "Đường Dẫn"]
    
    st.dataframe(df.drop(columns=["Đường Dẫn"]), use_container_width=True)
    
    # Khu vực tải file xuống / xem file
    if not df.empty:
        st.subheader("⬇️ Tải file văn bản")
        selected_id = st.selectbox("Chọn ID văn bản để tải/xem:", df["ID"].tolist())
        if selected_id:
            row = df[df["ID"] == selected_id].iloc[0]
            file_name = row["Tên File"]
            dia_phuong_file = row["Địa Phương"]
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button(f"📥 Tải {file_name} từ Cloud"):
                    with st.spinner(f"Đang kéo file từ thư mục '{dia_phuong_file}' trên Google Drive về..."):
                        file_bytes = download_file_bytes_from_drive(file_name, dia_phuong_file)
                        if file_bytes:
                            st.session_state.temp_file_bytes = file_bytes
                            st.session_state.temp_file_name = file_name
                        else:
                            st.error("Không tìm thấy file trên Google Drive!")
            
            with col2:
                if st.session_state.get("temp_file_bytes") and st.session_state.get("temp_file_name") == file_name:
                    st.download_button(
                        label="👉 Bấm vào đây để tải xuống máy",
                        data=st.session_state.temp_file_bytes,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )

with tab2:
    st.header("Thêm Văn Bản Mới")
    
    with st.form("add_document_form"):
        col1, col2 = st.columns(2)
        with col1:
            locs = [loc for loc in get_locations() if loc != "Chưa có thư mục nào"]
            if not locs: locs = ["Chung"]
            dia_phuong = st.selectbox("Địa phương (*)", locs)
            
            ten_van_ban = st.text_input("Tên văn bản (*)", placeholder="VD: V/v cấp phép...")
            loai_vb_opts = get_distinct_types()
            loai_vb_opts = loai_vb_opts if loai_vb_opts else ["Quyết định", "Thông báo", "Tờ trình"]
            loai_vb = st.selectbox("Loại văn bản", loai_vb_opts + ["Khác"])
            if loai_vb == "Khác":
                loai_vb = st.text_input("Nhập loại văn bản mới")
        with col2:
            so_hieu = st.text_input("Số hiệu", placeholder="VD: 123/QĐ-UBND")
            ngay = st.text_input("Ngày ban hành", placeholder="DD/MM/YYYY")
            co_quan = st.text_input("Cơ quan", placeholder="VD: UBND Tỉnh")
            
        uploaded_file = st.file_uploader("File đính kèm (*)", type=["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "rar", "zip"])
        
        submitted = st.form_submit_button("LƯU VĂN BẢN VÀ ĐỒNG BỘ GOOGLE DRIVE")
        
        if submitted:
            if not ten_van_ban or not uploaded_file:
                st.error("Vui lòng nhập Tên văn bản và File đính kèm!")
            else:
                with st.spinner("Đang lưu trữ và đồng bộ..."):
                    # Lưu file vào thư mục local tạm thời
                    file_name = uploaded_file.name
                    target_dir = os.path.join(DATA_DIR, dia_phuong)
                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, file_name)
                    
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    rel_path = os.path.relpath(target_path, BASE_DIR).replace("\\", "/")
                    
                    # Cập nhật DB
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO documents (dia_phuong, loai_van_ban, so_hieu, ten_van_ban, ngay_ban_hanh, co_quan, file_name, file_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (dia_phuong, loai_vb, so_hieu, ten_van_ban, ngay, co_quan, file_name, rel_path))
                    conn.commit()
                    conn.close()
                    
                    # ĐỒNG BỘ LÊN GOOGLE DRIVE
                    service = get_drive_service()
                    root_id = get_root_folder_id()
                    
                    if service and root_id:
                        # 1. Tìm hoặc tạo thư mục con (VD: Cần Thơ)
                        subfolder_id = get_or_create_subfolder(service, root_id, dia_phuong)
                        
                        # 2. Upload file vào thư mục con đó
                        if upload_file_to_drive(target_path, file_name, subfolder_id):
                            st.success(f"Đã đồng bộ file PDF/Docx vào thư mục '{dia_phuong}' trên Google Drive!")
                        else:
                            st.warning("Đã lưu file ở máy cục bộ, nhưng đồng bộ Drive gặp lỗi.")
                            
                        # 3. Đồng bộ documents.db lên thư mục gốc
                        if upload_file_to_drive(DB_PATH, "documents.db", root_id):
                            st.success("Đã đồng bộ CSDL lên Google Drive thành công!")
                            st.session_state.pop("db_synced", None) # Để lần sau tải lại
                        else:
                            st.warning("Lưu CSDL gặp lỗi khi đồng bộ Drive.")
                    else:
                        st.error("Chưa cấu hình Google Drive hoặc lỗi xác thực!")

with tab3:
    st.header("Sửa Thông Tin Văn Bản")
    if df.empty:
        st.info("Chưa có văn bản nào để sửa.")
    else:
        edit_id = st.selectbox("Chọn ID văn bản cần sửa:", df["ID"].tolist())
        if edit_id:
            row = df[df["ID"] == edit_id].iloc[0]
            with st.form("edit_document_form"):
                col1, col2 = st.columns(2)
                with col1:
                    locs = [loc for loc in get_locations() if loc != "Chưa có thư mục nào"]
                    if row['Địa Phương'] not in locs and row['Địa Phương']:
                        locs.append(row['Địa Phương'])
                    e_dia_phuong = st.selectbox("Địa phương (*)", locs, index=locs.index(row['Địa Phương']) if row['Địa Phương'] in locs else 0)
                    
                    e_ten_van_ban = st.text_input("Tên văn bản (*)", value=row['Tên Văn Bản'] if pd.notna(row['Tên Văn Bản']) else "")
                    
                    loai_vb_opts = get_distinct_types()
                    if row['Loại VB'] not in loai_vb_opts and row['Loại VB']:
                        loai_vb_opts.append(row['Loại VB'])
                    e_loai_vb = st.selectbox("Loại văn bản", loai_vb_opts, index=loai_vb_opts.index(row['Loại VB']) if row['Loại VB'] in loai_vb_opts else 0)
                with col2:
                    e_so_hieu = st.text_input("Số hiệu", value=row['Số Hiệu'] if pd.notna(row['Số Hiệu']) else "")
                    e_ngay = st.text_input("Ngày ban hành", value=row['Ngày'] if pd.notna(row['Ngày']) else "")
                    e_co_quan = st.text_input("Cơ quan", value=row['Cơ Quan'] if pd.notna(row['Cơ Quan']) else "")
                
                updated = st.form_submit_button("CẬP NHẬT VÀ ĐỒNG BỘ GOOGLE DRIVE")
                if updated:
                    if not e_ten_van_ban:
                        st.error("Vui lòng nhập Tên văn bản!")
                    else:
                        with st.spinner("Đang cập nhật..."):
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute('''
                                UPDATE documents 
                                SET dia_phuong=?, loai_van_ban=?, so_hieu=?, ten_van_ban=?, ngay_ban_hanh=?, co_quan=?
                                WHERE id=?
                            ''', (e_dia_phuong, e_loai_vb, e_so_hieu, e_ten_van_ban, e_ngay, e_co_quan, edit_id))
                            conn.commit()
                            conn.close()
                            
                            service = get_drive_service()
                            root_id = get_root_folder_id()
                            if service and root_id:
                                if upload_file_to_drive(DB_PATH, "documents.db", root_id):
                                    st.success("Cập nhật thành công! Đã lưu lên Drive.")
                                    st.session_state.pop("db_synced", None)
                                else:
                                    st.warning("Cập nhật ở Local thành công nhưng lỗi đồng bộ Drive.")
                            else:
                                st.error("Lỗi cấu hình Drive API!")
