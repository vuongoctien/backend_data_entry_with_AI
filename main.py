from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io

# Đường dẫn đến Tesseract và Poppler
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin" 

app = FastAPI()

# Cho phép frontend gọi API nếu cần
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-pdf") # nhận api /upload-pdf 
async def upload_pdf(file: UploadFile = File(...)): #gán file PDF vừa nhận vào biến file
    contents = await file.read() #đọc nội dung file, phải có await vì nó lâu
    text = ""

    """# Thử đọc bằng PyMuPDF (nếu có text layer, và chỉ là nếu thôi, thực tế sẽ không có)
    doc = fitz.open(stream=contents, filetype="pdf")
    for page in doc:
        text += page.get_text()
    
    # Nếu không có text nào (và khi dùng thực tế sẽ không thể có)-> dùng OCR (scan dạng ảnh)
    if not text.strip():"""

    images = convert_from_bytes(contents, poppler_path=POPPLER_PATH) #Chuyển đổi file PDF thành list các hình ảnh (mỗi ảnh tương ứng một trang).
    for img in images: # duyệt list hình ảnh
        text += pytesseract.image_to_string(img, lang="vie") + "\n" #orc, nối vào biến text

    return {"text": text} # Trả về kết quả dưới dạng JSON với key "text"