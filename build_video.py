#!/usr/bin/env python3
"""scenes.json -> out/lucknow_land_video.mp4 (+ captions.srt, thumbnail.png)

Pipeline: Pillow draws each scene (vector-style, blue/amber grade) -> edge-tts Hindi
voice (or your own scene_XX recordings) -> ffmpeg slow pan/zoom + fades -> mix ambient music.
"""
import asyncio, glob, json, os, random, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

ROOT = Path(__file__).resolve().parent
OUT, WORK, AUDIO = ROOT / "out", ROOT / "work", ROOT / "audio"
W, H, S = 3840, 2160, 2            # drawing canvas; S = scale vs 1080p
FPS = 25
LEAD = float(os.environ.get("LEAD", 0.8))          # silence before narration in each scene
VOICE = os.environ.get("VOICE", "hi-IN-MadhurNeural")   # female: hi-IN-SwaraNeural
RATE = os.environ.get("RATE", "-8%")                # calmer pace
FINAL = OUT / "lucknow_land_video.mp4"

AMBER = (255, 176, 72); BLUE = (92, 160, 255); WHITE = (236, 241, 250)
PALETTES = {
    "night": ((5, 10, 28), (20, 52, 100)),
    "dusk": ((14, 22, 58), (150, 88, 48)),
    "deep": ((6, 12, 30), (16, 38, 78)),
    "day": ((12, 36, 76), (70, 120, 170)),
    "sunrise": ((22, 40, 92), (244, 172, 84)),
}


def sh(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"Command failed: {' '.join(map(str, cmd))}\n{r.stderr[-2500:]}")
    return r.stdout


# ---------------------------------------------------------------- fonts
RAQM = features.check("raqm")
if not RAQM:
    print("WARNING: libraqm missing - Hindi conjuncts may render incorrectly.")
_fc = {}


def font_path(bold=True):
    if os.environ.get("FONT_PATH"):
        return os.environ["FONT_PATH"]
    style = "Bold" if bold else "Regular"
    c = glob.glob(f"/usr/share/fonts/**/NotoSansDevanagari-{style}.ttf", recursive=True)
    if c:
        return c[0]
    try:
        p = subprocess.check_output(
            ["fc-match", "-f", "%{file}", "Noto Sans Devanagari:" + ("bold" if bold else "")], text=True)
        if p:
            return p
    except Exception:
        pass
    sys.exit("Devanagari font not found. Install fonts-noto-core (or set FONT_PATH).")


def F(size, bold=True):
    k = (size, bold)
    if k not in _fc:
        kw = {"layout_engine": ImageFont.Layout.RAQM} if RAQM else {}
        _fc[k] = ImageFont.truetype(font_path(bold), size, **kw)
    return _fc[k]


def P(x, y):
    return (int(x * W), int(y * H))


class Ctx:
    """b = dark/opaque shapes, l = bright shapes that get a soft glow."""
    def __init__(self):
        self.bi = Image.new("RGBA", (W, H), (0, 0, 0, 0)); self.b = ImageDraw.Draw(self.bi)
        self.li = Image.new("RGBA", (W, H), (0, 0, 0, 0)); self.l = ImageDraw.Draw(self.li)


def txt(d, xy, s, size, fill=WHITE, bold=True, anchor="mm"):
    d.text(xy, s, font=F(size, bold), fill=fill, anchor=anchor)


def person(d, x, ground, h, col=(6, 10, 24, 255)):
    hr = h * 0.09
    d.ellipse([*P(x - hr * H / W, ground - h), *P(x + hr * H / W, ground - h + 2 * hr)], fill=col)
    d.rounded_rectangle([*P(x - 0.45 * hr * 2 * H / W, ground - h + 2.3 * hr),
                         *P(x + 0.45 * hr * 2 * H / W, ground)], radius=int(0.02 * H), fill=col)


