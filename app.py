import os
import sys
import shutil
import sqlite3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk

# Cấu hình CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

if getattr(sys, 'frozen', False):
    # Chạy dưới dạng file .exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Chạy dưới dạng script Python
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
            file_path TEXT
        )
    ''')
    
    # Thêm cột ten_van_ban nếu chưa có
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN ten_van_ban TEXT")
    except sqlite3.OperationalError:
        pass # Cột đã tồn tại
        
    conn.commit()
    conn.close()

# Lấy danh sách địa phương
def get_locations():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    
    locations = []
    for item in os.listdir(DATA_DIR):
        item_path = os.path.join(DATA_DIR, item)
        if os.path.isdir(item_path):
            locations.append(item)
    return locations if locations else ["Chưa có thư mục nào"]

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Phần Mềm Quản Lý Văn Bản")
        self.geometry("1200x750")
        self.minsize(1000, 600)
        
        init_db()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR (Tìm kiếm) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="BỘ LỌC TÌM KIẾM", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        # Ô tìm kiếm chung
        self.search_keyword = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Tìm từ khóa chung...")
        self.search_keyword.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Lọc theo địa phương
        self.loc_label = ctk.CTkLabel(self.sidebar_frame, text="Địa phương:", anchor="w")
        self.loc_label.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        locations = ["Tất cả"] + get_locations()
        self.search_location = ctk.CTkOptionMenu(self.sidebar_frame, values=locations)
        self.search_location.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        # Lọc Tên VB
        self.search_title = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Tên văn bản (VD: V/v cấp phép...)")
        self.search_title.grid(row=4, column=0, padx=20, pady=10, sticky="ew")

        # Lọc Loại VB (Dropdown List)
        self.type_label = ctk.CTkLabel(self.sidebar_frame, text="Loại văn bản:", anchor="w")
        self.type_label.grid(row=5, column=0, padx=20, pady=(10, 0), sticky="w")
        
        types = ["Tất cả"] + self.get_distinct_types()
        self.search_type = ctk.CTkOptionMenu(self.sidebar_frame, values=types)
        self.search_type.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        # Lọc Số hiệu
        self.search_number = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Số hiệu (VD: 123/QĐ)")
        self.search_number.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

        # Lọc Cơ quan
        self.search_agency = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Cơ quan ban hành")
        self.search_agency.grid(row=8, column=0, padx=20, pady=10, sticky="ew")

        # Nút Tìm kiếm
        self.search_btn = ctk.CTkButton(self.sidebar_frame, text="TÌM KIẾM", command=self.perform_search)
        self.search_btn.grid(row=9, column=0, padx=20, pady=20, sticky="ew")

        # --- MAIN CONTENT ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header bar
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self.header_frame, text="Danh Sách Văn Bản", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")

        self.add_btn = ctk.CTkButton(self.header_frame, text="+ THÊM VĂN BẢN", fg_color="#2ecc71", hover_color="#27ae60", command=self.open_add_window)
        self.add_btn.grid(row=0, column=1, sticky="e")

        # Table (Treeview)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=35, fieldbackground="#2b2b2b", font=("Inter", 11))
        style.map('Treeview', background=[('selected', '#1f538d')])
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=("Inter", 11, "bold"))

        self.tree_frame = ctk.CTkFrame(self.main_frame)
        self.tree_frame.grid(row=1, column=0, sticky="nsew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        columns = ("id", "dia_phuong", "so_hieu", "loai_vb", "ten_van_ban", "ngay", "co_quan", "file_name", "file_path")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("id", text="ID")
        self.tree.heading("dia_phuong", text="Địa Phương")
        self.tree.heading("so_hieu", text="Số Hiệu")
        self.tree.heading("loai_vb", text="Loại VB")
        self.tree.heading("ten_van_ban", text="Tên Văn Bản")
        self.tree.heading("ngay", text="Ngày")
        self.tree.heading("co_quan", text="Cơ Quan")
        self.tree.heading("file_name", text="Tên File")
        self.tree.heading("file_path", text="Đường dẫn")

        self.tree.column("id", width=30, anchor="center")
        self.tree.column("dia_phuong", width=100)
        self.tree.column("so_hieu", width=100)
        self.tree.column("loai_vb", width=100)
        self.tree.column("ten_van_ban", width=250)
        self.tree.column("ngay", width=90)
        self.tree.column("co_quan", width=120)
        self.tree.column("file_name", width=200)
        self.tree.column("file_path", width=0, stretch=False) # Ẩn cột

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Khung chứa các nút hành động (dưới bảng)
        self.action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_columnconfigure(1, weight=1)

        self.open_file_btn = ctk.CTkButton(self.action_frame, text="MỞ FILE ĐÃ CHỌN", command=self.open_selected_file, height=40)
        self.open_file_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.edit_btn = ctk.CTkButton(self.action_frame, text="SỬA VĂN BẢN ĐÃ CHỌN", command=self.open_edit_window, fg_color="#f39c12", hover_color="#e67e22", height=40)
        self.edit_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.perform_search()

    def get_distinct_types(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT loai_van_ban FROM documents WHERE loai_van_ban IS NOT NULL AND loai_van_ban != ''")
            types = [row[0] for row in cursor.fetchall()]
            conn.close()
            return types
        except:
            return []

    def refresh_type_dropdown(self):
        types = ["Tất cả"] + self.get_distinct_types()
        self.search_type.configure(values=types)

    def perform_search(self):
        keyword = self.search_keyword.get().strip().lower()
        location = self.search_location.get()
        title = self.search_title.get().strip().lower()
        v_type = self.search_type.get()
        if v_type == "Tất cả":
            v_type = ""
        else:
            v_type = v_type.strip().lower()
            
        number = self.search_number.get().strip().lower()
        agency = self.search_agency.get().strip().lower()

        conn = sqlite3.connect(DB_PATH)
        # Tạo hàm custom py_lower để hỗ trợ lower string Tiếng Việt Unicode trong SQLite
        conn.create_function("py_lower", 1, lambda s: str(s).lower() if s is not None else "")
        cursor = conn.cursor()

        query = "SELECT id, dia_phuong, loai_van_ban, so_hieu, ten_van_ban, ngay_ban_hanh, co_quan, file_name, file_path FROM documents WHERE 1=1"
        params = []

        if location != "Tất cả":
            query += " AND dia_phuong = ?"
            params.append(location)
        if title:
            query += " AND py_lower(IFNULL(ten_van_ban, '')) LIKE ?"
            params.append(f"%{title}%")
        if v_type:
            query += " AND py_lower(IFNULL(loai_van_ban, '')) LIKE ?"
            params.append(f"%{v_type}%")
        if number:
            query += " AND py_lower(IFNULL(so_hieu, '')) LIKE ?"
            params.append(f"%{number}%")
        if agency:
            query += " AND py_lower(IFNULL(co_quan, '')) LIKE ?"
            params.append(f"%{agency}%")
        
        if keyword:
            query += """ AND (
                py_lower(IFNULL(dia_phuong, '')) LIKE ? OR
                py_lower(IFNULL(loai_van_ban, '')) LIKE ? OR
                py_lower(IFNULL(so_hieu, '')) LIKE ? OR
                py_lower(IFNULL(ten_van_ban, '')) LIKE ? OR
                py_lower(IFNULL(co_quan, '')) LIKE ? OR
                py_lower(IFNULL(file_name, '')) LIKE ?
            )"""
            params.extend([f"%{keyword}%"] * 6)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for row in rows:
            self.tree.insert("", tk.END, values=(row[0], row[1], row[3], row[2], row[4] or "", row[5], row[6], row[7], row[8]))

    def open_selected_file(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một văn bản trong danh sách!")
            return
        
        item_values = self.tree.item(selected_item[0], "values")
        file_path = item_values[8] # Cột thứ 9
        
        absolute_path = os.path.join(BASE_DIR, file_path)
        if os.path.exists(absolute_path):
            try:
                os.startfile(absolute_path)
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở file: {str(e)}")
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy file gốc trên ổ cứng! File có thể đã bị xóa hoặc di chuyển.")

    def open_add_window(self):
        AddDocumentWindow(self)

    def open_edit_window(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một văn bản để sửa!")
            return
        
        item_values = self.tree.item(selected_item[0], "values")
        doc_id = item_values[0]
        EditDocumentWindow(self, doc_id)


class AddDocumentWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Thêm Văn Bản Mới")
        self.geometry("500x600")
        self.grab_set() 
        
        self.grid_columnconfigure(1, weight=1)
        self.selected_file_path = None

        row_idx = 0
        pad_y = 8

        # Địa phương
        ctk.CTkLabel(self, text="Địa phương (*)").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        locations = [loc for loc in get_locations() if loc != "Chưa có thư mục nào"]
        self.loc_var = ctk.StringVar(value=locations[0] if locations else "")
        self.loc_menu = ctk.CTkOptionMenu(self, values=locations if locations else ["--"], variable=self.loc_var)
        self.loc_menu.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Tên văn bản
        ctk.CTkLabel(self, text="Tên văn bản (*)").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.title_entry = ctk.CTkEntry(self, placeholder_text="VD: V/v cấp phép...")
        self.title_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Loại văn bản (ComboBox cho phép chọn hoặc nhập mới)
        ctk.CTkLabel(self, text="Loại văn bản").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        types = self.parent.get_distinct_types()
        self.type_entry = ctk.CTkComboBox(self, values=types if types else ["Quyết định", "Thông báo", "Tờ trình"])
        # Nếu đã có data thì default rỗng, nếu chưa có thì gán mặc định để gợi ý
        if not types:
            self.type_entry.set("")
        self.type_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Số hiệu
        ctk.CTkLabel(self, text="Số hiệu").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.number_entry = ctk.CTkEntry(self, placeholder_text="VD: 123/QĐ-UBND")
        self.number_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Ngày ban hành
        ctk.CTkLabel(self, text="Ngày ban hành").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.date_entry = ctk.CTkEntry(self, placeholder_text="DD/MM/YYYY")
        self.date_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Cơ quan ban hành
        ctk.CTkLabel(self, text="Cơ quan").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.agency_entry = ctk.CTkEntry(self, placeholder_text="VD: UBND Tỉnh")
        self.agency_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # File đính kèm
        ctk.CTkLabel(self, text="File đính kèm (*)").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.file_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.file_frame.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        self.file_frame.grid_columnconfigure(0, weight=1)
        
        self.file_label = ctk.CTkLabel(self.file_frame, text="Chưa chọn file", text_color="gray")
        self.file_label.grid(row=0, column=0, sticky="w")
        
        self.browse_btn = ctk.CTkButton(self.file_frame, text="Chọn File", width=80, command=self.browse_file)
        self.browse_btn.grid(row=0, column=1, padx=(10,0))
        row_idx += 1

        # Save button
        self.save_btn = ctk.CTkButton(self, text="LƯU VĂN BẢN", fg_color="#2ecc71", hover_color="#27ae60", height=40, command=self.save_document)
        self.save_btn.grid(row=row_idx, column=0, columnspan=2, padx=20, pady=30, sticky="ew")

    def browse_file(self):
        initial_dir = DATA_DIR if os.path.exists(DATA_DIR) else os.path.expanduser("~")
        file_path = filedialog.askopenfilename(
            title="Chọn file văn bản",
            initialdir=initial_dir,
            filetypes=[("Documents", "*.pdf *.doc *.docx *.xls *.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            self.selected_file_path = file_path
            self.file_label.configure(text=os.path.basename(file_path), text_color="white")

    def save_document(self):
        dia_phuong = self.loc_var.get()
        title = self.title_entry.get().strip()
        loai_vb = self.type_entry.get().strip()
        so_hieu = self.number_entry.get().strip()
        ngay = self.date_entry.get().strip()
        co_quan = self.agency_entry.get().strip()

        if not dia_phuong or not self.selected_file_path or not title:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Tên văn bản, chọn Địa phương và File đính kèm!")
            return

        file_name = os.path.basename(self.selected_file_path)
        target_dir = os.path.join(DATA_DIR, dia_phuong)
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, file_name)

        norm_source = os.path.normcase(os.path.abspath(self.selected_file_path))
        norm_target = os.path.normcase(os.path.abspath(target_path))

        if norm_source != norm_target:
            try:
                shutil.copy2(self.selected_file_path, target_path)
            except Exception as e:
                messagebox.showerror("Lỗi Copy", f"Không thể copy file: {str(e)}")
                return

        rel_path = os.path.relpath(target_path, BASE_DIR)

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO documents (dia_phuong, loai_van_ban, so_hieu, ten_van_ban, ngay_ban_hanh, co_quan, file_name, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (dia_phuong, loai_vb, so_hieu, title, ngay, co_quan, file_name, rel_path))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Thành công", "Đã thêm văn bản thành công!")
            self.parent.refresh_type_dropdown() # Cập nhật dropdown ở sidebar
            self.parent.perform_search()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Lỗi khi lưu vào Database: {str(e)}")


class EditDocumentWindow(ctk.CTkToplevel):
    def __init__(self, parent, doc_id):
        super().__init__(parent)
        self.parent = parent
        self.doc_id = doc_id
        self.title("Sửa Thông Tin Văn Bản")
        self.geometry("500x500")
        self.grab_set() 
        
        self.grid_columnconfigure(1, weight=1)

        # Lấy dữ liệu từ DB
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT dia_phuong, loai_van_ban, so_hieu, ten_van_ban, ngay_ban_hanh, co_quan FROM documents WHERE id = ?", (self.doc_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Lỗi", "Không tìm thấy văn bản trong CSDL!")
            self.destroy()
            return
            
        db_dia_phuong, db_loai, db_so_hieu, db_ten, db_ngay, db_co_quan = row

        row_idx = 0
        pad_y = 8

        # Địa phương
        ctk.CTkLabel(self, text="Địa phương (*)").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        locations = [loc for loc in get_locations() if loc != "Chưa có thư mục nào"]
        self.loc_var = ctk.StringVar(value=db_dia_phuong if db_dia_phuong in locations else (locations[0] if locations else ""))
        self.loc_menu = ctk.CTkOptionMenu(self, values=locations if locations else ["--"], variable=self.loc_var)
        self.loc_menu.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Tên văn bản
        ctk.CTkLabel(self, text="Tên văn bản (*)").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.title_entry = ctk.CTkEntry(self)
        self.title_entry.insert(0, db_ten if db_ten else "")
        self.title_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Loại văn bản
        ctk.CTkLabel(self, text="Loại văn bản").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        types = self.parent.get_distinct_types()
        self.type_entry = ctk.CTkComboBox(self, values=types if types else ["Quyết định", "Thông báo", "Tờ trình"])
        self.type_entry.set(db_loai if db_loai else "")
        self.type_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Số hiệu
        ctk.CTkLabel(self, text="Số hiệu").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.number_entry = ctk.CTkEntry(self)
        self.number_entry.insert(0, db_so_hieu if db_so_hieu else "")
        self.number_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Ngày ban hành
        ctk.CTkLabel(self, text="Ngày ban hành").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.date_entry = ctk.CTkEntry(self)
        self.date_entry.insert(0, db_ngay if db_ngay else "")
        self.date_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Cơ quan ban hành
        ctk.CTkLabel(self, text="Cơ quan").grid(row=row_idx, column=0, padx=20, pady=pad_y, sticky="w")
        self.agency_entry = ctk.CTkEntry(self)
        self.agency_entry.insert(0, db_co_quan if db_co_quan else "")
        self.agency_entry.grid(row=row_idx, column=1, padx=20, pady=pad_y, sticky="ew")
        row_idx += 1

        # Save button
        self.save_btn = ctk.CTkButton(self, text="CẬP NHẬT", fg_color="#f39c12", hover_color="#e67e22", height=40, command=self.update_document)
        self.save_btn.grid(row=row_idx, column=0, columnspan=2, padx=20, pady=30, sticky="ew")

    def update_document(self):
        dia_phuong = self.loc_var.get()
        title = self.title_entry.get().strip()
        loai_vb = self.type_entry.get().strip()
        so_hieu = self.number_entry.get().strip()
        ngay = self.date_entry.get().strip()
        co_quan = self.agency_entry.get().strip()

        if not title:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập Tên văn bản!")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE documents 
                SET dia_phuong=?, loai_van_ban=?, so_hieu=?, ten_van_ban=?, ngay_ban_hanh=?, co_quan=?
                WHERE id=?
            ''', (dia_phuong, loai_vb, so_hieu, title, ngay, co_quan, self.doc_id))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Thành công", "Đã cập nhật thông tin văn bản!")
            self.parent.refresh_type_dropdown() # Cập nhật dropdown ở sidebar nếu có loại VB mới
            self.parent.perform_search()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi CSDL", f"Lỗi khi cập nhật Database: {str(e)}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
