from pathlib import Path
import os
import subprocess
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, jsonify, abort, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_FOLDER = BASE_DIR / "uploads"
THUMB_FOLDER = BASE_DIR / "thumbnails"
DB_PATH = BASE_DIR / "videos.db"

UPLOAD_FOLDER.mkdir(exist_ok=True)
THUMB_FOLDER.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {"mp4", "webm", "ogg", "mov", "avi", "mkv"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["THUMB_FOLDER"] = str(THUMB_FOLDER)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get("FLASK_SECRET", "change-me-in-prod")

db = SQLAlchemy(app)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(512), nullable=False)
    title = db.Column(db.String(256), default="")
    overlay_text = db.Column(db.Text, default="")
    thumbnail = db.Column(db.String(512), default="")  # relative filename in thumbnails/
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def file_path(self):
        return os.path.join(app.config["UPLOAD_FOLDER"], self.filename)

    def thumbnail_path(self):
        return os.path.join(app.config["THUMB_FOLDER"], self.thumbnail)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_thumbnail(video_path, thumb_path):
    """
    Try to run ffmpeg to extract a frame for thumbnail.
    Expects ffmpeg to be installed. If ffmpeg is missing or fails, return False.
    """
    try:
        # extract frame at 1 second
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-ss",
            "00:00:01.000",
            "-vframes",
            "1",
            str(thumb_path),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


@app.route("/")
def index():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return render_template("index.html", videos=videos)


@app.route("/upload", methods=["POST"])
def upload():
    # supports multiple file upload via input multiple
    if "files" not in request.files:
        flash("No files part", "warning")
        return redirect(url_for("index"))
    files = request.files.getlist("files")
    created = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Make unique filename if exists
            dest = UPLOAD_FOLDER / filename
            i = 1
            base, ext = os.path.splitext(filename)
            while dest.exists():
                filename = f"{base}_{i}{ext}"
                dest = UPLOAD_FOLDER / filename
                i += 1
            file.save(str(dest))

            # create thumbnail filename
            thumb_name = f"{Path(filename).stem}.jpg"
            thumb_path = THUMB_FOLDER / thumb_name

            # try ffmpeg
            ok = generate_thumbnail(dest, thumb_path)
            if not ok:
                # fallback to placeholder thumbnail
                thumb_name = "placeholder.jpg"
                # ensure placeholder exists (we won't generate it here, templates will fallback)
            video = Video(filename=filename, thumbnail=thumb_name, title=base)
            db.session.add(video)
            created.append(filename)
    db.session.commit()
    if created:
        flash(f"Uploaded {len(created)} file(s).", "success")
    else:
        flash("No allowed files uploaded.", "warning")
    return redirect(url_for("index"))


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/thumbnails/<path:filename>")
def thumbnail_file(filename):
    # If thumbnail doesn't exist, we serve a simple generic placeholder from static
    thumb_path = Path(app.config["THUMB_FOLDER"]) / filename
    if thumb_path.exists():
        return send_from_directory(app.config["THUMB_FOLDER"], filename)
    else:
        return send_from_directory("static", "img/placeholder.jpg")


@app.route("/video/<int:video_id>")
def video_detail(video_id):
    video = Video.query.get_or_404(video_id)
    return render_template("detail.html", video=video)


@app.route("/api/video/<int:video_id>/save_overlay", methods=["POST"])
def save_overlay(video_id):
    video = Video.query.get_or_404(video_id)
    data = request.get_json()
    if data is None:
        return jsonify({"error": "invalid json"}), 400
    overlay = data.get("overlay_text", "")
    title = data.get("title", "")
    video.overlay_text = overlay or ""
    video.title = title or video.title
    db.session.commit()
    return jsonify({"ok": True, "overlay_text": video.overlay_text})


@app.route("/api/video/<int:video_id>/delete", methods=["POST"])
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    # delete files
    try:
        fp = Path(video.file_path())
        if fp.exists():
            fp.unlink()
    except Exception:
        pass
    try:
        tp = Path(video.thumbnail_path())
        if tp.exists():
            tp.unlink()
    except Exception:
        pass
    db.session.delete(video)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/videos/bulk_delete", methods=["POST"])
def bulk_delete():
    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not isinstance(ids, list):
        return jsonify({"error": "ids must be a list"}), 400
    deleted = []
    for vid in ids:
        video = Video.query.get(vid)
        if video:
            try:
                fp = Path(video.file_path())
                if fp.exists():
                    fp.unlink()
            except Exception:
                pass
            try:
                tp = Path(video.thumbnail_path())
                if tp.exists():
                    tp.unlink()
            except Exception:
                pass
            db.session.delete(video)
            deleted.append(vid)
    db.session.commit()
    return jsonify({"ok": True, "deleted": deleted})


@app.route("/video/<int:video_id>/download")
def download_video(video_id):
    video = Video.query.get_or_404(video_id)
    return send_from_directory(app.config["UPLOAD_FOLDER"], video.filename, as_attachment=True)


def init_db():
    """
    Ensure the database tables exist. This must run inside an application context.
    Call init_db() at startup (or use flask CLI to manage migrations).
    """
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    # create DB tables within app context before running
    init_db()
    app.run(debug=True, port=5000)
