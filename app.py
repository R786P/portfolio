from flask import Flask, render_template

app = Flask(__name__)

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

# thumb: static/thumbs/ me file daalo aur yahan naam likho, e.g. "p1.jpg"
# url: video ka Drive / Instagram / YouTube link
VIDEOS = [
    {"title": "5 AM Habits", "type": "Reel", "desc": "AI visuals, text on screen and voiceover.", "thumb": "", "url": ""},
    {"title": "How to Make an AI Reel", "type": "YouTube", "desc": "Step-by-step explainer edited in InShot.", "thumb": "", "url": ""},
    {"title": "Diwali Highlights", "type": "Event film", "desc": "Festive highlight film with music sync.", "thumb": "", "url": ""},
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


@app.context_processor
def inject_profile():
    return {"p": PROFILE}


@app.route("/")
def home():
    return render_template("index.html", vs=VIDEO_SERVICES, ws=WRITING_SERVICES)


@app.route("/video-editing")
def video():
    return render_template("video.html", videos=VIDEOS, vs=VIDEO_SERVICES)


@app.route("/content-writing")
def writing():
    return render_template("writing.html", samples=WRITING, ws=WRITING_SERVICES)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
