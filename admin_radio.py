import streamlit as st
import edge_tts
import asyncio
from github import Github
import json
import base64
import time
from datetime import datetime
import os

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Admin Radio Khuyến Nông", page_icon="🔒")

# --- KIỂM TRA MẬT KHẨU (LOGIN SYSTEM) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    try:
        if st.session_state.password_input == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
        else:
            st.error("❌ Sai mật khẩu! Vui lòng thử lại.")
    except:
        st.error("⚠️ Chưa cấu hình APP_PASSWORD trong Settings của Streamlit.")

if not st.session_state.authenticated:
    st.title("🔒 Đăng Nhập Hệ Thống")
    st.write("Vui lòng nhập mật khẩu quản trị để truy cập công cụ.")
    st.text_input("Mật khẩu:", type="password", key="password_input", on_change=check_password)
    st.stop()

# =================================================================================
# GIAO DIỆN QUẢN TRỊ VIÊN
# =================================================================================

st.title("🌾 Công Cụ Sản Xuất Radio Tự Động")
st.success("✅ Đã đăng nhập quyền Quản trị viên")

# --- KẾT NỐI GITHUB ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = "snnmt/radiokhuyennong" 
except:
    st.error("⚠️ Chưa cấu hình GITHUB_TOKEN! Hãy vào Settings của Streamlit để thêm.")
    st.stop()

# Cấu hình thư mục lưu trữ
FOLDER_AUDIO = "amthanh/"
FOLDER_IMAGE = "hinhanh/"
FOLDER_DOCS = "tailieu/" # Thư mục chứa PDF
FILE_JSON_DATA = "danh_sach_tai_lieu.json"

# --- HÀM XỬ LÝ ---

# 1. Hàm tạo file MP3
async def generate_audio(text, filename, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

# 2. Hàm Upload file lên GitHub (Dùng chung cho Ảnh và PDF)
def upload_file_to_github(file_obj, folder_path, repo):
    # Tạo tên file mới dựa trên thời gian để tránh trùng lặp
    file_ext = file_obj.name.split(".")[-1]
    new_filename = f"upload_{int(time.time())}.{file_ext}"
    git_path = f"{folder_path}{new_filename}"
    
    # Đọc dữ liệu file
    content = file_obj.getvalue()
    
    # Upload
    repo.create_file(git_path, f"Upload file: {new_filename}", content)
    
    # Trả về link raw
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/{git_path}"

# 3. Hàm xử lý chính (Biên tập & Phát sóng)
def process_upload(title, category, description, pdf_file, content_text, voice_choice, image_file):
    status = st.status("⏳ Đang xử lý phát sóng...", expanded=True)
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # --- BƯỚC A: XỬ LÝ FILE ĐÍNH KÈM (PDF & ẢNH) ---
    final_pdf_url = ""
    final_image_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/hinhanh/logo_mac_dinh.png"
    
    if pdf_file is not None:
        status.write(f"📄 Đang upload tài liệu PDF: {pdf_file.name}...")
        final_pdf_url = upload_file_to_github(pdf_file, FOLDER_DOCS, repo)
        
    if image_file is not None:
        status.write(f"🖼️ Đang upload ảnh minh họa: {image_file.name}...")
        final_image_url = upload_file_to_github(image_file, FOLDER_IMAGE, repo)
    
    # --- BƯỚC B: TẠO AUDIO ---
    status.write("🎙️ Đang chuyển văn bản thành giọng nói...")
    filename_mp3 = f"radio_{int(time.time())}.mp3"
    asyncio.run(generate_audio(content_text, filename_mp3, voice_choice))
    
    # --- BƯỚC C: UPLOAD MP3 ---
    status.write(f"⬆️ Đang tải file âm thanh lên...")
    with open(filename_mp3, "rb") as file:
        content = file.read()
    
    file_path_on_git = f"{FOLDER_AUDIO}{filename_mp3}"
    repo.create_file(file_path_on_git, f"Add audio: {title}", content)
    final_audio_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path_on_git}"
    
    # --- BƯỚC D: CẬP NHẬT JSON ---
    status.write("📝 Đang cập nhật danh sách bài viết...")
    
    try:
        file_content = repo.get_contents(FILE_JSON_DATA)
        json_str = base64.b64decode(file_content.content).decode("utf-8")
        data_list = json.loads(json_str)
    except Exception as e:
        # Nếu chưa có file json thì tạo list rỗng
        data_list = []

    # Tự động tăng ID
    new_id = 1
    if data_list:
        max_id = max(item.get('id', 0) for item in data_list)
        new_id = max_id + 1

    # Tạo Object mới
    new_item = {
        "id": new_id,
        "title": title,
        "category": category,
        "description": description,
        "pdf_url": final_pdf_url,
        "audio_url": final_audio_url,
        "image_url": final_image_url,
        "last_updated": datetime.now().strftime("%d/%m/%Y")
    }
    
    # Chèn lên đầu danh sách
    data_list.insert(0, new_item)
    
    # Upload lại JSON
    updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
    repo.update_file(file_content.path, f"Add post ID {new_id}: {title}", updated_json, file_content.sha)
    
    # Xóa file tạm mp3
    os.remove(filename_mp3)
    
    status.update(label="✅ ĐÃ XONG! Bài viết đã lên sóng.", state="complete", expanded=False)
    st.success(f"Đã đăng bài: {title} (ID: {new_id})")
    
    # Hiển thị kết quả để kiểm tra
    st.write("dữ liệu vừa tạo:")
    st.json(new_item)
    st.balloons()

