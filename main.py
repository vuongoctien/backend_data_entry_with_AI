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
        "Tôi gửi bạn 1 văn bản  và 1 hướng dẫn nhập liệu. Văn bản này đã được ORC từ bản scan của 1 văn bản hành chính: "
        f""
        f"{text}"
        f""
        "Bạn đọc văn bản này và trả về JSON với các trường: "
        "loai_van_ban, don_vi_hanh_chinh, so_va_ky_hieu, ngay_ban_hanh, trich_yeu_noi_dung, nguoi_ky"
        "Trong đó các trường thông tin này được xác định như sau:"
            "loai_van_ban: Ghi đúng tên loại văn bản như: Tờ trình, Quyết định, Thông báo, Công văn, Biên bản, Giấy mời, v.v. Lưu ý: Nếu văn bản không ghi rõ loại văn bản, hãy căn cứ vào cách trình bày, cấu trúc để xác định loại văn bản phù hợp nhất. Ví dụ: Có mục 'Kính gửi' và Dưới phần 'Số và ký hiệu' có nội dung 'Về việc' thì thường là Công văn; Có nội dung đề xuất thì thường là Tờ trình."
            "don_vi_hanh_chinh: Ghi tên cơ quan, tổ chức ban hành văn bản theo đúng tên được thể hiện trong văn bản. "
        "Nếu là văn bản liên tịch do nhiều cơ quan ban hành thì ghi tất cả các cơ quan ban hành, tên của mỗi cơ quan cách nhau bởi dấu chấm phẩy (;)."
        "Nếu dòng chữ IN ĐẬM bên dưới đứng một mình mà đủ thông tin để người đọc hiểu cơ quan ban hành là ai, ở đâu: thì chỉ nhập dòng IN ĐẬM "
        "Nếu dòng chữ bên dưới đứng một mình không đủ thông tin để người đọc hiểu cơ quan ban hành ở đâu, thì nhập thêm địa chỉ ở dòng bên trên vào."
        "-Ví dụ có nhiều cơ quan ban hành: "
        "PHÒNG TÀI NGUYÊN VÀ MÔI TRƯỜNG"
        "PHÒNG TÀI CHÍNH KẾ HOẠCH"
        "=> Phòng Tài nguyên và Môi trường; Phòng Tài chính kế hoạch"
        "Ví dụ khi dòng bên dưới đã đủ thông tin thì lấy dòng bên dưới đó:"
        "UBND THÀNH PHỐ HẢI PHÒNG"
        "PHÒNG TNMT QUẬN HẢI AN"
        "=> Phòng TNMT quận Hải An"
        "-Ví dụ Dòng bên dưới chưa đủ thông tin thì lấy thêm thông tin dòng bên trên:"
        "UỶ BAN NHÂN DÂN QUẬN HẢI AN"
        "TIỂU BAN KHÁNH THIẾT"
        "=>Tiểu ban khánh tiết quận Hải An"
            "so_va_ky_hieu: Thường nằm ở góc trái, dưới tên đơn vị ban hành văn bản. Ghi đầy đủ cả số và ký hiệu. Không có thì bỏ trống. Ví dụ: 05/TTr-VHTT 152/QĐ-UBND"
            "ngay_ban_hanh: Mặc định dd/mm/yyyy Thường nằm ở góc phải bên trên dưới Tiêu ngữ hoặc phía cuối bên trên chữ ký và con dấu, đối với thường sẽ ghi bắt đầu bằng: Địa danh, ngày…tháng...năm…"
        "Trường hợp phiếu chỉ có tháng và năm nhập theo định dạng: MM/YYYY -	Trường hợp phiếu chỉ có năm nhập theo định dạng: YYYY"
        "Trường hợp phiếu chỉ có ngày và năm => chỉ cần nhập năm định dạng: YYYY"
        "Trường hợp phiếu chỉ có ngày và tháng, không có năm => bỏ trống. "
        "Không có bỏ trống"
            "trich_yeu_noi_dung:"
        "Tóm tắt trong 2-3 câu. Ghi đúng trích yếu nội dung của văn bản, tài liệu. Đối với văn bản tài liệu không có trích yếu nội dung thì người nhập phải đọc và tóm tắt nội dung của văn bản, tài liệu đó theo form: Về việc gì + cho ai/đối tượng nào/ở đâu/đến đâu."
        "(Lưu ý: Bắt buộc phải thêm đối tượng, VD: Quyết định ... cho ai)"
        "Trường hợp văn bản có nhiều trang gồm nhiều loại văn bản khác nhau thì nhập trích yếu theo nội dung của văn bản đầu tiên."
        "Ví dụ: Quyết định về việc nâng lương cho cán bộ, công chức đối với ông Nguyễn Văn A, công tác tại Trường THPT Tiên Lãng."
        "Dạng tài liệu đóng quyển thì ghi trích yếu nội dung theo tờ bìa của quyển đó."
        "Trường hợp văn bản mà nội dung đề cập có từ 06 người (hay từ 06 cơ quan, tổ chức) trở lên, bên cạnh nhập trích yếu nội dung cần chú ý nhập số lượng 03 người ( hay số lượng 03 cơ quan, tổ chức) kèm dấu “…”. Số lượng người ( hay số lượng cơ quan, tổ chức) được đặt trong dấu ngoặc đơn."
        "Vd: V/v xếp hạng doanh nghiệp nhà nước (Công ty A; Công ty B; Công ty C…) “06 Công ty”"
            "nguoi_ky: Ghi đầy đủ họ tên người ký. Cuối văn bản, dưới chức danh (ví dụ Trưởng phòng, Hiệu trưởng, Chủ tịch) thường có tên của người ký. Ghi đúng và đầy đủ họ tên người ký, thường nằm dưới dấu đỏ."
        "\n\n"
        "Chỉ trả về nội dung JSON, không có chú thích nào khác."
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

