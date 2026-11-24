
import os
import hmac
import requests
from html import escape
from flask import Flask, request, Response
from bs4 import BeautifulSoup

app = Flask(__name__)

SITES = {
    "wiki": ("ويكيبيديا العربية", "https://ar.wikipedia.org"),
    "bbc": ("بي بي سي عربي", "https://www.bbc.com/arabic")
}

@app.before_request
def protect():
    if request.path == "/health":
        return None

    auth = request.authorization
    user = os.environ.get("RETROWAP_USER", "")
    password = os.environ.get("RETROWAP_PASSWORD", "")

    if not user or not password or not auth:
        return login_required()

    if not (
        hmac.compare_digest(auth.username or "", user)
        and hmac.compare_digest(auth.password or "", password)
    ):
        return login_required()

def login_required():
    return Response(
        "يلزم تسجيل الدخول",
        401,
        {"WWW-Authenticate": 'Basic realm="RetroWAP"'}
    )

@app.route("/")
def home():
    links = ""
    for key, (name, url) in SITES.items():
        links += f'<p><a href="/read?site={key}">{escape(name)}</a></p>'

    return """
    <html dir="rtl">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width">
    <title>RetroWAP</title>
    </head>
    <body>
    <h2>RetroWAP</h2>
    <p>متصفح الإنترنت الخفيف</p>
    <hr>
    <h3>المواقع</h3>
    """ + links + """
    <hr>
    <h3>مساعد الذكاء الاصطناعي</h3>
    <form action="/ask" method="post">
    <textarea name="question" rows="4" cols="25"
    maxlength="2000" required></textarea>
    <p><button type="submit">اسأل Gemini</button></p>
    </form>
    <hr>
    <p>متصفح عربي شخصي</p>
    </body>
    </html>
    """

@app.route("/read")
def read():
    key = request.args.get("site", "")
    if key not in SITES:
        return "الموقع غير متاح", 404

    name, url = SITES[key]

    try:
        r = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "RetroWAP/1.0"},
            allow_redirects=False
        )

        if r.status_code != 200:
            return "تعذر تحميل الصفحة", 502

        if "text/html" not in r.headers.get("Content-Type", ""):
            return "نوع الصفحة غير مدعوم", 415

        if len(r.content) > 1000000:
            return "الصفحة كبيرة جداً", 413

        soup = BeautifulSoup(r.content, "html.parser")

        for tag in soup([
            "script", "style", "nav", "footer",
            "header", "form", "iframe"
        ]):
            tag.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else name

        text = ""
        for item in soup.find_all(
            ["h1", "h2", "h3", "p", "li"]
        )[:50]:
            line = item.get_text(" ", strip=True)
            if line:
                text += "<p>" + escape(line) + "</p>"

        return """
        <html dir="rtl">
        <head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width">
        <title>RetroWAP</title></head>
        <body>
        <p><a href="/">الرئيسية</a></p>
        <h3>""" + escape(title) + """</h3>
        """ + text + """
        <hr><a href="/">العودة</a>
        </body></html>
        """

    except requests.RequestException:
        return "تعذر الاتصال بالموقع", 502

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question", "").strip()

    if not question or len(question) > 2000:
        return "اكتب سؤالاً لا يتجاوز 2000 حرف", 400

    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key:
        return "مفتاح الذكاء الاصطناعي غير موجود", 500

    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "contents": [{
                    "parts": [{
                        "text": "أجب باللغة العربية وبأسلوب بسيط ومختصر:\n" + question
                    }]
                }],
                "generationConfig": {
                    "maxOutputTokens": 300
                }
            },
            timeout=35
        )

        if response.status_code != 200:
            return "تعذر الحصول على إجابة. تحقق من المفتاح أو حدود الاستخدام.", 502

        data = response.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]

        return """
        <html dir="rtl">
        <head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width">
        <title>RetroWAP AI</title></head>
        <body>
        <h3>مساعد RetroWAP</h3>
        <p style="white-space:pre-wrap">""" + escape(answer) + """</p>
        <hr><a href="/">العودة للرئيسية</a>
        </body></html>
        """

    except (requests.RequestException, ValueError, KeyError, IndexError):
        return "حدث خطأ في الاتصال بالذكاء الاصطناعي. حاول لاحقاً.", 502

@app.route("/health")
def health():
    return "RetroWAP يعمل"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

