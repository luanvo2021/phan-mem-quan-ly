import os
import shutil
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import List, Optional
import uvicorn
from pydantic import BaseModel

# Cấu hình đường dẫn
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(os.path.dirname(BASE_DIR), "luu_tru_van_ban")
DB_PATH = os.path.join(BASE_DIR, "documents.db")

# Cấu hình CSDL
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    dia_phuong = Column(String, index=True)
    loai_van_ban = Column(String, index=True)
    so_hieu = Column(String, index=True)
    ngay_ban_hanh = Column(String, index=True)
    co_quan = Column(String, index=True)
    file_name = Column(String)
    file_path = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Phần mềm Quản lý Văn bản")

# Tạo thư mục static nếu chưa có
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

class DocumentSchema(BaseModel):
    id: int
    dia_phuong: str
    loai_van_ban: str
    so_hieu: str
    ngay_ban_hanh: str
    co_quan: str
    file_name: str
    file_path: str

    class Config:
        from_attributes = True

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open(os.path.join(BASE_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/locations")
def get_locations():
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)
    
    locations = []
    for item in os.listdir(STORAGE_DIR):
        if os.path.isdir(os.path.join(STORAGE_DIR, item)):
            locations.append(item)
    return {"locations": locations}

@app.post("/api/documents")
async def create_document(
    dia_phuong: str = Form(...),
    loai_van_ban: str = Form(...),
    so_hieu: str = Form(...),
    ngay_ban_hanh: str = Form(...),
    co_quan: str = Form(...),
    file: UploadFile = File(...)
):
    # Đảm bảo thư mục lưu trữ cho địa phương tồn tại
    target_dir = os.path.join(STORAGE_DIR, dia_phuong)
    os.makedirs(target_dir, exist_ok=True)

    # Đường dẫn file
    file_path = os.path.join(target_dir, file.filename)
    
    # Copy file vào thư mục
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Lưu vào CSDL
    db = SessionLocal()
    try:
        new_doc = DocumentModel(
            dia_phuong=dia_phuong,
            loai_van_ban=loai_van_ban,
            so_hieu=so_hieu,
            ngay_ban_hanh=ngay_ban_hanh,
            co_quan=co_quan,
            file_name=file.filename,
            file_path=os.path.relpath(file_path, BASE_DIR) # Lưu đường dẫn tương đối
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)
        return {"message": "Thêm văn bản thành công", "document_id": new_doc.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/documents", response_model=List[DocumentSchema])
def search_documents(
    dia_phuong: Optional[str] = None,
    loai_van_ban: Optional[str] = None,
    so_hieu: Optional[str] = None,
    ngay_ban_hanh: Optional[str] = None,
    co_quan: Optional[str] = None,
    keyword: Optional[str] = None
):
    db = SessionLocal()
    try:
        query = db.query(DocumentModel)

        if dia_phuong:
            query = query.filter(DocumentModel.dia_phuong.contains(dia_phuong))
        if loai_van_ban:
            query = query.filter(DocumentModel.loai_van_ban.contains(loai_van_ban))
        if so_hieu:
            query = query.filter(DocumentModel.so_hieu.contains(so_hieu))
        if ngay_ban_hanh:
            query = query.filter(DocumentModel.ngay_ban_hanh.contains(ngay_ban_hanh))
        if co_quan:
            query = query.filter(DocumentModel.co_quan.contains(co_quan))
        
        # Tìm kiếm chung trên tất cả các trường
        if keyword:
            query = query.filter(
                DocumentModel.dia_phuong.contains(keyword) |
                DocumentModel.loai_van_ban.contains(keyword) |
                DocumentModel.so_hieu.contains(keyword) |
                DocumentModel.co_quan.contains(keyword) |
                DocumentModel.file_name.contains(keyword)
            )

        documents = query.all()
        return documents
    finally:
        db.close()

@app.get("/api/download/{doc_id}")
def download_document(doc_id: int):
    db = SessionLocal()
    try:
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        absolute_path = os.path.join(BASE_DIR, doc.file_path)
        if not os.path.exists(absolute_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        return FileResponse(path=absolute_path, filename=doc.file_name)
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
