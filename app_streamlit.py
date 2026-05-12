import streamlit as st
import sqlite3
import pandas as pd
import os
import shutil
import base64
import urllib.parse
import streamlit.components.v1 as components
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
tab1, tab2, tab3, tab4 = st.tabs(["📄 Danh sách văn bản", "➕ Thêm văn bản", "✏️ Sửa văn bản", "🗑️ Xóa văn bản"])

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
    
    st.dataframe(df.drop(columns=["Đường Dẫn"]), use_container_width=True, hide_index=True)
    
    # Khu vực tải file xuống / xem file
    if not df.empty:
        st.subheader("⬇️ Tải file văn bản")
        selected_id = st.selectbox("Chọn ID văn bản để tải/xem:", df["ID"].tolist())
        if selected_id:
            row = df[df["ID"] == selected_id].iloc[0]
            file_path = row["Đường Dẫn"]
            
            # Sửa lỗi khác biệt đường dẫn giữa Windows (\) và Linux trên Streamlit (/)
            file_path = file_path.replace('\\', '/')
            
            # Fix lỗi đường dẫn cũ từ bản Desktop trỏ ra ngoài (luu_tru_van_ban)
            if file_path.startswith('../luu_tru_van_ban/'):
                file_path = file_path.replace('../luu_tru_van_ban/', 'Data/')
            elif file_path.startswith('luu_tru_van_ban/'):
                file_path = file_path.replace('luu_tru_van_ban/', 'Data/')
                
            abs_path = os.path.join(BASE_DIR, file_path)
            
            if os.path.exists(abs_path):
                # 1. Đọc file
                with open(abs_path, "rb") as f:
                    file_bytes = f.read()
                    
                col_dl, col_share = st.columns([1, 1])
                with col_dl:
                    st.download_button(
                        label=f"Tải file {row['Tên File']}",
                        data=file_bytes,
                        file_name=row["Tên File"],
                        mime="application/octet-stream"
                    )
                
                # 2. Nút chia sẻ (Web Share API cho Mobile)
                with col_share:
                    # Tạo Public Link từ GitHub Raw
                    github_raw_base = "https://raw.githubusercontent.com/luanvo2021/phan-mem-quan-ly/main/"
                    # Encode URL để xử lý khoảng trắng và tiếng Việt
                    encoded_path = urllib.parse.quote(file_path)
                    public_url = github_raw_base + encoded_path
                    
                    share_html = f"""
                    <button onclick="shareFile()" style="background-color: #0084FF; color: white; padding: 0.4rem 1rem; border: none; border-radius: 0.3rem; cursor: pointer; font-weight: 600; width: 100%; font-family: sans-serif; font-size: 15px; margin-top: 2px;">
                        🔗 Chia sẻ (Zalo/Apps...)
                    </button>
                    <script>
                    function shareFile() {{
                        var urlToShare = '{public_url}';
                        if (navigator.share) {{
                            navigator.share({{
                                title: '{row['Tên File']}',
                                text: 'Gửi bạn tài liệu: {row['Tên File']}',
                                url: urlToShare
                            }}).catch(console.error);
                        }} else {{
                            // Nếu trình duyệt/WebView khóa Web Share, dùng Android Intent
                            var ua = navigator.userAgent.toLowerCase();
                            var isAndroid = ua.indexOf("android") > -1;
                            
                            if (isAndroid) {{
                                // Gọi Intent chia sẻ mặc định của Android
                                var intentUrl = 'intent:#Intent;action=android.intent.action.SEND;type=text/plain;S.android.intent.extra.TEXT=' + encodeURIComponent(urlToShare) + ';end';
                                window.location.href = intentUrl;
                            }} else {{
                                // Bất đắc dĩ mới copy
                                navigator.clipboard.writeText(urlToShare).then(function() {{
                                    alert('Đã copy link tài liệu! Hãy mở Zalo/Messenger và dán ra nhé.');
                                }});
                            }}
                        }}
                    }}
                    </script>
                    """
                    components.html(share_html, height=50)

                # 3. Khu vực Xem trước (Preview)
                st.markdown("---")
                with st.expander("👀 Bấm vào đây để Xem trước văn bản"):
                    file_ext = os.path.splitext(row['Tên File'])[1].lower()
                    
                    if file_ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
                        # Sử dụng Google Docs Viewer để hỗ trợ xem trên điện thoại (WebView)
                        viewer_url = f"https://docs.google.com/viewer?url={public_url}&embedded=true"
                        pdf_display = f'<iframe src="{viewer_url}" width="100%" height="600px" style="border: none;"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                        st.caption("Nếu màn hình vẫn trắng, vui lòng bấm Tải file ở trên.")
                    elif file_ext in ['.png', '.jpg', '.jpeg']:
                        st.image(file_bytes, use_container_width=True)
                    else:
                        st.info("⚠️ Không hỗ trợ xem trước định dạng này. Vui lòng bấm 'Tải file' hoặc 'Chia sẻ'.")
                    
            else:
                st.warning("⚠️ Không tìm thấy file trên hệ thống (File có thể chưa được đồng bộ từ GitHub).")

