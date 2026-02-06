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

async def generate_audio(text, filename, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def upload_file_to_github(file_obj, folder_path, repo):
    file_ext = file_obj.name.split(".")[-1]
    new_filename = f"up_{int(time.time())}.{file_ext}"
    git_path = f"{folder_path}{new_filename}"
    repo.create_file(git_path, f"Up: {new_filename}", file_obj.getvalue())
    return f"https://raw.githubusercontent.com/{REPO_NAME}/main/{git_path}"

# Hàm lấy dữ liệu JSON từ GitHub
def get_data_from_github():
    repo = get_github_repo()
    try:
        contents = repo.get_contents(FILE_JSON_DATA)
        json_str = base64.b64decode(contents.content).decode("utf-8")
        return json.loads(json_str), contents.sha
    except:
        return [], None

# Hàm cập nhật JSON lên GitHub
def push_json_to_github(data_list, sha, message):
    repo = get_github_repo()
    contents = repo.get_contents(FILE_JSON_DATA)
    updated_json = json.dumps(data_list, ensure_ascii=False, indent=4)
    repo.update_file(contents.path, message, updated_json, contents.sha)

# --- CHIA GIAO DIỆN THÀNH 2 TAB ---
tab1, tab2 = st.tabs(["➕ ĐĂNG BÀI MỚI", "🛠️ QUẢN LÝ & CHỈNH SỬA"])

# =================================================================================
# TAB 1: ĐĂNG BÀI MỚI (Code cũ)
# =================================================================================
with tab1:
    st.subheader("Soạn Thảo Bài Viết Mới")
    with st.form("new_post_form"):
        c1, c2 = st.columns(2)
        with c1:
            title = st.text_input("Tiêu đề bài viết")
            category = st.selectbox("Chuyên mục", ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"])
        with c2:
            description = st.text_input("Mô tả ngắn")
            pdf_file = st.file_uploader("File PDF (nếu có)", type=["pdf"])

        c3, c4 = st.columns(2)
        with c3:
            voice_opts = {"Nam (Miền Nam)": "vi-VN-NamMinhNeural", "Nữ (Miền Bắc)": "vi-VN-HoaiMyNeural"}
            voice_label = st.selectbox("Giọng đọc", list(voice_opts.keys()))
            voice_code = voice_opts[voice_label]
        with c4:
            image_file = st.file_uploader("Ảnh bìa (JPG/PNG)", type=["jpg", "png", "jpeg"])

        content_text = st.text_area("Nội dung bài viết (Text)", height=200)
        
        btn_submit = st.form_submit_button("🚀 PHÁT SÓNG NGAY")

        if btn_submit:
            if not title or not content_text:
                st.warning("Thiếu tiêu đề hoặc nội dung!")
            else:
                status = st.status("Đang xử lý...", expanded=True)
                repo = get_github_repo()
                
                # Upload files
                status.write("Upload file...")
                final_pdf = upload_file_to_github(pdf_file, FOLDER_DOCS, repo) if pdf_file else ""
                final_img = upload_file_to_github(image_file, FOLDER_IMAGE, repo) if image_file else f"https://raw.githubusercontent.com/{REPO_NAME}/main/hinhanh/logo_mac_dinh.png"
                
                # Audio
                status.write("Tạo âm thanh...")
                fname_mp3 = f"radio_{int(time.time())}.mp3"
                asyncio.run(generate_audio(content_text, fname_mp3, voice_code))
                with open(fname_mp3, "rb") as f:
                    repo.create_file(f"{FOLDER_AUDIO}{fname_mp3}", f"Audio: {title}", f.read())
                final_audio = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{FOLDER_AUDIO}{fname_mp3}"
                os.remove(fname_mp3)

                # Update JSON
                status.write("Lưu dữ liệu...")
                data, sha = get_data_from_github()
                new_id = (max([x['id'] for x in data]) + 1) if data else 1
                
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
# TAB 2: QUẢN LÝ (XEM / SỬA / XÓA)
# =================================================================================
with tab2:
    st.subheader("Danh Sách Bài Viết Đang Có")
    
    # Nút load dữ liệu thủ công để tiết kiệm request GitHub
    if st.button("🔄 Tải danh sách mới nhất từ GitHub"):
        data, _ = get_data_from_github()
        st.session_state.db_data = data
        st.rerun()

    # Lấy dữ liệu từ session
    current_data = st.session_state.get("db_data", [])

    if not current_data:
        st.info("Chưa có dữ liệu. Vui lòng bấm nút 'Tải danh sách' ở trên.")
    else:
        # Hiển thị bảng tóm tắt
        df = pd.DataFrame(current_data)
        st.dataframe(df[["id", "title", "category", "last_updated"]], use_container_width=True)

        st.markdown("---")
        st.subheader("🛠️ Thao Tác")

        # Chọn bài để thao tác
        list_ids = [f"{item['id']} - {item['title']}" for item in current_data]
        selected_option = st.selectbox("Chọn bài viết muốn Sửa hoặc Xóa:", list_ids)
        
        if selected_option:
            # Lấy ID từ chuỗi chọn
            selected_id = int(selected_option.split(" - ")[0])
            # Tìm object tương ứng
            selected_item = next((item for item in current_data if item["id"] == selected_id), None)

            if selected_item:
                with st.expander("📝 CHỈNH SỬA BÀI VIẾT NÀY", expanded=True):
                    with st.form("edit_form"):
                        new_title = st.text_input("Tiêu đề:", value=selected_item["title"])
                        new_desc = st.text_input("Mô tả:", value=selected_item["description"])
                        new_cat = st.selectbox("Chuyên mục:", ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"], index=["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"].index(selected_item["category"]) if selected_item["category"] in ["Trồng trọt", "Chăn nuôi", "Thủy sản", "Giá cả", "Tin tức"] else 0)
                        
                        st.markdown(f"**Ảnh hiện tại:** [Xem ảnh]({selected_item['image_url']})")
                        new_image = st.file_uploader("Thay ảnh mới (Bỏ qua nếu giữ nguyên)", type=["jpg", "png"])

                        st.markdown(f"**PDF hiện tại:** [Xem PDF]({selected_item['pdf_url']})")
                        new_pdf = st.file_uploader("Thay PDF mới (Bỏ qua nếu giữ nguyên)", type=["pdf"])

                        btn_save_edit = st.form_submit_button("💾 LƯU THAY ĐỔI")

                        if btn_save_edit:
                            status = st.status("Đang cập nhật...", expanded=True)
                            repo = get_github_repo()
                            
                            # Nếu có upload ảnh mới
                            if new_image:
                                selected_item["image_url"] = upload_file_to_github(new_image, FOLDER_IMAGE, repo)
                            
                            # Nếu có upload PDF mới
                            if new_pdf:
                                selected_item["pdf_url"] = upload_file_to_github(new_pdf, FOLDER_DOCS, repo)
                            
                            # Cập nhật thông tin text
                            selected_item["title"] = new_title
                            selected_item["description"] = new_desc
                            selected_item["category"] = new_cat
                            selected_item["last_updated"] = datetime.now().strftime("%d/%m/%Y")

                            # Ghi đè vào danh sách gốc và đẩy lên GitHub
                            # Cần lấy data mới nhất trước khi push để tránh conflict
                            full_data, sha = get_data_from_github()
                            # Tìm và thay thế trong list mới lấy về
                            for idx, item in enumerate(full_data):
                                if item["id"] == selected_id:
                                    full_data[idx] = selected_item
                                    break
                            
                            push_json_to_github(full_data, sha, f"Edit post ID {selected_id}")
                            st.session_state.db_data = full_data # Cập nhật local
                            status.update(label="✅ Đã cập nhật xong!", state="complete")
                            st.success("Cập nhật thành công! Hãy bấm 'Tải danh sách' để xem thay đổi.")

                # Phần XÓA BÀI VIẾT
                st.markdown("---")
                col_del1, col_del2 = st.columns([3, 1])
                with col_del2:
                    if st.button("🗑️ XÓA BÀI NÀY", type="primary"):
                        with st.spinner("Đang xóa dữ liệu..."):
                            full_data, sha = get_data_from_github()
                            # Lọc bỏ bài có ID này
                            filtered_data = [x for x in full_data if x["id"] != selected_id]
                            
                            push_json_to_github(filtered_data, sha, f"Delete post ID {selected_id}")
                            st.session_state.db_data = filtered_data
                            st.success(f"Đã xóa bài viết ID {selected_id}!")
                            time.sleep(1)
                            st.rerun()
