import streamlit as st
import edge_tts
import asyncio
from github import Github
import json
import base64
import time
from datetime import datetime
import os

# --- CẤU HÌNH ---
st.set_page_config(page_title="Admin Radio Khuyến Nông", page_icon="🌾")
st.title("🌾 Công Cụ Sản Xuất Radio Tự Động")

# --- KẾT NỐI GITHUB ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = "snnmt/radiokhuyennong" 
except:
    st.error("⚠️ Chưa cấu hình Token! Hãy vào Settings của Streamlit để thêm GITHUB_TOKEN.")
    st.stop()

FOLDER_AUDIO = "amthanh/"
FILE_JSON_DATA = "danh_sach_tai_lieu.json"

# --- HÀM XỬ LÝ ---

# 1. Hàm tạo file MP3
async def generate_audio(text, filename, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

# 2. Hàm xử lý chính
def process_upload(title, category, description, pdf_url_input, content_text, voice_choice, image_url_input):
    status = st.status("⏳ Đang xử lý...", expanded=True)
    
    # --- BƯỚC A: TẠO AUDIO ---
    status.write("🎙️ Đang chuyển văn bản thành giọng nói...")
    filename_mp3 = f"radio_{int(time.time())}.mp3"
    asyncio.run(generate_audio(content_text, filename_mp3, voice_choice))
    
    # --- BƯỚC B: KẾT NỐI GITHUB ---
    status.write("🚀 Đang kết nối GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # --- BƯỚC C: UPLOAD MP3 ---
    status.write(f"⬆️ Đang tải file âm thanh lên...")
    with open(filename_mp3, "rb") as file:
        content = file.read()
    
    file_path_on_git = f"{FOLDER_AUDIO}{filename_mp3}"
    repo.create_file(file_path_on_git, f"Add audio: {title}", content)
    
    # --- BƯỚC D: CẬP NHẬT JSON ---
    status.write("📝 Đang cập nhật danh sách bài viết...")
    
    try:
        file_content = repo.get_contents(FILE_JSON_DATA)
        json_str = base64.b64decode(file_content.content).decode("utf-8")
        data_list = json.loads(json_str)
    except Exception as e:
        st.error(f"Lỗi đọc file JSON: {e}")
        st.stop()

    # Tự động tăng ID
    new_id = 1
    if data_list:
        # Lấy ID lớn nhất hiện có + 1
        max_id = max(item.get('id', 0) for item in data_list)
        new_id = max_id + 1

    # Link file âm thanh chuẩn
    final_audio_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{file_path_on_git}"
    
    # Xử lý ảnh mặc định nếu để trống
    final_image_url = image_url_input if image_url_input else f"https://raw.githubusercontent.com/{REPO_NAME}/main/hinhanh/logo_mac_dinh.png"

    # --- TẠO OBJECT MỚI (Khớp 100% cấu trúc anh yêu cầu) ---
    new_item = {
        "id": new_id,
        "title": title,
        "category": category,
        "description": description,
        "pdf_url": pdf_url_input, # Link PDF anh nhập vào
        "audio_url": final_audio_url,
        "image_url": final_image_url,
        "last_updated": datetime.now().strftime("%d/%m/%Y") # Ví dụ: 24/01/2026
    }
    
    # Chèn lên đầu danh sách
    data_list.insert(0, new_item)
    
    # Upload lại JSON
    updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
    repo.update_file(file_content.path, f"Add post ID {new_id}: {title}", updated_json, file_content.sha)
    
    # Xóa file tạm
    os.remove(filename_mp3)
    
    status.update(label="✅ ĐÃ XONG! Bài viết đã lên sóng.", state="complete", expanded=False)
    st.success(f"Đã đăng bài: {title} (ID: {new_id})")
    st.json(new_item) # Hiển thị lại kết quả JSON vừa tạo để kiểm tra
    st.balloons()

# --- GIAO DIỆN FORM ---

with st.form("radio_form"):
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("1. Tiêu đề bài viết", placeholder="VD: Kỹ thuật trồng Sầu Riêng...")
    with col2:
        category = st.selectbox("2. Chuyên mục", ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"])
    
    description = st.text_input("3. Mô tả ngắn", placeholder="VD: Hướng dẫn xử lý ra hoa...")
    
    # Thêm ô nhập Link PDF
    pdf_url_input = st.text_input("4. Link tài liệu PDF (Nếu có)", placeholder="Dán link PDF từ GitHub hoặc để trống")
    
    col3, col4 = st.columns(2)
    with col3:
        # Chọn giọng đọc
        voice_options = {"Nam (Miền Nam)": "vi-VN-NamMinhNeural", "Nữ (Miền Bắc)": "vi-VN-HoaiMyNeural"}
        voice_label = st.selectbox("5. Giọng đọc AI", list(voice_options.keys()))
        voice_code = voice_options[voice_label]
    with col4:
        image_url = st.text_input("6. Link ảnh minh họa", placeholder="Để trống sẽ dùng ảnh mặc định")

    st.markdown("---")
    st.write("### 7. Nội dung bài viết (Để AI đọc)")
    content_text = st.text_area("Dán văn bản vào đây:", height=300)
    
    submitted = st.form_submit_button("🚀 BIÊN TẬP & PHÁT SÓNG")
    
    if submitted:
        if not title or not content_text:
            st.warning("⚠️ Vui lòng nhập Tiêu đề và Nội dung!")
        else:
            process_upload(title, category, description, pdf_url_input, content_text, voice_code, image_url)