# ---------------------------------------------------------------- motifs
def m_skyline(c, a):
    rnd = random.Random(7); base = 0.60
    c.l.ellipse([*P(0.80, 0.10), *P(0.86, 0.10 + 0.06 * W / H)], fill=(235, 228, 200, 220))
    x = 0.02
    while x < 0.98:
        w = rnd.uniform(0.018, 0.045)
        h = rnd.uniform(0.05, 0.24) * (1.0 if x < 0.55 else max(0.0, 1 - (x - 0.55) * 2.2))
        if h > 0.03:
            c.b.rectangle([*P(x, base - h), *P(x + w, base)], fill=(9, 16, 38, 255))
            for j in range(int(h / 0.028)):
                for i in range(max(1, int(w / 0.012))):
                    if rnd.random() < 0.35:
                        wx = x + 0.004 + i * 0.011; wy = base - h + 0.012 + j * 0.028
                        c.l.rectangle([*P(wx, wy), *P(wx + 0.005, wy + 0.012)], fill=(*AMBER, 210))
        x += w + rnd.uniform(0.004, 0.012)
    c.b.rectangle([*P(0, base), *P(1, 0.74)], fill=(10, 38, 34, 255))
    for k in range(6):
        y = base + 0.02 + k * 0.02
        c.l.line([*P(0, y), *P(1, y)], fill=(40, 110, 90, 90), width=3 * S)
    for tx in (0.66, 0.76, 0.86, 0.94):
        c.b.rectangle([*P(tx - 0.003, base), *P(tx + 0.003, base + 0.03)], fill=(30, 24, 18, 255))
        c.b.ellipse([*P(tx - 0.03, base - 0.07), *P(tx + 0.03, base + 0.01)], fill=(14, 60, 48, 255))


def m_lamp(c, a):
    c.b.rectangle([*P(0, 0.66), *P(1, 0.74)], fill=(8, 20, 36, 255))
    lx = 0.72
    c.l.polygon([P(lx - 0.02, 0.145), P(lx - 0.22, 0.70), P(lx + 0.10, 0.70)], fill=(*AMBER, 45))
    c.b.rectangle([*P(lx - 0.002, 0.14), *P(lx + 0.002, 0.66)], fill=(20, 28, 48, 255))
    c.b.rectangle([*P(lx - 0.03, 0.13), *P(lx + 0.01, 0.145)], fill=(20, 28, 48, 255))
    c.l.ellipse([*P(lx - 0.03, 0.140), *P(lx - 0.012, 0.140 + 0.017 * W / H)], fill=(*AMBER, 255))
    # plot map on a table
    c.l.rectangle([*P(0.22, 0.50), *P(0.50, 0.66)], fill=(225, 212, 180, 235))
    for i in range(1, 7):
        c.b.line([*P(0.22 + i * 0.04, 0.50), *P(0.22 + i * 0.04, 0.66)], fill=(60, 50, 40, 255), width=3 * S)
    for j in (0.54, 0.58, 0.62):
        c.b.line([*P(0.22, j), *P(0.50, j)], fill=(60, 50, 40, 255), width=3 * S)
    c.l.rectangle([*P(0.34, 0.54), *P(0.38, 0.58)], fill=(*AMBER, 255))
    for x, hh in ((0.58, 0.30), (0.625, 0.28), (0.66, 0.18)):
        person(c.b, x, 0.69, hh)


def m_plots(c, a):
    x0, y0, x1, y1, cols, rows = 0.20, 0.14, 0.80, 0.66, 8, 4
    hr, hc = a.get("highlight", [1, 3])
    cw, ch = (x1 - x0) / cols, (y1 - y0) / rows
    for r in range(rows):
        for k in range(cols):
            hl = (r, k) == (hr, hc)
            c.l.rectangle([*P(x0 + k * cw + 0.004, y0 + r * ch + 0.006), *P(x0 + (k + 1) * cw - 0.004, y0 + (r + 1) * ch - 0.006)],
                          fill=(*(AMBER if hl else BLUE), 110 if hl else 22), outline=(*(AMBER if hl else BLUE), 200), width=4 * S)