with tab2:
    st.header("Thêm Văn Bản Mới")
    
    with st.form("add_document_form"):
        col1, col2 = st.columns(2)
        with col1:
            locs = [loc for loc in get_locations() if loc != "Chưa có thư mục nào"]
            if not locs: locs = ["Chung"]
            dia_phuong_chon = st.selectbox("Địa phương (*)", locs + ["-- THÊM ĐỊA PHƯƠNG MỚI --"])
            dia_phuong_moi = st.text_input("Tên địa phương mới (Chỉ điền nếu chọn Thêm mới ở trên)", placeholder="VD: Sóc Trăng")
            
            ten_van_ban = st.text_input("Tên văn bản (*)", placeholder="VD: V/v cấp phép...")
            
            loai_vb_opts = get_distinct_types()
            loai_vb_opts = loai_vb_opts if loai_vb_opts else ["Quyết định", "Thông báo", "Tờ trình"]
            loai_vb_chon = st.selectbox("Loại văn bản", loai_vb_opts + ["-- THÊM LOẠI MỚI --"])
            loai_vb_moi = st.text_input("Loại văn bản mới (Chỉ điền nếu chọn Thêm mới ở trên)")
        with col2:
            so_hieu = st.text_input("Số hiệu", placeholder="VD: 123/QĐ-UBND")
            ngay = st.text_input("Ngày ban hành", placeholder="DD/MM/YYYY")
            co_quan = st.text_input("Cơ quan", placeholder="VD: UBND Tỉnh")
            
        uploaded_file = st.file_uploader("File đính kèm (*)", type=["pdf", "doc", "docx", "xls", "xlsx", "png", "jpg", "rar", "zip"])
        
        submitted = st.form_submit_button("LƯU VĂN BẢN VÀ ĐỒNG BỘ GITHUB")
        
        if submitted:
            # Xử lý biến lấy từ form
            dia_phuong = dia_phuong_moi.strip() if dia_phuong_chon == "-- THÊM ĐỊA PHƯƠNG MỚI --" and dia_phuong_moi.strip() else dia_phuong_chon
            loai_vb = loai_vb_moi.strip() if loai_vb_chon == "-- THÊM LOẠI MỚI --" and loai_vb_moi.strip() else loai_vb_chon
            
            if dia_phuong == "-- THÊM ĐỊA PHƯƠNG MỚI --":
                st.error("Vui lòng nhập tên địa phương mới!")
            elif not ten_van_ban or not uploaded_file:
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
                    # File sẽ được lưu vào đúng thư mục con "Data/Tên_Địa_Phương" trên GitHub
                    github_path = f"Data/{dia_phuong}/{file_name}"
                    if push_file_to_github(target_path, github_path, f"Upload file: {file_name}"):
                        st.success(f"Đã đồng bộ file lên thư mục '{dia_phuong}' trên GitHub thành công!")
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
                    e_dia_phuong_chon = st.selectbox("Địa phương (*)", locs + ["-- THÊM ĐỊA PHƯƠNG MỚI --"], index=locs.index(row['Địa Phương']) if row['Địa Phương'] in locs else 0)
                    e_dia_phuong_moi = st.text_input("Tên địa phương mới", placeholder="VD: Bến Tre (Chỉ điền nếu chọn Thêm mới)")
                    
                    e_ten_van_ban = st.text_input("Tên văn bản (*)", value=row['Tên Văn Bản'] if pd.notna(row['Tên Văn Bản']) else "")
                    
                    loai_vb_opts = get_distinct_types()
                    if row['Loại VB'] not in loai_vb_opts and row['Loại VB']:
                        loai_vb_opts.append(row['Loại VB'])
                    e_loai_vb_chon = st.selectbox("Loại văn bản", loai_vb_opts + ["-- THÊM LOẠI MỚI --"], index=loai_vb_opts.index(row['Loại VB']) if row['Loại VB'] in loai_vb_opts else 0)
                    e_loai_vb_moi = st.text_input("Loại văn bản mới", placeholder="Chỉ điền nếu chọn Thêm mới ở trên")
                with col2:
                    e_so_hieu = st.text_input("Số hiệu", value=row['Số Hiệu'] if pd.notna(row['Số Hiệu']) else "")
                    e_ngay = st.text_input("Ngày ban hành", value=row['Ngày'] if pd.notna(row['Ngày']) else "")
                    e_co_quan = st.text_input("Cơ quan", value=row['Cơ Quan'] if pd.notna(row['Cơ Quan']) else "")
                
                updated = st.form_submit_button("CẬP NHẬT VÀ ĐỒNG BỘ GITHUB")
                if updated:
                    e_dia_phuong = e_dia_phuong_moi.strip() if e_dia_phuong_chon == "-- THÊM ĐỊA PHƯƠNG MỚI --" and e_dia_phuong_moi.strip() else e_dia_phuong_chon
                    e_loai_vb = e_loai_vb_moi.strip() if e_loai_vb_chon == "-- THÊM LOẠI MỚI --" and e_loai_vb_moi.strip() else e_loai_vb_chon
                    
                    if e_dia_phuong == "-- THÊM ĐỊA PHƯƠNG MỚI --":
                        st.error("Vui lòng nhập tên địa phương mới!")
                    elif not e_ten_van_ban:
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

