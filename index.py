# -*- coding: utf-8 -*-
import cv2
import numpy as np
import os, json, zipfile, io, base64
from PIL import Image
from collections import Counter

video_path = "/mnt/data/WhatsApp Video 2025-08-22 at 18.29.08.mp4"

# Create output directory
out_dir = "/mnt/data/video_to_code_assets"
os.makedirs(out_dir, exist_ok=True)

# Open the video
cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    raise RuntimeError("Não consegui abrir o vídeo. Verifique o arquivo enviado.")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = frame_count / fps if fps else 0

# Choose timestamps to sample (up to 8 evenly spaced frames)
num_samples = min(8, frame_count if frame_count>0 else 8)
timestamps = [duration * i / (num_samples + 1) for i in range(1, num_samples + 1)]

saved_frames = []
for t in timestamps:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ret, frame = cap.read()
    if not ret:
        continue
    # Convert BGR->RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    fname = f"frame_{int(t*1000):06d}.png"
    fpath = os.path.join(out_dir, fname)
    img.save(fpath, "PNG")
    saved_frames.append(fpath)

cap.release()

# Compute a color palette from the saved frames using k-means (cv2.kmeans)
def extract_palette(image_paths, k=5):
    # Collect pixels sampled from each image (downsample to speed up)
    pixels = []
    for p in image_paths:
        im = Image.open(p).convert("RGB")
        im = im.resize((160, 90))  # small thumbnail
        arr = np.array(im).reshape(-1, 3).astype(np.float32)
        pixels.append(arr)
    if not pixels:
        return []
    data = np.vstack(pixels)

    # k-means
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2)
    ret, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    centers = centers.astype(int)
    # Order by cluster size (descending)
    counts = Counter(labels.flatten())
    ordered = [tuple(centers[i]) for i, _ in counts.most_common()]
    return ordered

palette = extract_palette(saved_frames, k=6)

# Save palette as an image strip and JSON
palette_hex = ['#%02x%02x%02x' % tuple(c) for c in palette]
palette_img = Image.new("RGB", (60*max(1,len(palette)), 60), (255,255,255))
for i, col in enumerate(palette):
    block = Image.new("RGB", (60,60), tuple(col))
    palette_img.paste(block, (i*60, 0))
palette_img_path = os.path.join(out_dir, "palette.png")
palette_img.save(palette_img_path)

with open(os.path.join(out_dir, "palette.json"), "w", encoding="utf-8") as f:
    json.dump({"palette_rgb": palette, "palette_hex": palette_hex}, f, ensure_ascii=False, indent=2)

# Build HTML/CSS/JS project using extracted palette
project_dir = "/mnt/data/video_landing"
os.makedirs(project_dir, exist_ok=True)

primary = palette_hex[0] if palette_hex else "#222222"
accent  = palette_hex[1] if len(palette_hex)>1 else "#555555"
bg      = palette_hex[2] if len(palette_hex)>2 else "#ffffff"
text    = "#ffffff" if np.mean(Image.open(saved_frames[0]).convert("L")) < 128 else "#111111" if saved_frames else "#111111"

# Copy first frame as a hero background
hero_src = saved_frames[0] if saved_frames else None
hero_rel = None
if hero_src:
    hero_rel = "hero.png"
    Image.open(hero_src).save(os.path.join(project_dir, hero_rel))

# Prepare CSS with variables
css = f""":root{{
  --color-primary: {primary};
  --color-accent:  {accent};
  --color-bg:      {bg};
  --color-text:    {text};
  --radius: 1.25rem;
  --shadow: 0 10px 30px rgba(0,0,0,.15);
}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif;background:var(--color-bg);color:var(--color-text)}}
.container{{max-width:1100px;margin:0 auto;padding:24px}}
.nav{{position:sticky;top:0;background:rgba(255,255,255,.08);backdrop-filter: blur(8px);border-bottom:1px solid rgba(0,0,0,.06);z-index:10}}
.nav-inner{{display:flex;align-items:center;gap:16px;justify-content:space-between;padding:12px 24px}}
.brand{{display:flex;align-items:center;gap:10px;font-weight:700}}
.brand .dot{{width:10px;height:10px;border-radius:50%;background:var(--color-accent)}}
.actions a{{text-decoration:none;padding:10px 14px;border-radius:999px;border:1px solid rgba(0,0,0,.1)}}
.actions a.primary{{background:var(--color-primary);color:white;border-color:transparent;box-shadow:var(--shadow)}}
.hero{{position:relative;display:grid;place-items:center;min-height:68vh;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);margin:16px}}
.hero::before{{content:'';position:absolute;inset:0;background:linear-gradient(180deg, rgba(0,0,0,.45), rgba(0,0,0,.35));z-index:0}}
.hero .inner{{position:relative;z-index:1;text-align:center;padding:32px}}
.hero h1{{font-size:clamp(28px,6vw,56px);margin:0 0 10px 0;line-height:1.05}}
.hero p{{font-size:clamp(14px,2.5vw,18px);opacity:.9;margin:6px 0 20px}}
.badges{{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}}
.badge{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.25);padding:8px 12px;border-radius:999px;backdrop-filter: blur(4px)}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin:24px 16px}}
.card{{background:rgba(255,255,255,.06);border:1px solid rgba(0,0,0,.06);border-radius:var(--radius);padding:18px;box-shadow:var(--shadow)}}
.card h3{{margin:0 0 6px 0}}
.footer{{text-align:center;opacity:.7;padding:30px}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
.fadeUp{{animation:fadeUp .8s ease both}}
"""

