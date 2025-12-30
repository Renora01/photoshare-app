from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sqlite3
import uuid

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_FILE = "photos.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Photos table with likes
    c.execute('''CREATE TABLE IF NOT EXISTS photos
                 (id TEXT PRIMARY KEY, title TEXT, caption TEXT, filename TEXT, likes INTEGER DEFAULT 0)''')
    # Comments table
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, photo_id TEXT, comment TEXT)''')
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# FIXED UPLOAD ROUTE
# -----------------------------
@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    # FIX: Expect "photo" instead of "file"
    if 'photo' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['photo']
    title = request.form.get("title", "")
    caption = request.form.get("caption", "")

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    photo_id = str(uuid.uuid4())
    filename = photo_id + "_" + file.filename
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO photos (id, title, caption, filename) VALUES (?, ?, ?, ?)",
              (photo_id, title, caption, filename))
    conn.commit()
    conn.close()

    return jsonify({"message": "Photo uploaded", "photo_id": photo_id})


@app.route("/list_photos", methods=["GET"])
def list_photos():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, caption, filename, likes FROM photos")
    rows = c.fetchall()
    conn.close()
    photos = [{"id": r[0], "title": r[1], "caption": r[2], "url": f"/uploads/{r[3]}", "likes": r[4]} for r in rows]
    return jsonify(photos)


@app.route("/search")
def search_photos():
    query = request.args.get("q", "")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, caption, filename, likes FROM photos WHERE title LIKE ? OR caption LIKE ?",
              (f"%{query}%", f"%{query}%"))
    rows = c.fetchall()
    conn.close()
    results = [{"id": r[0], "title": r[1], "caption": r[2], "url": f"/uploads/{r[3]}", "likes": r[4]} for r in rows]
    return jsonify(results)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# Add a comment
@app.route("/add_comment", methods=["POST"])
def add_comment():
    data = request.json
    photo_id = data.get("photo_id")
    comment = data.get("comment")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO comments (photo_id, comment) VALUES (?, ?)", (photo_id, comment))
    conn.commit()
    conn.close()
    return jsonify({"status": "comment added"})


# Get comments for a photo
@app.route("/get_comments/<photo_id>")
def get_comments(photo_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT comment FROM comments WHERE photo_id = ?", (photo_id,))
    rows = c.fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])


# Like a photo
@app.route("/like_photo/<photo_id>", methods=["POST"])
def like_photo(photo_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE photos SET likes = likes + 1 WHERE id = ?", (photo_id,))
    conn.commit()
    c.execute("SELECT likes FROM photos WHERE id = ?", (photo_id,))
    likes = c.fetchone()[0]
    conn.close()
    return jsonify({"likes": likes})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
