from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
import json
from openai import OpenAI
from dotenv import load_dotenv
import os

# Khai báo đường dẫn đến Tesseract và Poppler
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

# Tạo FastAPI app
app = FastAPI()

# Cho phép gọi từ frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load biến môi trường từ .env
load_dotenv()

# Lấy API key
api_key = os.getenv("OPENAI_API_KEY")

# Khởi tạo client với API key từ .env
client = OpenAI(api_key=api_key)

# 🧠 Hàm gọi ChatGPT và nhận kết quả JSON
def query_chatgpt(text: str):
    prompt = (
        "Hãy đọc văn bản sau và trả về JSON với các trường: "
        "Loại văn bản, Đơn vị ban hành văn bản, Số và ký hiệu của văn bản, Ngày tháng năm ban hành, Trích yếu nội dung, Người ký, Số trang"
        "Chỉ trả về nội dung JSON, không có chú thích nào khác.\n\n"
        f"{text}"
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo", # chọn loại này rẻ nhất
        messages=[
            {"role": "system", "content": "Bạn là một trợ lý AI, chuyên tóm tắt và trích xuất thông tin từ văn bản."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3, #từ 0 đến 1, mức độ sáng tạo
    )

    reply_content = response.choices[0].message.content

    try:
        return json.loads(reply_content)
    except json.JSONDecodeError:
        return {
            "error": "Phản hồi không phải JSON hợp lệ.",
            "raw_response": reply_content
        }

# 📄 API nhận PDF, OCR, gửi GPT, trả JSON
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    contents = await file.read()
    images = convert_from_bytes(contents, poppler_path=POPPLER_PATH)

    text = ""
    for img in images:
        text += pytesseract.image_to_string(img, lang="vie") + "\n"
    
    gpt_result = query_chatgpt(text)
    return {"text_raw": text, "gpt_result": gpt_result}