# --- GIAO DIỆN FORM NHẬP LIỆU ---

with st.form("radio_form"):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("1. Tiêu đề bài viết", placeholder="VD: Kỹ thuật trồng Sầu Riêng...")
    with col2:
        category = st.selectbox("2. Chuyên mục", ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"])
    
    description = st.text_input("3. Mô tả ngắn", placeholder="VD: Hướng dẫn xử lý ra hoa...")
    
    # Ô Upload file PDF
    st.markdown("---")
    st.write("📁 **Tài liệu đính kèm**")
    pdf_file = st.file_uploader("4. Chọn file PDF (Nếu có)", type=["pdf"])
    
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("---")
        st.write("🎤 **Cấu hình giọng đọc**")
        voice_options = {"Nam (Miền Nam)": "vi-VN-NamMinhNeural", "Nữ (Miền Bắc)": "vi-VN-HoaiMyNeural"}
        voice_label = st.selectbox("5. Chọn giọng", list(voice_options.keys()))
        voice_code = voice_options[voice_label]
    with col4:
        st.markdown("---")
        st.write("🖼️ **Ảnh bìa bài viết**")
        image_file = st.file_uploader("6. Chọn ảnh (JPG/PNG)", type=["jpg", "png", "jpeg"])

    st.markdown("---")
    st.write("### 7. Nội dung bài viết (AI sẽ đọc nội dung này)")
    content_text = st.text_area("Dán văn bản vào đây:", height=300)
    
    # --- KHU VỰC NÚT BẤM ---
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        btn_preview = st.form_submit_button("🎧 NGHE THỬ TRƯỚC")
        
    with col_btn2:
        btn_publish = st.form_submit_button("🚀 BIÊN TẬP & PHÁT SÓNG")

    # XỬ LÝ SỰ KIỆN
    if btn_preview:
        if not content_text:
            st.warning("⚠️ Chưa có nội dung để đọc!")
        else:
            st.info("🎙️ Đang tạo bản nghe thử...")
            preview_file = "preview_audio.mp3"
            asyncio.run(generate_audio(content_text, preview_file, voice_code))
            st.audio(preview_file, format="audio/mp3")
            st.success("Nghe thử ở trên (File tạm).")

    if btn_publish:
        if not title or not content_text:
            st.warning("⚠️ Vui lòng nhập Tiêu đề và Nội dung!")
        else:
            process_upload(title, category, description, pdf_file, content_text, voice_code, image_file)
