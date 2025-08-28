import os, io, tempfile
from flask import Flask, render_template, request, send_file, redirect, url_for, abort, make_response
from werkzeug.utils import secure_filename
import config
from PyPDF2 import PdfMerger
from PIL import Image
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from moviepy.editor import VideoFileClip
import pikepdf

app = Flask(__name__)
app.config.from_object(config)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_FILE_SIZE_MB * 1024 * 1024

TOOLS = {
    "merge-pdf": {"title":"Merge PDF","accept":".pdf","multiple":True},
    "png-to-pdf": {"title":"PNG → PDF","accept":".png","multiple":True},
    "mp4-to-mp3": {"title":"MP4 → MP3","accept":".mp4","multiple":False}
}

@app.context_processor
def inject_config():
    return dict(config=config, SITE_NAME=config.SITE_NAME)

@app.route('/robots.txt')
def robots():
    lines = ["User-agent: *", "Allow: /", f"Sitemap: {config.SITE_URL.rstrip('/')}/sitemap.xml"]
    resp = make_response("\n".join(lines), 200)
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route('/sitemap.xml')
def sitemap():
    base = config.SITE_URL.rstrip('/')
    urls = ["/", "/how-to-use"] + [f"/tool/{slug}" for slug in TOOLS.keys()]
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml_parts.append(f"<url><loc>{base}{u}</loc></url>")
    xml_parts.append("</urlset>")
    resp = make_response("\n".join(xml_parts), 200)
    resp.headers["Content-Type"] = "application/xml"
    return resp

@app.route('/')
def index():
    return render_template('index.html', tools=TOOLS)

@app.route('/how-to-use')
def how_to_use():
    return render_template('how-to-use.html')

@app.route('/tool/<slug>', methods=['GET','POST'])
def tool(slug):
    if slug not in TOOLS:
        abort(404)
    cfg = TOOLS[slug]
    if request.method == 'GET':
        return render_template('tool.html', tool_name=cfg['title'], accept=cfg['accept'], multiple=cfg['multiple'], desc=cfg.get('desc',''))
    # POST: process uploads for three tools
    files = request.files.getlist('file') if 'file' in request.files else request.files.getlist('files')
    if not files or files[0].filename == '':
        return redirect(request.url)
    saved = []
    try:
        for f in files:
            filename = secure_filename(f.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            f.save(path)
            saved.append(path)
        # Merge PDF
        if slug == 'merge-pdf':
            merger = PdfMerger()
            for p in saved:
                merger.append(p)
            out = io.BytesIO()
            merger.write(out); merger.close()
            return send_file(io.BytesIO(out.getvalue()), as_attachment=True, download_name='merged.pdf', mimetype='application/pdf')
        # PNG to PDF (single or multiple)
        if slug == 'png-to-pdf':
            imgs = [Image.open(p).convert('RGB') for p in saved]
            out = io.BytesIO()
            if len(imgs) == 1:
                imgs[0].save(out, format='PDF')
            else:
                imgs[0].save(out, format='PDF', save_all=True, append_images=imgs[1:])
            return send_file(io.BytesIO(out.getvalue()), as_attachment=True, download_name='images.pdf', mimetype='application/pdf')
        # MP4 to MP3
        if slug == 'mp4-to-mp3':
            src = saved[0]
            clip = VideoFileClip(src)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            clip.audio.write_audiofile(tmp.name, fps=44100, bitrate='192k')
            clip.close()
            with open(tmp.name,'rb') as f:
                data = f.read()
            os.remove(tmp.name)
            return send_file(io.BytesIO(data), as_attachment=True, download_name='audio.mp3', mimetype='audio/mpeg')
    finally:
        for p in saved:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except: pass
    abort(400)

@app.errorhandler(413)
def too_large(e):
    return f"File too large. Max is {app.config['MAX_CONTENT_LENGTH']//1024//1024} MB", 413

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