with tab4:
    st.header("Xóa Văn Bản")
    if df.empty:
        st.info("Chưa có văn bản nào để xóa.")
    else:
        delete_id = st.selectbox("Chọn ID văn bản cần xóa:", df["ID"].tolist())
        if delete_id:
            row = df[df["ID"] == delete_id].iloc[0]
            st.warning(f"Bạn đang chọn xóa văn bản: **{row['Tên Văn Bản']}** (ID: {delete_id})")
            st.write(f"- Địa phương: {row['Địa Phương']}")
            st.write(f"- Số hiệu: {row['Số Hiệu']}")
            
            # Thêm xác nhận hai bước để an toàn
            confirm = st.checkbox("Tôi chắc chắn muốn xóa văn bản này khỏi cơ sở dữ liệu.")
            
            if confirm:
                if st.button("XÓA VĂN BẢN (KHÔNG THỂ PHỤC HỒI)", type="primary"):
                    with st.spinner("Đang xóa..."):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM documents WHERE id=?', (int(delete_id),))
                        conn.commit()
                        conn.close()
                        
                        # Cập nhật DB lên GitHub
                        if push_file_to_github(DB_PATH, "documents.db", f"Update DB: Xóa văn bản ID {delete_id}"):
                            st.success("Đã xóa thành công! (Vui lòng refresh lại trang để cập nhật danh sách)")
                        else:
                            st.warning("Đã xóa ở Local thành công nhưng lỗi đồng bộ GitHub.")
