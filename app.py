import os
import re
import hmac
import time
import secrets
from urllib.parse import quote

from flask import (Flask, render_template, url_for, request, session,
                   redirect, abort, flash)
from sqlalchemy import create_engine, text

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or ("pf-" + os.environ.get("ADMIN_PASSWORD", "dev"))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # sirf forms (video Cloudinary pe jata hai)

# ====== SIRF YAHAN EDIT KARO ======
PROFILE = {
    "name": "Rahul Bunker",
    "tagline": "Video Editor & Content Writer",
    "intro": "I create AI reels and short videos, and write scripts, captions and blogs in Hindi, Hinglish and English.",
    "whatsapp": "",      # e.g. "919999999999"  (country code ke saath, + ke bina)
    "email": "",         # e.g. "you@gmail.com"
    "instagram": "",     # full link
    "linkedin": "",      # full link
    "drive_samples": "", # Google Drive / Docs ka link
}

# Ye list sirf BACKUP hai: jab database mein ek bhi video nahi hoti tab dikhti hai.
# Videos ab /admin se add karo.
VIDEOS = [
    {"title": "Meri Reel 1", "type": "Reel", "desc": "AI visuals with voiceover.", "thumb": "../f1.jpg", "url": ""},
    {"title": "Meri Reel 2", "type": "Reel", "desc": "Short reel edited in InShot.", "thumb": "../i1.jpg", "url": ""},
    {"title": "Diwali Highlights", "type": "Event film", "desc": "Festive highlight film with music sync.", "thumb": "../d1.jpg", "url": ""},
]

WRITING = [
    {"type": "Blog", "title": "5 Simple Ways to Build a Morning Routine That Sticks",
     "text": "A good morning does not need a perfect plan. It needs a few small habits you can repeat every day. Wake up at the same time, drink water before checking your phone, move for ten minutes and write down your top three tasks."},
    {"type": "Reel Script", "title": "3 Phone Battery Saving Tips",
     "text": "Is your phone battery dying too fast? Tip 1: turn on auto brightness. Tip 2: close background apps. Tip 3: switch on dark mode. Try these today and follow for more simple tech tips."},
    {"type": "Instagram Caption", "title": "Small Steps",
     "text": "Every big goal starts with one small step. Take that step today, and your future self will thank you. Which step will you take today? Tell us in the comments."},
    {"type": "Product Description", "title": "Light Cotton Kurta",
     "text": "Stay cool and comfortable all day in this lightweight cotton kurta. Soft, breathable fabric, a relaxed fit and a clean finish make it perfect for office, festivals and everyday wear."},
    {"type": "Hindi Caption", "title": "छोटा कदम",
     "text": "हर बड़ी मंज़िल एक छोटे कदम से शुरू होती है। आज वह कदम उठाइए, कल आपको खुद पर गर्व होगा। आप आज कौन सा कदम उठाएंगे? कमेंट में बताइए।"},
]

VIDEO_SERVICES = ["Reels & Shorts", "AI-generated visuals", "YouTube videos", "Event & wedding films", "Captions & subtitles", "Thumbnails"]
WRITING_SERVICES = ["Reel & short scripts", "Social media captions", "Blog articles", "Product descriptions", "Hindi & Hinglish copy", "Email & ad copy"]
# ==================================

# ---------- Render ke Environment Variables se aate hain ----------
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
UPLOAD_PRESET = os.environ.get("CLOUDINARY_UPLOAD_PRESET", "")
DB_URL = os.environ.get("DATABASE_URL", "")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=280) if DB_URL else None

VIDEO_TYPES = ["Reel", "YouTube", "Event film", "Short film", "Other"]


