import streamlit as st
import edge_tts
import asyncio
from github import Github
import json
import base64
import time
from datetime import datetime
import os
import pandas as pd

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Admin Radio Khuyến Nông", page_icon="🌾", layout="wide")

# --- KIỂM TRA MẬT KHẨU ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    try:
        if st.session_state.password_input == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
        else:
            st.error("❌ Sai mật khẩu!")
    except:
        st.error("⚠️ Chưa cấu hình APP_PASSWORD trong Settings.")

if not st.session_state.authenticated:
    st.markdown("<h2 style='text-align: center;'>🔒 Đăng Nhập Hệ Thống</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.text_input("Mật khẩu quản trị:", type="password", key="password_input", on_change=check_password)
    st.stop()

# =================================================================================
# KHI ĐÃ ĐĂNG NHẬP
# =================================================================================

st.title("🌾 Hệ Thống Quản Trị Radio Khuyến Nông")

# --- KẾT NỐI GITHUB ---
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = "snnmt/radiokhuyennong" 
except:
    st.error("⚠️ Thiếu GITHUB_TOKEN.")
    st.stop()

FOLDER_AUDIO = "amthanh/"
FOLDER_IMAGE = "hinhanh/"
FOLDER_DOCS = "tailieu/"
FILE_JSON_DATA = "danh_sach_tai_lieu.json"

# --- CÁC HÀM HỖ TRỢ ---

def get_github_repo():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(REPO_NAME)

async def generate_audio(text, filename, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(filename)

def upload_file_to_github(file_obj, folder_path, repo, custom_name=None):
    if custom_name:
        new_filename = custom_name
    else:
        file_ext = file_obj.name.split(".")[-1]
        new_filename = f"up_{int(time.time())}.{file_ext}"
        
    git_path = f"{folder_path}{new_filename}"
    repo.create_file(git_path, f"Up: {new_filename}", file_obj.getvalue())
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/{git_path}"

def get_data_from_github():
    repo = get_github_repo()
    try:
        contents = repo.get_contents(FILE_JSON_DATA)
        json_str = base64.b64decode(contents.content).decode("utf-8")
        return json.loads(json_str), contents.sha
    except:
        return [], None

def push_json_to_github(data_list, sha, message):
    repo = get_github_repo()
    contents = repo.get_contents(FILE_JSON_DATA)
    updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
    repo.update_file(contents.path, message, updated_json, contents.sha)

# --- CHIA GIAO DIỆN THÀNH 2 TAB ---
tab1, tab2 = st.tabs(["➕ ĐĂNG BÀI MỚI", "🛠️ QUẢN LÝ & CHỈNH SỬA"])

# =================================================================================
# TAB 1: ĐĂNG BÀI MỚI (Đã bỏ Form để tương tác nhanh hơn)
# =================================================================================
with tab1:
    st.subheader("Soạn Thảo Bài Viết Mới")
    
    # 1. THÔNG TIN CƠ BẢN
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Tiêu đề bài viết")
        category = st.selectbox("Chuyên mục", ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"])
    with c2:
        description = st.text_input("Mô tả ngắn")
        pdf_file = st.file_uploader("File PDF (nếu có)", type=["pdf"])

    st.markdown("---")
    
    # 2. CHỌN NGUỒN ÂM THANH
    st.write("🎙️ **Cấu hình Âm thanh & Hình ảnh**")
    
    # Radio button nằm ngoài form sẽ kích hoạt load lại trang ngay lập tức khi chọn
    audio_source_options = ["🎙️ Tạo từ văn bản (AI)", "📁 Tải file có sẵn từ máy"]
    audio_source = st.radio("Chọn nguồn âm thanh:", audio_source_options, horizontal=True)
    
    content_text = ""
    uploaded_audio = None
    voice_code = "vi-VN-NamMinhNeural"
    speed_rate = "+0%"
    
    col_audio, col_image = st.columns([2, 1])
    
    with col_audio:
        # LOGIC HIỂN THỊ ĐỘNG
        if audio_source == audio_source_options[0]: # Chọn AI
            c_voice, c_speed = st.columns(2)
            with c_voice:
                voice_opts = {"Nam (Miền Nam)": "vi-VN-NamMinhNeural", "Nữ (Miền Bắc)": "vi-VN-HoaiMyNeural"}
                voice_label = st.selectbox("Giọng đọc:", list(voice_opts.keys()))
                voice_code = voice_opts[voice_label]
            with c_speed:
                speed_opts = {
                    "Bình thường (+0%)": "+0%",
                    "Hơi nhanh - Tin tức (+10%)": "+10%", 
                    "Nhanh - Khẩn cấp (+20%)": "+20%",
                    "Chậm - Kể chuyện (-10%)": "-10%"
                }
                speed_label = st.selectbox("Tốc độ đọc:", list(speed_opts.keys()), index=0)
                speed_rate = speed_opts[speed_label]
            
            content_text = st.text_area("Nội dung bài viết (AI sẽ đọc nội dung này):", height=200, placeholder="Dán văn bản vào đây...")
        
        else: # Chọn Tải file
            st.info("📂 Chế độ: Upload file âm thanh có sẵn")
            # Hiện ô upload file ngay lập tức
            uploaded_audio = st.file_uploader("Chọn file âm thanh (MP3/WAV/M4A):", type=["mp3", "wav", "m4a"])
            content_text = st.text_area("Nội dung văn bản (Để lưu trữ, không bắt buộc):", height=100)

    with col_image:
        image_file = st.file_uploader("Ảnh bìa (JPG/PNG)", type=["jpg", "png", "jpeg"])

    # --- KHU VỰC NÚT BẤM (Dùng st.button thường) ---
    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        # Nút nghe thử
        if st.button("🎧 NGHE THỬ / KIỂM TRA"):
            if audio_source == audio_source_options[0]: # AI
                if not content_text:
                    st.warning("⚠️ Chưa có nội dung văn bản để đọc!")
                else:
                    st.info(f"🎙️ Đang tạo bản nghe thử ({voice_label})...")
                    preview_filename = "preview_temp.mp3"
                    asyncio.run(generate_audio(content_text, preview_filename, voice_code, speed_rate))
                    with open(preview_filename, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
                    st.success("Nghe thử AI ở trên.")
                    os.remove(preview_filename)
            else: # File Upload
                if not uploaded_audio:
                    st.warning("⚠️ Chưa chọn file âm thanh!")
                else:
                    st.audio(uploaded_audio)
                    st.success("File âm thanh chuẩn bị upload.")

    with col_btn2:
        # Nút phát sóng
        if st.button("🚀 PHÁT SÓNG NGAY", type="primary"):
            # Kiểm tra đầu vào
            valid = True
            if not title:
                st.warning("⚠️ Thiếu tiêu đề!")
                valid = False
            
            if audio_source == audio_source_options[0] and not content_text:
                st.warning("⚠️ Thiếu nội dung văn bản để AI đọc!")
                valid = False
                
            if audio_source == audio_source_options[1] and not uploaded_audio:
                st.warning("⚠️ Chưa upload file âm thanh!")
                valid = False

            if valid:
                status = st.status("Đang xử lý...", expanded=True)
                repo = get_github_repo()
                
                # 1. Upload Ảnh & PDF
                status.write("Upload file đính kèm...")
                final_pdf = upload_file_to_github(pdf_file, FOLDER_DOCS, repo) if pdf_file else ""
                final_img = upload_file_to_github(image_file, FOLDER_IMAGE, repo) if image_file else f"https://raw.githubusercontent.com/{REPO_NAME}/main/hinhanh/logo_mac_dinh.png"
                
                # 2. Xử lý Âm thanh
                status.write("Xử lý âm thanh...")
                timestamp = int(time.time())
                
                if audio_source == audio_source_options[0]: # AI
                    fname_mp3 = f"radio_{timestamp}.mp3"
                    asyncio.run(generate_audio(content_text, fname_mp3, voice_code, speed_rate))
                    with open(fname_mp3, "rb") as f:
                        audio_content = f.read()
                    os.remove(fname_mp3)
                else: # File Upload
                    audio_content = uploaded_audio.getvalue()
                    ext = uploaded_audio.name.split(".")[-1]
                    fname_mp3 = f"radio_{timestamp}.{ext}"

                # Upload Audio lên GitHub
                repo.create_file(f"{FOLDER_AUDIO}{fname_mp3}", f"Audio: {title}", audio_content)
                final_audio = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_AUDIO}{fname_mp3}"

                # 3. Cập nhật JSON
                status.write("Cập nhật cơ sở dữ liệu...")
                data, sha = get_data_from_github()
                
                if data:
                    ids = [x.get('id', 0) for x in data] 
                    new_id = max(ids) + 1 if ids else 1
                else:
                    new_id = 1
                
                new_item = {
                    "id": new_id, "title": title, "category": category, "description": description,
                    "pdf_url": final_pdf, "audio_url": final_audio, "image_url": final_img,
                    "last_updated": datetime.now().strftime("%d/%m/%Y")
                }
                data.insert(0, new_item)
                push_json_to_github(data, sha, f"Add post: {title}")
                
                status.update(label="✅ Thành công!", state="complete")
                st.success(f"Đã đăng bài ID: {new_id}")

# =================================================================================
# TAB 2: QUẢN LÝ
# =================================================================================
with tab2:
    st.subheader("Danh Sách Bài Viết Đang Có")
    
    if st.button("🔄 Tải danh sách mới nhất từ GitHub"):
        data, _ = get_data_from_github()
        st.session_state.db_data = data
        st.rerun()

    current_data = st.session_state.get("db_data", [])

    if not current_data:
        st.info("Chưa có dữ liệu. Vui lòng bấm nút 'Tải danh sách' ở trên.")
    else:
        # Hiển thị bảng tóm tắt
        safe_data = []
        for item in current_data:
            safe_data.append({
                "id": item.get("id", "N/A"),
                "title": item.get("title", "Không tiêu đề"),
                "category": item.get("category", "Chưa phân loại"),
                "last_updated": item.get("last_updated", "")
            })
            
        df = pd.DataFrame(safe_data)
        st.dataframe(df, use_container_width=True)

        st.markdown("---")
        st.subheader("🛠️ Thao Tác")

        list_ids = []
        for item in current_data:
            i_id = item.get("id", "N/A")
            i_title = item.get("title", "No Title")
            list_ids.append(f"{i_id} - {i_title}")

        selected_option = st.selectbox("Chọn bài viết muốn Sửa hoặc Xóa:", list_ids)
        
        if selected_option:
            try:
                selected_id_str = selected_option.split(" - ")[0]
                selected_id = int(selected_id_str)
                selected_item = next((item for item in current_data if item.get("id") == selected_id), None)
            except:
                selected_item = None

            if selected_item:
                curr_title = selected_item.get("title", "")
                curr_desc = selected_item.get("description", "")
                curr_cat = selected_item.get("category", "Tin tức")
                curr_img = selected_item.get("image_url", "")
                curr_pdf = selected_item.get("pdf_url", "")
                
                cat_options = ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"]
                cat_index = 0
                if curr_cat in cat_options:
                    cat_index = cat_options.index(curr_cat)

                with st.expander("📝 CHỈNH SỬA BÀI VIẾT NÀY", expanded=True):
                    with st.form("edit_form"):
                        new_title = st.text_input("Tiêu đề:", value=curr_title)
                        new_desc = st.text_input("Mô tả:", value=curr_desc)
                        new_cat = st.selectbox("Chuyên mục:", cat_options, index=cat_index)
                        
                        if curr_img:
                            st.markdown(f"**Ảnh hiện tại:** [Xem ảnh]({curr_img})")
                        else:
                            st.warning("⚠️ Bài này chưa có ảnh")
                            
                        new_image = st.file_uploader("Thay ảnh mới (Bỏ qua nếu giữ nguyên)", type=["jpg", "png"])

                        if curr_pdf:
                            st.markdown(f"**PDF hiện tại:** [Xem PDF]({curr_pdf})")
                        new_pdf = st.file_uploader("Thay PDF mới (Bỏ qua nếu giữ nguyên)", type=["pdf"])

                        btn_save_edit = st.form_submit_button("💾 LƯU THAY ĐỔI")

                        if btn_save_edit:
                            status = st.status("Đang cập nhật...", expanded=True)
                            repo = get_github_repo()
                            
                            if new_image:
                                selected_item["image_url"] = upload_file_to_github(new_image, FOLDER_IMAGE, repo)
                            if new_pdf:
                                selected_item["pdf_url"] = upload_file_to_github(new_pdf, FOLDER_DOCS, repo)
                            
                            selected_item["title"] = new_title
                            selected_item["description"] = new_desc
                            selected_item["category"] = new_cat
                            selected_item["last_updated"] = datetime.now().strftime("%d/%m/%Y")

                            full_data, sha = get_data_from_github()
                            for idx, item in enumerate(full_data):
                                if item.get("id") == selected_id:
                                    item.update(selected_item)
                                    full_data[idx] = item
                                    break
                            
                            push_json_to_github(full_data, sha, f"Edit post ID {selected_id}")
                            st.session_state.db_data = full_data
                            status.update(label="✅ Đã cập nhật xong!", state="complete")
                            st.success("Cập nhật thành công! Hãy bấm 'Tải danh sách' để xem thay đổi.")

                st.markdown("---")
                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("🗑️ XÓA BÀI NÀY", type="primary"):
                        with st.spinner("Đang xóa dữ liệu..."):
                            full_data, sha = get_data_from_github()
                            filtered_data = [x for x in full_data if x.get("id") != selected_id]
                            
                            push_json_to_github(filtered_data, sha, f"Delete post ID {selected_id}")
                            st.session_state.db_data = filtered_data
                            st.success(f"Đã xóa bài viết ID {selected_id}!")
                            time.sleep(1)
                            st.rerun()
