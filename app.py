
from flask import Flask, request, Response
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

SITES = {
    "BBC Arabic": "https://www.bbc.com/arabic",
    "Wikipedia Arabic": "https://ar.wikipedia.org",
    "Project Gutenberg": "https://www.gutenberg.org"
}

@app.route("/")
def home():
    links = ""
    for name, url in SITES.items():
        links += f'<p><a href="/read?site={name}">{name}</a></p>'

    return f"""
    <html>
    <head><meta charset="utf-8">
    <title>RetroWAP</title></head>
    <body>
    <h2>RetroWAP</h2>
    <p>متصفح خفيف للهواتف القديمة</p>
    {links}
    </body></html>
    """

@app.route("/read")
def read():
    name = request.args.get("site", "")
    url = SITES.get(name)

    if not url:
        return "الموقع غير متاح", 404

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "RetroWAP/1.0"}
        )
        response.raise_for_status()

        if "text/html" not in response.headers.get("Content-Type", ""):
            return "نوع الصفحة غير مدعوم", 415

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else name
        paragraphs = soup.find_all(["p", "h1", "h2", "h3", "li"])

        text = ""
        for item in paragraphs[:50]:
            line = item.get_text(" ", strip=True)
            if line:
                text += f"<p>{line}</p>"

        return f"""
        <html><head><meta charset="utf-8">
        <title>{title}</title></head>
        <body>
        <p><a href="/">الرئيسية</a></p>
        <h3>{title}</h3>
        {text}
        <p><a href="/">العودة</a></p>
        </body></html>
        """

    except requests.RequestException:
        return "تعذر تحميل الصفحة. حاول لاحقاً.", 502

@app.route("/health")
def health():
    return "RetroWAP is running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