def init_db():
    if not engine:
        return
    try:
        pk = "SERIAL PRIMARY KEY" if engine.dialect.name == "postgresql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        with engine.begin() as c:
            c.execute(text(
                "CREATE TABLE IF NOT EXISTS videos ("
                "id " + pk + ", title TEXT NOT NULL, vtype TEXT, description TEXT, "
                "source TEXT NOT NULL, video_url TEXT NOT NULL, thumb_url TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
            c.execute(text(
                "CREATE TABLE IF NOT EXISTS articles ("
                "id " + pk + ", title TEXT NOT NULL, wtype TEXT, body TEXT, file_url TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"))
    except Exception as e:  # site chalta rahe, chahe DB na ho
        app.logger.error("DB init failed: %s", e)


def db_all():
    if not engine:
        return []
    try:
        with engine.connect() as c:
            rows = c.execute(text("SELECT * FROM videos ORDER BY id DESC")).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as e:
        app.logger.error("DB read failed: %s", e)
        return []


def db_one(vid):
    if not engine:
        return None
    try:
        with engine.connect() as c:
            r = c.execute(text("SELECT * FROM videos WHERE id = :i"), {"i": vid}).fetchone()
        return dict(r._mapping) if r else None
    except Exception as e:
        app.logger.error("DB read failed: %s", e)
        return None


def art_all():
    if not engine:
        return []
    try:
        with engine.connect() as c:
            rows = c.execute(text("SELECT * FROM articles ORDER BY id DESC")).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception as e:
        app.logger.error("DB read failed: %s", e)
        return []


def art_one(aid):
    if not engine:
        return None
    try:
        with engine.connect() as c:
            r = c.execute(text("SELECT * FROM articles WHERE id = :i"), {"i": aid}).fetchone()
        return dict(r._mapping) if r else None
    except Exception as e:
        app.logger.error("DB read failed: %s", e)
        return None


def acard(r):
    body = r["body"] or ""
    return {"id": r["id"], "title": r["title"], "type": r["wtype"] or "Article", "body": body,
            "excerpt": (body[:220] + "...") if len(body) > 220 else body,
            "file_url": r["file_url"] or "", "date": str(r["created_at"])[:10]}


init_db()


# ---------- video helpers ----------
def link_embed(url):
    """(embed_url, auto_thumb) for YouTube / Drive / Facebook links."""
    yt = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|shorts/|embed/))([\w-]{11})", url)
    dr = re.search(r"drive\.google\.com/file/d/([\w-]+)", url)
    if yt:
        return ("https://www.youtube.com/embed/" + yt.group(1) + "?autoplay=1&rel=0",
                "https://img.youtube.com/vi/" + yt.group(1) + "/hqdefault.jpg")
    if dr:
        return "https://drive.google.com/file/d/" + dr.group(1) + "/preview", ""
    if "facebook.com" in url or "fb.watch" in url:
        return ("https://www.facebook.com/plugins/video.php?href=" + quote(url, safe="")
                + "&show_text=false&autoplay=true", "")
    return "", ""


def cloud_thumb(url, sec=1):
    if "/upload/" not in url:
        return ""
    try:
        sec = max(0, int(sec))
    except (TypeError, ValueError):
        sec = 1
    t = url.replace("/upload/", "/upload/so_%d,w_800,h_450,c_fill/" % sec, 1)
    return re.sub(r"\.\w+$", ".jpg", t)


def prepare_video(v):
    """Backup list (VIDEOS) ke liye."""
    v = dict(v)
    url = v.get("url", "")
    v["id"] = None
    v["embed"], auto = link_embed(url)
    v["thumb_url"] = url_for("static", filename="thumbs/" + v["thumb"]) if v.get("thumb") else auto
    return v


def card(r):
    v = {"id": r["id"], "title": r["title"], "type": r["vtype"] or "Video",
         "desc": r["description"] or "", "source": r["source"], "url": r["video_url"],
         "thumb_url": r["thumb_url"] or "", "embed": "", "date": str(r["created_at"])[:10]}
    if r["source"] == "link":
        v["embed"], auto = link_embed(r["video_url"])
        if not v["thumb_url"]:
            v["thumb_url"] = auto
    elif not v["thumb_url"]:
        v["thumb_url"] = cloud_thumb(r["video_url"])
    return v


def ok_url(u, cloud_only=False):
    if cloud_only:
        return u.startswith("https://res.cloudinary.com/")
    return u.startswith("https://") or u.startswith("http://")


# ---------- public pages ----------
@app.context_processor
def inject_profile():
    return {"p": PROFILE}


@app.route("/")
def home():
    return render_template("index.html", vs=VIDEO_SERVICES, ws=WRITING_SERVICES)


