import streamlit as st
import sqlite3
import pandas as pd
import os
import shutil
from github_sync import push_file_to_github

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="Phần Mềm Quản Lý Văn Bản", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "Data")
DB_PATH = os.path.join(BASE_DIR, "documents.db")

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
            file_path = row["Đường Dẫn"]
            abs_path = os.path.join(BASE_DIR, file_path)
            
            if os.path.exists(abs_path):
                with open(abs_path, "rb") as f:
                    st.download_button(
                        label=f"Tải file {row['Tên File']}",
                        data=f,
                        file_name=row["Tên File"],
                        mime="application/octet-stream"
                    )
            else:
                st.warning("⚠️ Không tìm thấy file trên hệ thống (File có thể chưa được đồng bộ từ GitHub).")

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
        
        submitted = st.form_submit_button("LƯU VĂN BẢN VÀ ĐỒNG BỘ GITHUB")
        
        if submitted:
            if not ten_van_ban or not uploaded_file:
                st.error("Vui lòng nhập Tên văn bản và File đính kèm!")
            else:
                with st.spinner("Đang lưu trữ và đồng bộ..."):
                    # Lưu file vào thư mục local
                    file_name = uploaded_file.name
                    target_dir = os.path.join(DATA_DIR, dia_phuong)
                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, file_name)
                    
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    rel_path = os.path.relpath(target_path, BASE_DIR)
                    rel_path = rel_path.replace("\\", "/") # Fix cho Windows -> Web
                    
                    # Cập nhật DB
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO documents (dia_phuong, loai_van_ban, so_hieu, ten_van_ban, ngay_ban_hanh, co_quan, file_name, file_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (dia_phuong, loai_vb, so_hieu, ten_van_ban, ngay, co_quan, file_name, rel_path))
                    conn.commit()
                    conn.close()
                    
                    # Đồng bộ file lên GitHub
                    if push_file_to_github(target_path, f"Data/{dia_phuong}/{file_name}", f"Upload file: {file_name}"):
                        st.success("Đã đồng bộ file lên GitHub thành công!")
                    else:
                        st.warning("Đã lưu file ở máy cục bộ, nhưng đồng bộ GitHub gặp lỗi. Vui lòng kiểm tra lại Secrets.")
                        
                    # Đồng bộ DB lên GitHub
                    if push_file_to_github(DB_PATH, "documents.db", f"Update DB: Thêm văn bản {so_hieu}"):
                        st.success("Đã đồng bộ CSDL lên GitHub thành công!")
                    else:
                        st.warning("Lưu CSDL gặp lỗi khi đồng bộ GitHub.")

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
                
                updated = st.form_submit_button("CẬP NHẬT VÀ ĐỒNG BỘ GITHUB")
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
                            
                            # Cập nhật DB lên GitHub
                            if push_file_to_github(DB_PATH, "documents.db", f"Update DB: Sửa văn bản ID {edit_id}"):
                                st.success("Cập nhật thành công! (Vui lòng refresh lại trang để thấy thay đổi)")
                            else:
                                st.warning("Cập nhật ở Local thành công nhưng lỗi đồng bộ GitHub.")
