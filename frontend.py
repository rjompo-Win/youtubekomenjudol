import streamlit as st
import requests
import webbrowser
import json


# Gunakan URL Railway sebagai backend
BACKEND_URL = "https://youtubekomenjudol-production.up.railway.app"

st.title("🛡️ YouTube Comment Cleaner")

# Cek apakah user sudah login
try:
    response = requests.get(f"{BACKEND_URL}/get_status")
    response.raise_for_status()  # Cek jika error HTTP
    st.write(f"🔍 Debug: Response dari backend = {response.text}")  # Debugging
    status_response = response.json()  # Convert ke JSON
except requests.exceptions.RequestException as e:
    st.error(f"❌ Gagal menghubungi backend: {e}")
    st.stop()
except json.decoder.JSONDecodeError:
    st.error(f"❌ Backend tidak mengembalikan JSON yang valid: {response.text}")
    st.stop()

is_logged_in = status_response.get("logged_in", False)

if not is_logged_in:
    st.warning("⚠️ Anda belum login! Harap login terlebih dahulu sebelum menggunakan fitur ini.")
    if st.button("🔑 Login ke YouTube"):
        webbrowser.open(f"{BACKEND_URL}/login")
    st.stop()  # Hentikan semua proses jika belum login

# 2️⃣ Input untuk Video ID dan Kata Kunci
st.subheader("2️⃣ Masukkan Link Video YouTube & Kata Kunci Filter")
video_link = st.text_input("🔗 Masukkan Link Video YouTube", "")
keywords = st.text_area("📝 Kata Kunci untuk Filter (pisahkan dengan koma)", "judi, slot, bet")

if st.button("🔍 Ambil Komentar"):
    if not video_link:
        st.warning("⚠️ Masukkan link video terlebih dahulu!")
    else:
        video_id = video_link.split("v=")[-1]  # Ekstrak Video ID dari URL
        
        response = requests.post(f"{BACKEND_URL}/get_comments", json={
            "video_id": video_id,
            "keywords": [k.strip() for k in keywords.split(",")]
        })

        if response.status_code == 200:
            comments_data = response.json().get("comments", [])
            if comments_data:
                st.success("✅ Komentar berhasil diambil!")
                
                comment_ids_to_delete = []
                for comment in comments_data:
                    is_spam = comment["spam"]
                    delete_comment = st.checkbox(
                        f"{comment['author']}: {comment['text']}",
                        value=is_spam
                    )
                    if delete_comment:
                        comment_ids_to_delete.append(comment["comment_id"])
                
                if st.button("🗑️ Hapus Komentar yang Dipilih"):
                    for comment_id in comment_ids_to_delete:
                        delete_response = requests.post(f"{BACKEND_URL}/delete_comment", json={
                            "comment_id": comment_id
                        })
                        if delete_response.status_code == 200:
                            st.success(f"✅ Komentar {comment_id} berhasil dihapus!")
                        else:
                            st.error(f"❌ Gagal menghapus komentar {comment_id}")

            else:
                st.warning("⚠️ Tidak ada komentar yang ditemukan.")
        else:
            st.error("❌ Gagal mengambil komentar. Pastikan Anda sudah login.")
