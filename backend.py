import os
import json
from flask import Flask, redirect, request, session, jsonify
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.oauth2.credentials
from flask_session import Session

# Ambil credential dari environment variable
GOOGLE_CREDENTIALS = json.loads(os.environ["GOOGLE_CREDENTIALS"])

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

@app.route("/login")
def login():
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            GOOGLE_CREDENTIALS, scopes=SCOPES
        )
        flow.redirect_uri = "https://hapuskomenjudol.onrender.com/callback"
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )
        session["state"] = state
        return redirect(authorization_url)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/callback")
def callback():
    try:
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            GOOGLE_CREDENTIALS, scopes=SCOPES, state=session.get("state")
        )
        flow.redirect_uri = "https://hapuskomenjudol.onrender.com/callback"
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        session["credentials"] = json.loads(credentials.to_json())
        return jsonify({"message": "Login successful! Now you can fetch comments."})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


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
