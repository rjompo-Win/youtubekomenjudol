import os
import json
from flask import Flask, redirect, request, session, jsonify
import google_auth_oauthlib.flow
import googleapiclient.discovery
import google.oauth2.credentials
from flask_session import Session

# Paksa OAuth untuk menerima HTTP jika belum HTTPS
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Ambil credential dari environment variable
GOOGLE_CREDENTIALS = json.loads(os.environ["GOOGLE_CREDENTIALS"])

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Redirect backend ke frontend Streamlit
FRONTEND_URL = "https://hapuskomenjudol.streamlit.app"

@app.route("/")
def index():
    return redirect(FRONTEND_URL)

@app.route("/login")
def login():
    try:
        backend_url = os.environ.get("BACKEND_URL", "https://youtubekomenjudol-production.up.railway.app")
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            GOOGLE_CREDENTIALS, scopes=SCOPES
        )
        flow.redirect_uri = backend_url + "/callback"
        
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )
        session["state"] = state
        session.modified = True  # Pastikan session tidak hilang
        return redirect(authorization_url)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/callback")
def callback():
    try:
        backend_url = os.environ.get("BACKEND_URL", "https://youtubekomenjudol-production.up.railway.app")
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            GOOGLE_CREDENTIALS, scopes=SCOPES, state=session.get("state")
        )
        flow.redirect_uri = backend_url + "/callback"
        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials
        session["credentials"] = json.loads(credentials.to_json())

        # 🚀 Redirect langsung ke frontend setelah login sukses!
        return redirect("https://hapuskomenjudol.streamlit.app/")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

@app.route("/get_status")
def get_status():
    if "credentials" in session:
        return jsonify({"logged_in": True})
    else:
        return jsonify({"logged_in": False})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Railway default port
    app.run(host="0.0.0.0", port=port, debug=True)
