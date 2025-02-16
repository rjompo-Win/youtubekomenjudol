import os
from flask import Flask, redirect, request, session, jsonify
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.oauth2.credentials
import json
from flask_session import Session  # Untuk menyimpan session agar tidak hilang setelah restart

# 🔧 Mengizinkan OAuth berjalan di HTTP (untuk testing lokal)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = "supersecretkey"

# 🛠️ Konfigurasi Flask-Session agar sesi tetap ada setelah restart
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

@app.route("/")
def index():
    return "YouTube Comment Cleaner API Running!"

# 1️⃣ Login ke YouTube API menggunakan OAuth
@app.route("/login")
def login():
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES
        )
        flow.redirect_uri = "http://127.0.0.1:5001/callback"
        
        # Debugging: Cetak redirect URI yang digunakan
        print(f"Redirect URI: {flow.redirect_uri}")

        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )
        session["state"] = state

        print(f"Authorization URL: {authorization_url}")  # Debugging
        return redirect(authorization_url)
    
    except Exception as e:
        print(f"Error in login: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 2️⃣ Callback setelah login berhasil
@app.route("/callback")
def callback():
    try:
        if "state" not in session:
            return jsonify({"error": "State is missing from session"}), 400
        
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=session.get("state")
        )
        flow.redirect_uri = "http://127.0.0.1:5001/callback"  # Ubah ke port 5001

        # Debugging: Cetak request URL untuk melihat masalahnya
        print("Authorization response:", request.url)

        # Ambil token dari Google
        flow.fetch_token(authorization_response=request.url)

        # Simpan token ke session
        credentials = flow.credentials
        session["credentials"] = json.loads(credentials.to_json())

        return jsonify({"message": "Login successful! Now you can fetch comments."})
    
    except Exception as e:
        print(f"Error in callback: {str(e)}")  # Debugging
        return jsonify({"error": str(e)}), 500

# 3️⃣ API untuk mendapatkan komentar berdasarkan video_id
@app.route("/get_comments", methods=["POST"])
def get_comments():
    if "credentials" not in session:
        return jsonify({"error": "User not logged in"}), 401

    credentials = google.oauth2.credentials.Credentials(**session["credentials"])
    youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    data = request.json
    video_id = data.get("video_id")
    keywords = data.get("keywords", [])

    if not video_id:
        return jsonify({"error": "Missing video_id parameter"}), 400

    comments = []
    request_data = youtube.commentThreads().list(
        part="snippet", videoId=video_id, textFormat="plainText", maxResults=100
    )
    response = request_data.execute()

    for item in response.get("items", []):
        comment = item["snippet"]["topLevelComment"]["snippet"]
        text = comment["textDisplay"]
        contains_spam = any(keyword.lower() in text.lower() for keyword in keywords)

        comments.append({
            "comment_id": item["id"],
            "text": text,
            "author": comment["authorDisplayName"],
            "spam": contains_spam,
        })

    return jsonify({"comments": comments})

# 4️⃣ API untuk menghapus komentar berdasarkan comment_id
@app.route("/delete_comment", methods=["POST"])
def delete_comment():
    if "credentials" not in session:
        return jsonify({"error": "User not logged in"}), 401

    credentials = google.oauth2.credentials.Credentials(**session["credentials"])
    youtube = googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    data = request.json
    comment_id = data.get("comment_id")

    if not comment_id:
        return jsonify({"error": "Missing comment_id parameter"}), 400

    youtube.comments().delete(id=comment_id).execute()

    return jsonify({"message": "Comment deleted successfully"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)  # Menggunakan port 5001 untuk menghindari konflik