@app.route("/video-editing")
def video():
    rows = db_all()
    videos = [card(r) for r in rows] if rows else [prepare_video(v) for v in VIDEOS]
    return render_template("video.html", videos=videos, vs=VIDEO_SERVICES)


@app.route("/watch/<int:vid>")
def watch(vid):
    r = db_one(vid)
    if not r:
        abort(404)
    others = [card(o) for o in db_all() if o["id"] != vid][:8]
    return render_template("watch.html", v=card(r), others=others)


@app.route("/content-writing")
def writing():
    rows = art_all()
    items = [acard(r) for r in rows]
    return render_template("writing.html", items=items, samples=WRITING, ws=WRITING_SERVICES)


@app.route("/article/<int:aid>")
def article(aid):
    r = art_one(aid)
    if not r:
        abort(404)
    return render_template("article.html", a=acard(r))


# ---------- admin ----------
def is_admin():
    return session.get("admin") is True


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


def check_csrf():
    if not hmac.compare_digest(request.form.get("csrf", ""), session.get("csrf", "x")):
        abort(400)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if not ADMIN_PASSWORD:
            flash("Render me ADMIN_PASSWORD set nahi hai.")
        elif hmac.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("admin"))
        else:
            time.sleep(1)
            flash("Password galat hai.")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
def admin():
    if not is_admin():
        return redirect(url_for("admin_login"))
    return render_template("admin.html", videos=[card(r) for r in db_all()], types=VIDEO_TYPES,
                           csrf=csrf_token(), cloud=CLOUD_NAME, preset=UPLOAD_PRESET, db_ok=bool(engine))


@app.route("/admin/add", methods=["POST"])
def admin_add():
    if not is_admin():
        abort(403)
    check_csrf()
    f = request.form
    title = f.get("title", "").strip()[:120]
    source = "file" if f.get("source") == "file" else "link"
    url = (f.get("video_url", "") if source == "file" else f.get("link_url", "")).strip()
    thumb = f.get("thumb_url", "").strip()
    if not title or not ok_url(url, cloud_only=(source == "file")):
        flash("Title aur sahi video chahiye.")
        return redirect(url_for("admin"))
    if thumb and not ok_url(thumb, cloud_only=True):
        thumb = ""
    if not thumb and source == "file":
        thumb = cloud_thumb(url, f.get("thumb_sec", 1))
    vtype = f.get("vtype") if f.get("vtype") in VIDEO_TYPES else "Other"
    try:
        with engine.begin() as c:
            c.execute(text("INSERT INTO videos (title, vtype, description, source, video_url, thumb_url) "
                           "VALUES (:t, :v, :d, :s, :u, :th)"),
                      {"t": title, "v": vtype, "d": f.get("description", "").strip()[:500],
                       "s": source, "u": url, "th": thumb})
        flash("Video save ho gaya.")
    except Exception as e:
        app.logger.error("insert failed: %s", e)
        flash("Database error. DATABASE_URL check karo.")
    return redirect(url_for("admin"))


@app.route("/admin/edit/<int:vid>", methods=["GET", "POST"])
def admin_edit(vid):
    if not is_admin():
        return redirect(url_for("admin_login"))
    r = db_one(vid)
    if not r:
        abort(404)
    if request.method == "POST":
        check_csrf()
        f = request.form
        thumb = f.get("thumb_url", "").strip()
        if thumb and ok_url(thumb, cloud_only=True):
            new_thumb = thumb
        elif f.get("auto") and r["source"] == "file":
            new_thumb = cloud_thumb(r["video_url"], f.get("thumb_sec", 1))
        else:
            new_thumb = r["thumb_url"] or ""
        vtype = f.get("vtype") if f.get("vtype") in VIDEO_TYPES else "Other"
        try:
            with engine.begin() as c:
                c.execute(text("UPDATE videos SET title=:t, vtype=:v, description=:d, thumb_url=:th WHERE id=:i"),
                          {"t": f.get("title", "").strip()[:120] or r["title"], "v": vtype,
                           "d": f.get("description", "").strip()[:500], "th": new_thumb, "i": vid})
            flash("Update ho gaya.")
        except Exception as e:
            app.logger.error("update failed: %s", e)
            flash("Database error.")
        return redirect(url_for("admin"))
    return render_template("admin_edit.html", v=card(r), types=VIDEO_TYPES, csrf=csrf_token(),
                           cloud=CLOUD_NAME, preset=UPLOAD_PRESET)