def m_badges(c, a):
    for cx, lab, col in ((0.36, "LDA", BLUE), (0.64, "RERA", AMBER)):
        r = 0.20 * H
        x, y = cx * W, 0.38 * H
        c.l.ellipse([x - r, y - r, x + r, y + r], outline=(*col, 230), width=8 * S, fill=(*col, 28))
        txt(c.l, (x, y), lab, 110 * S // 1, fill=col)
        c.l.line([x + r * 0.55, y - r * 1.0, x + r * 0.70, y - r * 0.85, x + r * 1.0, y - r * 1.25], fill=(*WHITE, 230), width=8 * S)
    txt(c.l, P(0.5, 0.63), "बोर्ड पर लिखा  ≠  कागज़ में दर्ज", 44 * S, fill=(*WHITE, 200), bold=False)


def m_split(c, a):
    for (x0, x1, col, kind) in ((0.08, 0.48, BLUE, "ok"), (0.52, 0.92, AMBER, "bad")):
        c.l.rounded_rectangle([*P(x0, 0.10), *P(x1, 0.64)], radius=30, outline=(*col, 220), width=6 * S, fill=(*col, 18))
        if kind == "ok":
            for i in range(1, 5):
                c.l.line([*P(x0 + i * 0.08, 0.14), *P(x0 + i * 0.08, 0.50)], fill=(*col, 150), width=3 * S)
            for j in (0.26, 0.38):
                c.l.line([*P(x0 + 0.02, j), *P(x1 - 0.02, j)], fill=(*col, 150), width=3 * S)
            cx, cy = (x0 + x1) / 2 * W, 0.52 * H
            c.l.line([cx - 90, cy, cx - 30, cy + 70, cx + 100, cy - 80], fill=(*WHITE, 240), width=10 * S)
            txt(c.l, P((x0 + x1) / 2, 0.59), "अप्रूव्ड लेआउट", 44 * S, fill=col)
        else:
            for j in range(5):
                y = 0.16 + j * 0.065
                c.l.line([*P(x0 + 0.02, y), *P(x1 - 0.02, y + 0.02)], fill=(*col, 120), width=3 * S)
            cx, cy = (x0 + x1) / 2 * W, 0.50 * H
            c.l.line([cx - 80, cy - 80, cx + 80, cy + 80], fill=(*WHITE, 240), width=10 * S)
            c.l.line([cx + 80, cy - 80, cx - 80, cy + 80], fill=(*WHITE, 240), width=10 * S)
            txt(c.l, P((x0 + x1) / 2, 0.59), "कृषि भूमि (कनवर्जन नहीं)", 44 * S, fill=col)


ROADS = {  # schematic, not to scale
    "ring": ("आउटर रिंग रोड", None),
    "shaheed": ("शहीद पथ", [(0.20, 0.58), (0.35, 0.66), (0.50, 0.68), (0.66, 0.65), (0.80, 0.56)]),
    "sultanpur": ("सुल्तानपुर रोड", [(0.50, 0.38), (0.70, 0.40), (0.90, 0.48)]),
    "raebareli": ("रायबरेली रोड", [(0.50, 0.38), (0.45, 0.52), (0.38, 0.67)]),
}


def m_map(c, a):
    hl = set(a.get("highlight", []))
    for i in range(1, 12):
        c.l.line([*P(i / 12, 0.06), *P(i / 12, 0.72)], fill=(*BLUE, 18), width=2 * S)
    for j in range(1, 8):
        c.l.line([*P(0.02, 0.06 + j * 0.083), *P(0.98, 0.06 + j * 0.083)], fill=(*BLUE, 18), width=2 * S)
    cx, cy = 0.5, 0.38
    ring_col = AMBER if "ring" in hl else BLUE
    c.l.ellipse([*P(cx - 0.20, cy - 0.27), *P(cx + 0.20, cy + 0.27)], outline=(*ring_col, 150), width=5 * S)
    txt(c.l, P(cx - 0.15, 0.10), "आउटर रिंग रोड", 36 * S, fill=(*BLUE, 220), bold=False)
    for key in ("shaheed", "sultanpur", "raebareli"):
        name, pts = ROADS[key]
        col = AMBER if key in hl else BLUE
        c.l.line([P(*p) for p in pts], fill=(*col, 255 if key in hl else 140), width=(12 if key in hl else 6) * S, joint="curve")
        ex, ey = pts[-1]
        txt(c.l, P(min(ex, 0.88), ey + 0.045), name, 40 * S, fill=col)
    c.l.ellipse([*P(cx - 0.012, cy - 0.012 * W / H), *P(cx + 0.012, cy + 0.012 * W / H)], fill=(*WHITE, 255))
    txt(c.l, P(cx, cy - 0.05), "लखनऊ", 44 * S, fill=WHITE)
    txt(c.l, P(0.80, 0.70), "योजनात्मक नक्शा — पैमाने के अनुसार नहीं", 28 * S, fill=(*WHITE, 150), bold=False)


def m_flow(c, a):
    act = set(a.get("active", []))
    labs = ["खसरा", "खतौनी", "बैनामा", "दाखिल-खारिज"]
    subs = ["प्लॉट नंबर व रकबा", "मालिक का रिकॉर्ड", "रजिस्ट्री / सेल डीड", "सरकारी रिकॉर्ड में नाम"]
    bw, gap, x = 0.19, 0.0467, 0.08
    for i, (lab, sub) in enumerate(zip(labs, subs)):
        col = AMBER if i in act else BLUE
        c.l.rounded_rectangle([*P(x, 0.26), *P(x + bw, 0.50)], radius=36, outline=(*col, 240), width=6 * S,
                              fill=(*col, 70 if i in act else 20))
        txt(c.l, P(x + bw / 2, 0.35), lab, 46 * S, fill=col)
        txt(c.l, P(x + bw / 2, 0.44), sub, 30 * S, fill=(*WHITE, 210), bold=False)
        if i < 3:
            ax, ay = (x + bw) * W, 0.38 * H
            bx = (x + bw + gap) * W
            c.l.line([ax + 12, ay, bx - 12, ay], fill=(*WHITE, 200), width=5 * S)
            c.l.polygon([(bx - 12, ay), (bx - 52, ay - 26), (bx - 52, ay + 26)], fill=(*WHITE, 200))
        x += bw + gap


def tag_img(label, col, angle):
    tw, th = 980, 340
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); dd = ImageDraw.Draw(im)
    pts = [(130, 6), (tw - 6, 6), (tw - 6, th - 6), (130, th - 6), (6, th // 2)]
    dd.polygon(pts, fill=(*col, 38))
    dd.line(pts + [pts[0]], fill=(*col, 235), width=8)
    dd.ellipse([86, th // 2 - 22, 130, th // 2 + 22], outline=(*col, 235), width=6)
    dd.text((tw // 2 + 70, th // 2), label, font=F(80), fill=(*WHITE, 245), anchor="mm")
    return im.rotate(angle, expand=True, resample=Image.BICUBIC)


def m_tags(c, a):
    labs = a.get("labels", ["कमीशन", "स्टांप ड्यूटी", "डेवलपमेंट चार्ज", "रजिस्ट्री खर्च"])
    slots = [(0.06, 0.12, -6, AMBER), (0.40, 0.10, 5, BLUE), (0.12, 0.40, 4, BLUE), (0.44, 0.38, -5, AMBER)]
    for (x, y, ang, col), lab in zip(slots, labs):
        im = tag_img(lab, col, ang)
        c.li.alpha_composite(im, dest=(int(x * W), int(y * H)))
    person(c.b, 0.88, 0.70, 0.46)
    c.l.line([*P(0.875, 0.31), *P(0.86, 0.35)], fill=(*AMBER, 255), width=4 * S)


def m_sunrise(c, a):
    horizon = 0.60
    c.l.ellipse([*P(0.5 - 0.09 * H / W, horizon - 0.18), *P(0.5 + 0.09 * H / W, horizon + 0.0)], fill=(255, 214, 140, 255))
    c.l.ellipse([*P(0.5 - 0.20 * H / W, horizon - 0.29), *P(0.5 + 0.20 * H / W, horizon + 0.11)], fill=(255, 190, 110, 40))
    c.b.rectangle([*P(0, horizon), *P(1, 0.74)], fill=(34, 26, 22, 255))
    x0, x1, y0, y1 = 0.14, 0.86, 0.52, 0.68
    c.b.rectangle([*P(x0, y0), *P(x1, y1)], fill=(118, 64, 44, 255))
    j = y0
    row = 0
    while j < y1:
        c.b.line([*P(x0, j), *P(x1, j)], fill=(70, 38, 28, 255), width=3 * S)
        off = 0.0 if row % 2 == 0 else 0.015
        xx = x0 + off
        while xx < x1:
            c.b.line([*P(xx, j), *P(xx, min(j + 0.02, y1))], fill=(70, 38, 28, 255), width=3 * S)
            xx += 0.03
        j += 0.02; row += 1
    for px in (x0, x1 - 0.015):
        c.b.rectangle([*P(px, y0 - 0.025), *P(px + 0.015, y1)], fill=(96, 52, 36, 255))


MOTIFS = {k[2:]: v for k, v in globals().items() if k.startswith("m_")}


# ---------------------------------------------------------------- scene render
def render_scene(sc, idx):
    top, bot = PALETTES[sc.get("palette", "night")]
    g = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), bot), Image.new("RGB", (W, H), top), g).convert("RGBA")
    if sc.get("palette", "night") in ("night", "dusk", "deep"):
        d = ImageDraw.Draw(img); rnd = random.Random(idx)
        for _ in range(140):
            x, y = rnd.randint(0, W), rnd.randint(0, int(H * 0.35)); r = rnd.choice((2, 3, 4))
            d.ellipse([x, y, x + r, y + r], fill=(255, 255, 255, rnd.randint(60, 190)))
    c = Ctx()
    MOTIFS[sc["motif"]](c, sc.get("args", {}))
    img = Image.alpha_composite(img, c.bi)
    img = Image.alpha_composite(img, c.li.filter(ImageFilter.GaussianBlur(26 * S)))
    img = Image.alpha_composite(img, c.li)
    # shade for text
    sh_h = int(0.34 * H)
    mask = Image.linear_gradient("L").resize((W, sh_h)).point(lambda v: int(v * 0.62))
    shade = Image.new("RGBA", (W, sh_h), (0, 0, 0, 255)); shade.putalpha(mask)
    img.alpha_composite(shade, (0, H - sh_h))
    d = ImageDraw.Draw(img)
    d.text((int(0.06 * W), int(0.775 * H)), sc.get("label", ""), font=F(34 * S, False), fill=(*AMBER, 255), anchor="ls")
    y = 0.865 * H
    for ln in sc.get("lines", []):
        d.text((int(0.06 * W), int(y)), ln, font=F(58 * S), fill=(*WHITE, 255), anchor="ls")
        y += 0.075 * H
    return img.convert("RGB")


# ---------------------------------------------------------------- audio
async def _tts(text, path):
    import edge_tts
    last = None
    for n in range(4):
        try:
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(path)); return
        except Exception as e:  # network hiccup / throttling
            last = e; await asyncio.sleep(3 * (n + 1))
    raise last


def get_audio(i, text):
    for folder in (AUDIO, ROOT):
        for ext in ("mp3", "m4a", "wav", "aac", "ogg"):
            p = folder / f"scene_{i:02d}.{ext}"
            if p.exists():
                print(f"  using your recording: {p.name}"); return p
    p = WORK / f"voice_{i:02d}.mp3"
    if not p.exists():
        asyncio.run(_tts(text, p))
    return p


def duration(p):
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip())


def make_clip(png, aud, total, i, out):
    fr = int(total * FPS)
    if i % 2:   # slow zoom-in
        z, x, y = f"1.0+0.12*on/{fr}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:       # slow pan
        z, x, y = "1.12", f"(iw-iw/zoom)*on/{fr}", "(ih-ih/zoom)/2"
    fl = (f"[0:v]zoompan=z='{z}':x='{x}':y='{y}':d={fr}:s=1920x1080:fps={FPS},"
          f"fade=t=in:st=0:d=0.7,fade=t=out:st={total-0.7:.2f}:d=0.7,format=yuv420p[v];"
          f"[1:a]adelay={int(LEAD*1000)}:all=1,apad=whole_dur={total:.3f},aresample=44100,"
          f"aformat=channel_layouts=stereo[a]")
    sh(["ffmpeg", "-y", "-i", png, "-i", aud, "-filter_complex", fl, "-map", "[v]", "-map", "[a]",
        "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", out])


def stamp(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def main():
    data = json.loads((ROOT / "scenes.json").read_text(encoding="utf-8"))
    scenes = data["scenes"]
    OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
    clips, srt, t, n = [], [], 0.0, 1
    for i, sc in enumerate(scenes, 1):
        print(f"Scene {i}/{len(scenes)}: {sc['motif']}")
        img = render_scene(sc, i)
        png = WORK / f"scene_{i:02d}.png"; img.save(png)
        if i == 1:
            img.resize((1280, 720), Image.LANCZOS).save(OUT / "thumbnail.png")
        aud = get_audio(i, sc["narration"]); da = duration(aud)
        total = LEAD + da + float(sc.get("pause", 2.5))
        clip = WORK / f"clip_{i:02d}.mp4"; make_clip(png, aud, total, i, clip); clips.append(clip)
        parts = [p.strip() for p in re.split(r"(?<=[।?!])\s+", sc["narration"]) if p.strip()]
        tot_chars = sum(len(p) for p in parts); st = t + LEAD
        for p in parts:
            dur = da * len(p) / tot_chars
            srt.append(f"{n}\n{stamp(st)} --> {stamp(st + dur)}\n{p}\n"); n += 1; st += dur
        t += total
    (OUT / "captions.srt").write_text("\n".join(srt), encoding="utf-8")

    lst = WORK / "list.txt"
    lst.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips))
    joined = WORK / "joined.mp4"
    sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    total_s = duration(joined)

    music = next(iter(sorted(glob.glob(str(AUDIO / "music.*")) + glob.glob(str(ROOT / "music.*")))), None)
    if music:
        print("Using your music:", music)
        minput, vol = ["-stream_loop", "-1", "-i", music], 0.12
    else:   # soft ambient drone placeholder
        amb = WORK / "ambient.wav"
        sh(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=f=110:d={total_s+1:.1f}", "-f", "lavfi", "-i", f"sine=f=164.81:d={total_s+1:.1f}",
            "-f", "lavfi", "-i", f"sine=f=220:d={total_s+1:.1f}", "-filter_complex",
            "[0:a][1:a][2:a]amix=inputs=3:normalize=0,lowpass=f=500,tremolo=f=0.12:d=0.6,volume=0.05,aformat=channel_layouts=stereo[a]",
            "-map", "[a]", amb])
        minput, vol = ["-i", amb], 1.0
    fl = (f"[1:a]volume={vol},afade=t=in:d=3,afade=t=out:st={max(total_s-4,0):.2f}:d=4[m];"
          f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]")
    sh(["ffmpeg", "-y", "-i", joined, *minput, "-filter_complex", fl, "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", FINAL])
    print(f"\nDONE: {FINAL}  ({total_s/60:.1f} min)")
    if total_s < 480:
        print("NOTE: video is under 8 minutes. Lengthen the 'narration' text in scenes.json to reach ~10 min.")


if __name__ == "__main__":
    main()