# Build HTML
hero_style = f"background-image:url('{hero_rel}');background-size:cover;background-position:center;" if hero_rel else ""
html = f"""<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Página baseada no seu vídeo</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="nav">
    <div class="nav-inner container">
      <div class="brand"><span class="dot"></span> Seu Evento</div>
      <nav class="actions">
        <a href="#detalhes">Detalhes</a>
        <a class="primary" href="#inscricao">Inscreva-se</a>
      </nav>
    </div>
  </header>

  <main>
    <section class="hero" style="{hero_style}">
      <div class="inner fadeUp">
        <h1>Título / Chamada do Vídeo</h1>
        <p>Subtítulo baseado no conteúdo apresentado. Edite estes textos para refletirem exatamente o que aparece no vídeo.</p>
        <div class="badges">
          <span class="badge">Data</span>
          <span class="badge">Local</span>
          <span class="badge">Inscrição</span>
        </div>
      </div>
    </section>

    <section id="detalhes" class="container">
      <h2 class="fadeUp">Detalhes</h2>
      <div class="card-grid">
        <article class="card fadeUp">
          <h3>Quando</h3>
          <p>Informe a data e o horário conforme o vídeo.</p>
        </article>
        <article class="card fadeUp">
          <h3>Onde</h3>
          <p>Endereço / Local do evento.</p>
        </article>
        <article class="card fadeUp">
          <h3>Premiações</h3>
          <p>Descreva os prêmios conforme mostrado.</p>
        </article>
        <article class="card fadeUp">
          <h3>Contato</h3>
          <p>Telefone / WhatsApp.</p>
        </article>
      </div>
    </section>

    <section id="inscricao" class="container">
      <div class="card fadeUp">
        <h3>Faça sua inscrição</h3>
        <form id="inscrever">
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px">
            <input required placeholder="Seu nome" name="nome">
            <input required placeholder="Telefone/WhatsApp" name="fone">
            <input placeholder="Equipe/Clube" name="clube">
            <select name="pagamento">
              <option value="" disabled selected>Forma de pagamento</option>
              <option>Dinheiro</option>
              <option>Pix</option>
              <option>Cartão de crédito</option>
              <option>Cartão de débito</option>
            </select>
          </div>
          <button style="margin-top:12px;padding:12px 18px;border-radius:10px;border:none;background:var(--color-primary);color:white;box-shadow:var(--shadow)">Enviar</button>
        </form>
      </div>
    </section>
  </main>

  <footer class="footer">Baseado nas cores extraídas do seu vídeo • Edite os textos para refletir exatamente o conteúdo.</footer>

  <script src="script.js"></script>
</body>
</html>
"""

# Minimal JS: smooth scroll + simple "enter" animations on scroll
js = r"""document.querySelectorAll('a[href^="#"]').forEach(a=>{
  a.addEventListener('click', (e)=>{
    e.preventDefault();
    const el = document.querySelector(a.getAttribute('href'));
    if (el) el.scrollIntoView({behavior:'smooth'});
  });
});

const io = new IntersectionObserver((entries)=>{
  entries.forEach(entry=>{
    if(entry.isIntersecting){ entry.target.classList.add('fadeUp'); }
  });
}, {threshold: .15});

document.querySelectorAll('.card, h2').forEach(el=>io.observe(el));

document.getElementById('inscrever')?.addEventListener('submit', (e)=>{
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target).entries());
  alert(`Inscrição registrada:\n${JSON.stringify(data,null,2)}`);
  e.target.reset();
});
"""

# Write files
with open(os.path.join(project_dir, "styles.css"), "w", encoding="utf-8") as f:
    f.write(css)
with open(os.path.join(project_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
with open(os.path.join(project_dir, "script.js"), "w", encoding="utf-8") as f:
    f.write(js)

# Create a zip
zip_path = "/mnt/data/video_landing_site.zip"
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(project_dir):
        for name in files:
            fpath = os.path.join(root, name)
            arc = os.path.relpath(fpath, project_dir)
            z.write(fpath, arcname=arc)

# Return summary
{
 "frames_saved": saved_frames,
 "palette_hex": palette_hex,
 "palette_image": palette_img_path,
 "project_zip": zip_path,
 "project_dir": project_dir
}


# Fix JSON serialization for NumPy types by converting to Python ints
import json, os
from PIL import Image

out_dir = "/mnt/data/video_to_code_assets"
palette_json_path = os.path.join(out_dir, "palette.json")

# Reload palette from previous state in memory would be ideal, but we will reconstruct from the saved palette.png if needed.
# Instead, read the palette from the image we saved (each 60x60 block). We'll re-derive hex colors by sampling pixels.
palette_img_path = os.path.join(out_dir, "palette.png")
img = Image.open(palette_img_path).convert("RGB")
w, h = img.size
cols = w // 60

palette = []
for i in range(cols):
    r,g,b = img.getpixel((i*60+30, h//2))
    palette.append((int(r), int(g), int(b)))

palette_hex = ['#%02x%02x%02x' % tuple(c) for c in palette]

with open(palette_json_path, "w", encoding="utf-8") as f:
    json.dump({"palette_rgb": [list(map(int,c)) for c in palette], "palette_hex": palette_hex}, f, ensure_ascii=False, indent=2)

palette_json_path