@app.route("/admin/delete/<int:vid>", methods=["POST"])
def admin_delete(vid):
    if not is_admin():
        abort(403)
    check_csrf()
    try:
        with engine.begin() as c:
            c.execute(text("DELETE FROM videos WHERE id = :i"), {"i": vid})
        flash("Delete ho gaya.")
    except Exception as e:
        app.logger.error("delete failed: %s", e)
        flash("Database error.")
    return redirect(url_for("admin"))


WRITING_TYPES = ["Article", "Blog", "Reel Script", "Caption", "Product Description", "Other"]


@app.route("/admin/writing")
def admin_writing():
    if not is_admin():
        return redirect(url_for("admin_login"))
    return render_template("admin_writing.html", items=[acard(r) for r in art_all()], types=WRITING_TYPES,
                           csrf=csrf_token(), cloud=CLOUD_NAME, preset=UPLOAD_PRESET, db_ok=bool(engine))


def _file_from_form(f, current=""):
    up = f.get("file_url", "").strip()
    link = f.get("file_link", "").strip()
    if up and ok_url(up, cloud_only=True):
        return up
    if link and ok_url(link):
        return link
    return current


@app.route("/admin/writing/add", methods=["POST"])
def admin_w_add():
    if not is_admin():
        abort(403)
    check_csrf()
    f = request.form
    title = f.get("title", "").strip()[:150]
    body = f.get("body", "").strip()[:30000]
    file_url = _file_from_form(f)
    if not title or not (body or file_url):
        flash("Title aur article text (ya file) chahiye.")
        return redirect(url_for("admin_writing"))
    wtype = f.get("wtype") if f.get("wtype") in WRITING_TYPES else "Other"
    try:
        with engine.begin() as c:
            c.execute(text("INSERT INTO articles (title, wtype, body, file_url) VALUES (:t, :w, :b, :f)"),
                      {"t": title, "w": wtype, "b": body, "f": file_url})
        flash("Article save ho gaya.")
    except Exception as e:
        app.logger.error("article insert failed: %s", e)
        flash("Database error. DATABASE_URL check karo.")
    return redirect(url_for("admin_writing"))


@app.route("/admin/writing/edit/<int:aid>", methods=["GET", "POST"])
def admin_w_edit(aid):
    if not is_admin():
        return redirect(url_for("admin_login"))
    r = art_one(aid)
    if not r:
        abort(404)
    if request.method == "POST":
        check_csrf()
        f = request.form
        wtype = f.get("wtype") if f.get("wtype") in WRITING_TYPES else "Other"
        file_url = "" if f.get("remove_file") else _file_from_form(f, r["file_url"] or "")
        try:
            with engine.begin() as c:
                c.execute(text("UPDATE articles SET title=:t, wtype=:w, body=:b, file_url=:f WHERE id=:i"),
                          {"t": f.get("title", "").strip()[:150] or r["title"], "w": wtype,
                           "b": f.get("body", "").strip()[:30000], "f": file_url, "i": aid})
            flash("Update ho gaya.")
        except Exception as e:
            app.logger.error("article update failed: %s", e)
            flash("Database error.")
        return redirect(url_for("admin_writing"))
    return render_template("admin_w_edit.html", a=acard(r), types=WRITING_TYPES, csrf=csrf_token(),
                           cloud=CLOUD_NAME, preset=UPLOAD_PRESET)


@app.route("/admin/writing/delete/<int:aid>", methods=["POST"])
def admin_w_delete(aid):
    if not is_admin():
        abort(403)
    check_csrf()
    try:
        with engine.begin() as c:
            c.execute(text("DELETE FROM articles WHERE id = :i"), {"i": aid})
        flash("Delete ho gaya.")
    except Exception as e:
        app.logger.error("article delete failed: %s", e)
        flash("Database error.")
    return redirect(url_for("admin_writing"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
