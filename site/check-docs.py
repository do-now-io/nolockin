#!/usr/bin/env python3
"""Vérifie les liens internes et les ancres du site généré (site/docs). Code de retour 1 si cassé."""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1] / "site" / "docs"
if not ROOT.exists():
    print("site/docs absent : lancer d'abord python3 site/build-docs.py"); sys.exit(2)

ids = {f: set(re.findall(r' id="([^"]+)"', f.read_text())) for f in ROOT.rglob("*.html")}
bad = 0
for f in ROOT.rglob("*.html"):
    txt = f.read_text()
    for path, anc in re.findall(r'href="([^"#]*)#([^"]+)"', txt):
        if path.startswith(("http", "mailto:")): continue
        t = (f.parent / path).resolve() if path else f
        if t.is_dir(): t = t / "index.html"
        if not t.exists():
            bad += 1; print(f"PAGE MANQUANTE  {f.relative_to(ROOT)} → {path}"); continue
        if anc not in ids.get(t, set()):
            bad += 1; print(f"ANCRE CASSÉE    {f.relative_to(ROOT)} → {path}#{anc}")
    for path in re.findall(r'href="([^"#:]+/)"', txt):
        if not ((f.parent / path).resolve() / "index.html").exists():
            bad += 1; print(f"LIEN CASSÉ      {f.relative_to(ROOT)} → {path}")
    for path in re.findall(r'(?:href|src)="(assets/[^"]+|\.\./[^"]*assets/[^"]+)"', txt):
        if not (f.parent / path).resolve().exists():
            bad += 1; print(f"ASSET MANQUANT  {f.relative_to(ROOT)} → {path}")
    for m in re.findall(r"\*\*[^*<\n]+\*\*|\]\([^)\s]+\)", re.sub(r"<pre.*?</pre>", "", txt, flags=re.S)):
        bad += 1; print(f"MARKDOWN RÉSIDUEL {f.relative_to(ROOT)} : {m[:60]}")
pages = sum(1 for _ in ROOT.rglob("index.html"))
print(f"{pages} pages, {bad} problème(s)")
sys.exit(1 if bad else 0)
