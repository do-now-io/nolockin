#!/usr/bin/env python3
"""Génère le site de documentation NoLockIn.

    python3 site/build-docs.py            # → site/docs/ (multi-pages, à héberger)
    python3 site/build-docs.py --bundle X # → X : un seul fichier HTML, navigation par hash (aperçu)

Sources : docs/**/*.md, README.md, examples/, charts/nolockin/README.md. Zéro dépendance.
"""
import html, json, os, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "docs"
GH = "https://github.com/do-now-io/nolockin/blob/main/"
MERMAID = "https://cdnjs.cloudflare.com/ajax/libs/mermaid/11.6.0/mermaid.min.js"
FONTS = "https://fonts.googleapis.com/css2?family=Overpass:wght@700;800;900&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap"

# (slug, source, titre de page ou None = premier H1, libellé sidebar ou None = titre)
NAV = [
    ("Démarrer", [
        ("index", "docs/README.md", "Documentation", "Sommaire"),
        ("demarrer/introduction", "docs/demarrer/introduction.md", None, "Introduction"),
        ("demarrer/installation", "docs/demarrer/installation.md", None, "Installation"),
        ("demarrer/premiere-app", "docs/demarrer/premiere-app.md", None, "Première application"),
        ("demarrer/environnements", "docs/demarrer/environnements.md", None, "Environnements"),
    ]),
    ("Guides", [
        ("guides/deployer", "docs/guides/deployer.md", None, "Déployer et livrer"),
        ("guides/secrets", "docs/guides/secrets.md", None, "Secrets"),
        ("guides/domaines", "docs/guides/domaines.md", None, "Domaines et TLS"),
        ("guides/add-ons", "docs/guides/add-ons.md", None, "Add-ons"),
        ("guides/observabilite", "docs/guides/observabilite.md", None, "Observabilité"),
        ("guides/self-hosting", "docs/guides/self-hosting.md", None, "Héberger NoLockIn chez vous"),
        ("guides/sortie", "docs/guides/sortie.md", None, "Quitter le cloud NoLockIn"),
    ]),
    ("Référence", [
        ("reference/manifeste", "docs/reference/manifeste.md", None, "Manifeste nolockin.yaml"),
        ("reference/cli", "docs/reference/cli.md", None, "CLI nlk"),
        ("reference/chart", ["charts/nolockin/README.md", "charts/nolockin/values.yaml", "charts/nolockin/Chart.yaml"], "Chart Helm", "Chart Helm"),
        ("reference/tarification", "docs/reference/tarification.md", None, "Tarification et metering"),
        ("reference/securite", "docs/reference/securite.md", None, "Sécurité et multi-tenant"),
        ("reference/glossaire", "docs/reference/glossaire.md", None, "Glossaire"),
    ]),
    ("Architecture", [
        ("architecture/vue-d-ensemble", "docs/architecture/vue-d-ensemble.md", None, "Vue d'ensemble"),
        ("architecture/adr", "docs/architecture/adr/README.md", "Architecture Decision Records", "Index des ADR"),
        ("architecture/adr/0001", "docs/architecture/adr/0001-kubernetes-only.md", None, "0001 · Kubernetes, substrat unique"),
        ("architecture/adr/0002", "docs/architecture/adr/0002-manifest-maps-to-plain-kubernetes.md", None, "0002 · Manifeste → Kubernetes standard"),
        ("architecture/adr/0003", "docs/architecture/adr/0003-argocd-plus-operator.md", None, "0003 · ArgoCD + opérateur"),
        ("architecture/adr/0004", "docs/architecture/adr/0004-metering-from-prometheus.md", None, "0004 · Metering depuis Prometheus"),
        ("architecture/adr/0005", "docs/architecture/adr/0005-apache-2-license.md", None, "0005 · Licence Apache-2.0"),
        ("architecture/adr/0006", "docs/architecture/adr/0006-exit-is-a-ci-gate.md", None, "0006 · La sortie, test bloquant"),
        ("architecture/adr/0007", "docs/architecture/adr/0007-policy-in-repo-state-in-store.md", None, "0007 · Politique vs état"),
    ]),
    ("Projet", [
        ("projet/vision", "docs/projet/vision.md", None, "Vision et principes"),
        ("projet/roadmap", "docs/projet/roadmap.md", None, "Roadmap"),
        ("projet/faq", "docs/projet/faq.md", None, "Questions fréquentes"),
    ]),
    ("Exemples", [
        ("exemples/app-de-reference", "examples/nolockin.yaml", "App de référence", None),
        ("exemples/minimal", "examples/minimal.yaml", "Manifeste minimal", None),
        ("exemples/propriete-separee", "examples/split-ownership", "Propriété séparée (CODEOWNERS)", None),
    ]),
]

# ----------------------------------------------------------------------------- markdown
def slugify(text):
    t = re.sub(r"`([^`]*)`", r"\1", text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = t.strip().lower()
    t = re.sub(r"[^\w\s-]", "", t)
    return re.sub(r"\s", "-", t)

def plain(text):
    t = re.sub(r"`([^`]*)`", r"\1", text)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t).strip()

def split_row(row):
    cells = re.split(r"(?<!\\)\|", row.strip())
    if cells and cells[0].strip() == "": cells = cells[1:]
    if cells and cells[-1].strip() == "": cells = cells[:-1]
    return [c.replace("\\|", "|").strip() for c in cells]

class Ctx:
    def __init__(self, page, by_src, mode, all_pages):
        self.page, self.by_src, self.mode, self.all = page, by_src, mode, all_pages
        self.ids = {}
    def uid(self, s):
        n = self.ids.get(s, 0); self.ids[s] = n + 1
        return s if n == 0 else f"{s}-{n}"
    def depth(self):
        return 0 if self.page.slug == "index" else self.page.slug.count("/") + 1
    def base(self):
        return "../" * self.depth()
    def page_href(self, target, anchor=""):
        if self.mode == "bundle":
            return "#/" + target.slug + ("/" + anchor if anchor else "")
        path = "" if target.slug == "index" else target.slug + "/"
        return self.base() + path + ("#" + anchor if anchor else "")
    def anchor_href(self, id_):
        return ("#/" + self.page.slug + "/" + id_) if self.mode == "bundle" else "#" + id_
    def resolve(self, url):
        if re.match(r"^[a-z][a-z0-9+.-]*:", url):
            return url, True
        if url.startswith("#"):
            return self.anchor_href(url[1:]), False
        path, _, anchor = url.partition("#")
        src_dir = str(pathlib.PurePosixPath(self.page.srcs[0]).parent)
        target = os.path.normpath(os.path.join(src_dir, path)).replace("\\", "/")
        if target.startswith("./"): target = target[2:]
        for cand in (target, target.rstrip("/") + "/README.md", target.rstrip("/")):
            if cand in self.by_src:
                return self.page_href(self.by_src[cand], anchor), False
        return GH + target, True

def inline(text, ctx):
    codes = []
    def stash(m):
        codes.append("<code>%s</code>" % html.escape(m.group(1), quote=False))
        return "\x00%d\x00" % (len(codes) - 1)
    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)
    def link(m):
        label, url = m.group(1), m.group(2)
        href, ext = ctx.resolve(url)
        attrs = ' target="_blank" rel="noopener"' if ext else ""
        return '<a href="%s"%s>%s</a>' % (html.escape(href, quote=True), attrs, label)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: codes[int(m.group(1))], text)

LIST_RE = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")

def convert(md, ctx, top=True):
    lines = md.split("\n"); i = 0; out = []; headings = []; title = None
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            lang = line[3:].strip(); j = i + 1; buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            code = html.escape("\n".join(buf), quote=False)
            if lang == "mermaid":
                out.append('<pre class="mermaid">%s</pre>' % code)
            else:
                out.append('<pre class="code" data-lang="%s"><code>%s</code></pre>' % (html.escape(lang or "text"), code))
            i = j + 1; continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and top and title is None:
                title = plain(text); i += 1; continue
            id_ = ctx.uid(slugify(text))
            headings.append((level, id_, plain(text)))
            out.append('<h%d id="%s">%s <a class="anchor" href="%s" aria-label="Lien vers cette section">#</a></h%d>'
                       % (level, id_, inline(text, ctx), ctx.anchor_href(id_), level))
            i += 1; continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{3,}", lines[i + 1]):
            head = split_row(line); j = i + 2; rows = []
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(split_row(lines[j])); j += 1
            t = ['<div class="table-wrap"><table><thead><tr>']
            t += ["<th>%s</th>" % inline(c, ctx) for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c, ctx) for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t)); i = j; continue
        if line.startswith(">"):
            j = i; buf = []
            while j < len(lines) and lines[j].startswith(">"):
                buf.append(re.sub(r"^>\s?", "", lines[j])); j += 1
            inner, _, _ = convert("\n".join(buf), ctx, top=False)
            out.append("<blockquote>%s</blockquote>" % inner); i = j; continue
        m = LIST_RE.match(line)
        if m:
            ordered = m.group(2)[0].isdigit(); items = []; j = i
            while j < len(lines):
                mm = LIST_RE.match(lines[j])
                if mm and mm.group(2)[0].isdigit() == ordered and not mm.group(1):
                    items.append(mm.group(3)); j += 1
                elif lines[j].startswith("  ") and lines[j].strip() and items:
                    items[-1] += " " + lines[j].strip(); j += 1
                else:
                    break
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x, ctx) for x in items), tag))
            i = j; continue
        if not line.strip():
            i += 1; continue
        j = i; buf = []
        while j < len(lines) and lines[j].strip() and not lines[j].startswith(("```", "#", "|", ">")) and not LIST_RE.match(lines[j]):
            buf.append(lines[j].strip()); j += 1
        if not buf:
            buf = [line.strip()]; j = i + 1
        out.append("<p>%s</p>" % inline(" ".join(buf), ctx)); i = j
    return "\n".join(out), headings, title

# ----------------------------------------------------------------------------- pages
class Page:
    def __init__(self, group, slug, src, title, label):
        self.group, self.slug, self.title_override, self.label_override = group, slug, title, label
        self.srcs = src if isinstance(src, list) else [src]
        self.src = src
        self.md = self.load()
        self.title = self.label = None; self.html = ""; self.headings = []; self.status = None
    def load(self):
        if isinstance(self.src, list):
            first = ROOT / self.src[0]
            parts = [first.read_text().rstrip()]
            for extra in self.src[1:]:
                f = ROOT / extra
                lang = "yaml" if f.suffix in (".yaml", ".yml") else "text"
                parts += ["", "## `%s`" % f.name, "", "```" + lang, f.read_text().rstrip(), "```"]
            return "\n".join(parts)
        p = ROOT / self.src
        if p.is_dir():
            parts = ["# " + (self.title_override or self.slug), "",
                     "Variante avec l'overlay de production dans un fichier séparé, protégé par CODEOWNERS. "
                     "Voir la [spécification du manifeste](../docs/reference/manifeste.md#overlays-dans-des-fichiers-séparés)."]
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(p).as_posix()
                    lang = "yaml" if f.suffix in (".yaml", ".yml") else "text"
                    parts += ["", "## `%s`" % rel, "", "```" + lang, f.read_text().rstrip(), "```"]
            return "\n".join(parts)
        text = p.read_text()
        if p.suffix in (".yaml", ".yml"):
            return "# %s\n\nSource : [`%s`](%s)\n\n```yaml\n%s\n```" % (self.title_override or self.slug, self.src, GH + self.src, text.rstrip())
        return text

def build_pages():
    pages = []
    for group, items in NAV:
        for slug, src, title, label in items:
            pages.append(Page(group, slug, src, title, label))
    by_src = {}
    for p in pages:
        for s_ in p.srcs:
            by_src[s_] = p
            by_src[s_.rstrip("/")] = p
    by_src["docs/architecture/adr"] = by_src.get("docs/architecture/adr/README.md")
    by_src["docs"] = by_src.get("docs/README.md")
    by_src["examples"] = by_src.get("examples/nolockin.yaml")
    by_src["docs/reference/chart.md"] = by_src.get("charts/nolockin/README.md")
    return pages, by_src

def render_pages(mode):
    pages, by_src = build_pages()
    for p in pages:
        ctx = Ctx(p, by_src, mode, pages)
        body, headings, h1 = convert(p.md, ctx)
        p.title = p.title_override or h1 or p.slug
        p.label = p.label_override or p.title
        p.html, p.headings = body, headings
        m = re.search(r"\*\*Statut\*\*\s*:\s*([^\n·]+)(?:·\s*([^\n]+))?", p.md)
        if m: p.status = (m.group(1).strip(), (m.group(2) or "").strip())
    return pages, by_src

# ----------------------------------------------------------------------------- templates
CSS = r"""
:root{--bg:#F2F5F1;--bg-2:#FFFFFF;--bg-3:#E6ECE7;--ink:#0F1D16;--ink-2:#4A5A51;--ink-3:#7C8A82;--line:#D3DCD5;--line-2:#BFCBC2;
--accent:#0E8A4A;--accent-ink:#0A6B39;--accent-soft:#DCF2E5;--accent-on:#FFFFFF;--code-bg:#E9EEEA;--shadow:0 1px 2px rgba(15,29,22,.06),0 12px 32px -16px rgba(15,29,22,.18);color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0B1410;--bg-2:#111C16;--bg-3:#18251E;--ink:#E6EEE8;--ink-2:#A6B6AC;--ink-3:#718278;--line:#22322A;--line-2:#2E4036;
--accent:#3DD68C;--accent-ink:#5FE3A3;--accent-soft:#12301F;--accent-on:#07130C;--code-bg:#0E1913;--shadow:0 1px 2px rgba(0,0,0,.4),0 12px 32px -16px rgba(0,0,0,.6);color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0B1410;--bg-2:#111C16;--bg-3:#18251E;--ink:#E6EEE8;--ink-2:#A6B6AC;--ink-3:#718278;--line:#22322A;--line-2:#2E4036;
--accent:#3DD68C;--accent-ink:#5FE3A3;--accent-soft:#12301F;--accent-on:#07130C;--code-bg:#0E1913;--shadow:0 1px 2px rgba(0,0,0,.4),0 12px 32px -16px rgba(0,0,0,.6);color-scheme:dark}
*{box-sizing:border-box}
html{scroll-padding-top:72px}
body{margin:0;background:var(--bg);color:var(--ink);font:15.5px/1.6 "IBM Plex Sans",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent-ink);text-decoration:none}
a:hover{text-decoration:underline}
code,pre,kbd{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
button{font:inherit;color:inherit}
.tnum{font-variant-numeric:tabular-nums}

/* top bar */
.top{position:sticky;top:0;z-index:30;height:56px;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top .in{height:100%;display:flex;align-items:center;gap:1rem;padding:0 1.1rem}
.brand{display:flex;align-items:center;gap:.6rem;color:var(--ink);font:900 1.1rem/1 Overpass,"Helvetica Neue",Arial,sans-serif;letter-spacing:-.02em}
.brand:hover{text-decoration:none}
.brand svg{width:26px;height:26px}
.brand .sep{color:var(--ink-3);font-weight:700;margin:0 .1rem}
.brand .docs{color:var(--ink-2);font-weight:700}
.search{position:relative;margin-left:auto;flex:0 1 380px;min-width:0}
.search input{width:100%;height:36px;border:1px solid var(--line-2);border-radius:8px;background:var(--bg-2);color:var(--ink);padding:0 2.4rem 0 2.1rem;font:inherit;font-size:.9rem}
.search input::placeholder{color:var(--ink-3)}
.search .ico{position:absolute;left:.65rem;top:50%;transform:translateY(-50%);width:15px;height:15px;color:var(--ink-3);pointer-events:none}
.search kbd{position:absolute;right:.55rem;top:50%;transform:translateY(-50%);font-size:.7rem;color:var(--ink-3);border:1px solid var(--line-2);border-radius:4px;padding:.1rem .35rem;background:var(--bg)}
.results{position:absolute;top:calc(100% + 6px);left:0;right:0;background:var(--bg-2);border:1px solid var(--line-2);border-radius:10px;box-shadow:var(--shadow);max-height:min(60vh,480px);overflow:auto;padding:.35rem;display:none;z-index:40}
.results.open{display:block}
.results a{display:block;padding:.55rem .7rem;border-radius:6px;color:var(--ink)}
.results a:hover,.results a.sel{background:var(--accent-soft);text-decoration:none}
.results .t{font-weight:600;font-size:.9rem;display:flex;gap:.4rem;align-items:baseline;flex-wrap:wrap}
.results .t span{color:var(--ink-3);font-weight:400;font-size:.8rem}
.results .x{color:var(--ink-2);font-size:.8rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.results .x mark,.results .t mark{background:transparent;color:var(--accent-ink);font-weight:600}
.results .none{padding:.7rem;color:var(--ink-3);font-size:.85rem}
.top .links{display:flex;align-items:center;gap:.25rem}
.top .links a,.iconbtn{display:inline-flex;align-items:center;gap:.4rem;height:34px;padding:0 .7rem;border-radius:7px;color:var(--ink-2);font-size:.88rem;font-weight:500;border:1px solid transparent;background:transparent;cursor:pointer}
.top .links a:hover,.iconbtn:hover{background:var(--bg-3);color:var(--ink);text-decoration:none}
.iconbtn svg{width:16px;height:16px}
.menubtn{display:none}
@media (max-width:860px){.top .links a.txt{display:none}.menubtn{display:inline-flex}.search{flex-basis:220px}}
@media (max-width:560px){.brand .docs,.brand .sep{display:none}.search kbd{display:none}}

/* layout */
.shell{display:grid;grid-template-columns:260px minmax(0,1fr) 220px;gap:0;max-width:1400px;margin:0 auto}
.side{position:sticky;top:56px;height:calc(100vh - 56px);overflow-y:auto;border-right:1px solid var(--line);padding:1.2rem 1rem 2rem 1.1rem;font-size:.9rem}
.side h4{margin:1.1rem 0 .35rem;padding:0 .5rem;font:600 .68rem/1 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3)}
.side h4:first-child{margin-top:0}
.side ul{list-style:none;margin:0;padding:0}
.side li a{display:block;padding:.38rem .55rem;border-radius:6px;color:var(--ink-2);line-height:1.35}
.side li a:hover{background:var(--bg-3);color:var(--ink);text-decoration:none}
.side li a.on{background:var(--accent-soft);color:var(--accent-ink);font-weight:600}
.scrim{display:none}
@media (max-width:1100px){.shell{grid-template-columns:260px minmax(0,1fr)}.toc{display:none}}
@media (max-width:860px){
  .shell{grid-template-columns:minmax(0,1fr)}
  .side{position:fixed;left:0;top:56px;width:min(300px,86vw);background:var(--bg);z-index:25;transform:translateX(-102%);transition:transform .18s ease;box-shadow:var(--shadow)}
  body.nav-open .side{transform:none}
  body.nav-open .scrim{display:block;position:fixed;inset:56px 0 0 0;background:rgba(0,0,0,.35);z-index:24}
}

/* content */
.main{min-width:0;padding:1.6rem clamp(1.1rem,3.5vw,3rem) 3rem}
.crumbs{display:flex;gap:.5rem;align-items:center;font-size:.82rem;color:var(--ink-3);margin-bottom:.9rem}
.crumbs a{color:var(--ink-3)}
.crumbs b{color:var(--ink-2);font-weight:500}
.status{display:inline-flex;align-items:center;gap:.4rem;font:600 .7rem/1 "IBM Plex Mono",monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--accent-ink);background:var(--accent-soft);border-radius:999px;padding:.35rem .6rem .3rem;margin:.6rem 0 0}
.status i{width:.5rem;height:.5rem;border-radius:50%;background:var(--accent);display:inline-block}
.status span{color:var(--ink-3);font-weight:500;text-transform:none;letter-spacing:0}
.prose{max-width:820px}
.prose h1{font:900 clamp(1.9rem,3.4vw,2.6rem)/1.08 Overpass,"Helvetica Neue",Arial,sans-serif;letter-spacing:-.02em;margin:0 0 .4rem;text-wrap:balance}
.prose h2{font:800 1.45rem/1.2 Overpass,sans-serif;letter-spacing:-.01em;margin:2.4rem 0 .8rem;padding-top:1.2rem;border-top:1px solid var(--line)}
.prose h3{font:700 1.12rem/1.3 Overpass,sans-serif;margin:1.8rem 0 .6rem}
.prose h4{font:600 .95rem/1.3 "IBM Plex Sans",sans-serif;margin:1.4rem 0 .5rem;color:var(--ink-2)}
.prose .anchor{color:var(--ink-3);opacity:0;margin-left:.1em;font-weight:400;font-size:.85em}
.prose h2:hover .anchor,.prose h3:hover .anchor,.prose h4:hover .anchor{opacity:1}
.prose p{margin:0 0 1rem;max-width:74ch}
.prose ul,.prose ol{margin:0 0 1rem;padding-left:1.4rem;max-width:74ch}
.prose li{margin:.3rem 0}
.prose li::marker{color:var(--ink-3)}
.prose a{text-decoration:underline;text-decoration-color:color-mix(in srgb,var(--accent) 45%,transparent);text-underline-offset:.15em}
.prose a:hover{text-decoration-color:var(--accent)}
.prose code{background:var(--code-bg);border:1px solid var(--line);border-radius:4px;padding:.08em .35em;font-size:.86em;color:var(--ink)}
.prose pre{margin:0 0 1.2rem;background:var(--code-bg);border:1px solid var(--line);border-radius:8px;padding:.95rem 1.1rem;overflow-x:auto;font-size:.84rem;line-height:1.55;position:relative}
.prose pre code{background:none;border:none;padding:0;font-size:inherit;color:var(--ink)}
.prose pre[data-lang]:not([data-lang="text"])::before{content:attr(data-lang);position:absolute;top:.4rem;right:.65rem;font:500 .65rem/1 "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.prose pre.mermaid{background:var(--bg-2);text-align:center;font-size:.8rem}
.prose blockquote{margin:0 0 1.2rem;padding:.6rem 1.1rem;border-left:3px solid var(--accent);background:var(--accent-soft);border-radius:0 8px 8px 0;color:var(--ink)}
.prose blockquote p{margin:0;font-size:1.05rem;font-weight:500}
.table-wrap{overflow-x:auto;margin:0 0 1.3rem;border:1px solid var(--line);border-radius:8px}
.prose table{border-collapse:collapse;width:100%;font-size:.88rem;line-height:1.5}
.prose th,.prose td{text-align:left;vertical-align:top;padding:.6rem .8rem;border-bottom:1px solid var(--line)}
.prose th{font:600 .7rem/1.3 "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);background:var(--bg-3);white-space:nowrap}
.prose tr:last-child td{border-bottom:none}
.prose td code{white-space:nowrap}
.prose strong{font-weight:600}
.pager{display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin-top:3rem;padding-top:1.4rem;border-top:1px solid var(--line);max-width:820px}
.pager a{display:flex;flex-direction:column;gap:.25rem;padding:.9rem 1rem;border:1px solid var(--line);border-radius:8px;color:var(--ink);background:var(--bg-2)}
.pager a:hover{border-color:var(--accent);text-decoration:none}
.pager a.next{text-align:right;grid-column:2}
.pager small{font:500 .7rem/1 "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.pager b{font-weight:600}
.edit{margin-top:1.6rem;font-size:.84rem;color:var(--ink-3)}
.edit a{color:var(--ink-2)}

/* toc */
.toc{position:sticky;top:56px;height:calc(100vh - 56px);overflow-y:auto;padding:1.4rem 1rem 2rem .5rem;font-size:.82rem;border-left:1px solid var(--line)}
.toc h4{margin:0 0 .5rem;font:600 .68rem/1 "IBM Plex Mono",monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3)}
.toc ul{list-style:none;margin:0;padding:0}
.toc li a{display:block;padding:.25rem .6rem;color:var(--ink-3);border-left:2px solid transparent;margin-left:-1px;line-height:1.4}
.toc li.l3 a{padding-left:1.3rem}
.toc li a:hover{color:var(--ink);text-decoration:none}
.toc li a.on{color:var(--accent-ink);border-left-color:var(--accent);font-weight:500}

/* home cards */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:.75rem;margin:1.2rem 0 1.6rem}
.cards a{display:flex;flex-direction:column;gap:.3rem;padding:.95rem 1rem;border:1px solid var(--line);border-radius:8px;background:var(--bg-2);color:var(--ink);text-decoration:none}
.cards a:hover{border-color:var(--accent);text-decoration:none}
.cards b{font-weight:600}
.cards span{font-size:.84rem;color:var(--ink-2)}

/* bundle mode */
.bundle .page{display:none}
.bundle .page.active{display:block}
footer.foot{border-top:1px solid var(--line);padding:1.4rem clamp(1.1rem,3.5vw,3rem);font-size:.82rem;color:var(--ink-3);display:flex;gap:1rem;flex-wrap:wrap;justify-content:space-between}
footer.foot a{color:var(--ink-2)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

JS = r"""
(function(){
  var root=document.documentElement, body=document.body;
  var MODE=body.dataset.mode||'multi', BASE=body.dataset.base||'';
  /* thème */
  var tbtn=document.getElementById('themebtn');
  function applyTheme(t){ if(t){root.setAttribute('data-theme',t)} else {root.removeAttribute('data-theme')} try{ if(t) localStorage.setItem('nlk-theme',t); else localStorage.removeItem('nlk-theme') }catch(e){} }
  function isDark(){ var t=root.getAttribute('data-theme'); if(t) return t==='dark'; return window.matchMedia('(prefers-color-scheme: dark)').matches }
  if(tbtn){ tbtn.addEventListener('click',function(){ applyTheme(isDark()?'light':'dark'); if(window.mermaid){ location.reload() } }) }
  /* menu mobile */
  var mbtn=document.getElementById('menubtn'), scrim=document.getElementById('scrim');
  if(mbtn){ mbtn.addEventListener('click',function(){ body.classList.toggle('nav-open') }) }
  if(scrim){ scrim.addEventListener('click',function(){ body.classList.remove('nav-open') }) }
  /* mermaid (site multi-pages uniquement ; l'aperçu le rend nativement) */
  if(window.mermaid){ mermaid.initialize({startOnLoad:true, theme:isDark()?'dark':'neutral', fontFamily:'IBM Plex Sans, sans-serif'}) }
  /* TOC actif */
  function wireToc(scope){
    var links=[].slice.call((scope||document).querySelectorAll('.toc a[href]')); if(!links.length) return;
    var map={}; links.forEach(function(a){ var id=a.getAttribute('data-id'); if(id) map[id]=a });
    var hs=[].slice.call((scope||document).querySelectorAll('.prose h2[id],.prose h3[id]'));
    if(!('IntersectionObserver' in window)||!hs.length) return;
    var cur=null;
    var io=new IntersectionObserver(function(es){
      es.forEach(function(e){ if(e.isIntersecting){ if(cur) cur.classList.remove('on'); cur=map[e.target.id]; if(cur) cur.classList.add('on') } });
    },{rootMargin:'-60px 0px -70% 0px',threshold:0});
    hs.forEach(function(h){ io.observe(h) });
  }
  /* recherche */
  var input=document.getElementById('q'), box=document.getElementById('results'), index=null, sel=-1;
  function loadIndex(cb){ if(index){cb();return} if(window.__NLK_INDEX){index=window.__NLK_INDEX;cb();return}
    fetch(BASE+'assets/search-index.json').then(function(r){return r.json()}).then(function(j){index=j;cb()}).catch(function(){index=[];cb()}) }
  function norm(s){ return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'') }
  function esc(s){ return s.replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]}) }
  function hl(s,terms){ var out=esc(s); terms.forEach(function(t){ if(!t) return; var re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig'); out=out.replace(re,'<mark>$1</mark>') }); return out }
  function search(q){
    var terms=norm(q).split(/\s+/).filter(Boolean); if(!terms.length){ box.classList.remove('open'); return }
    var scored=[];
    index.forEach(function(e){
      var t=norm(e.t), s=norm(e.s||''), x=norm(e.x||''), score=0, ok=true;
      terms.forEach(function(term){ var a=t.indexOf(term)>=0, b=s.indexOf(term)>=0, c=x.indexOf(term)>=0; if(!(a||b||c)) ok=false; score+= (a?6:0)+(b?4:0)+(c?1:0) });
      if(ok) scored.push([score,e]);
    });
    scored.sort(function(a,b){return b[0]-a[0]}); scored=scored.slice(0,10); sel=-1;
    if(!scored.length){ box.innerHTML='<div class="none">Aucun résultat pour « '+esc(q)+' »</div>'; box.classList.add('open'); return }
    box.innerHTML=scored.map(function(p){ var e=p[1]; var pos=norm(e.x||'').indexOf(terms[0]); var snip=(e.x||''); if(pos>60) snip='…'+snip.slice(pos-50); 
      return '<a href="'+e.u+'"><div class="t">'+hl(e.t,terms)+(e.s?'<span>› '+hl(e.s,terms)+'</span>':'')+'</div><div class="x">'+hl(snip.slice(0,160),terms)+'</div></a>' }).join('');
    box.classList.add('open');
  }
  if(input){
    input.addEventListener('focus',function(){ loadIndex(function(){}) });
    input.addEventListener('input',function(){ loadIndex(function(){ search(input.value) }) });
    input.addEventListener('keydown',function(e){
      var items=box.querySelectorAll('a');
      if(e.key==='Escape'){ box.classList.remove('open'); input.blur() }
      else if(e.key==='ArrowDown'&&items.length){ e.preventDefault(); sel=Math.min(sel+1,items.length-1); items.forEach(function(a,i){a.classList.toggle('sel',i===sel)}) }
      else if(e.key==='ArrowUp'&&items.length){ e.preventDefault(); sel=Math.max(sel-1,0); items.forEach(function(a,i){a.classList.toggle('sel',i===sel)}) }
      else if(e.key==='Enter'&&sel>=0&&items[sel]){ items[sel].click() }
    });
    document.addEventListener('click',function(e){ if(!box.contains(e.target)&&e.target!==input) box.classList.remove('open') });
    document.addEventListener('keydown',function(e){ if(e.key==='/'&&document.activeElement!==input&&!/input|textarea/i.test(document.activeElement.tagName)){ e.preventDefault(); input.focus() } });
    box.addEventListener('click',function(){ box.classList.remove('open'); if(MODE==='bundle') input.value='' });
  }
  /* routeur du bundle */
  if(MODE==='bundle'){
    var pages=[].slice.call(document.querySelectorAll('.page'));
    var navLinks=[].slice.call(document.querySelectorAll('.side a[data-slug]'));
    function route(){
      var h=location.hash.replace(/^#\/?/,''); var parts=h.split('/').filter(Boolean); var slug='index', id='';
      var known={}; pages.forEach(function(p){known[p.dataset.page]=1});
      for(var k=parts.length;k>0;k--){ var cand=parts.slice(0,k).join('/'); if(known[cand]){ slug=cand; id=parts.slice(k).join('/'); break } }
      pages.forEach(function(p){ p.classList.toggle('active',p.dataset.page===slug) });
      navLinks.forEach(function(a){ a.classList.toggle('on',a.dataset.slug===slug) });
      var active=document.querySelector('.page.active'); document.title=(active&&active.dataset.title?active.dataset.title+' · ':'')+'NoLockIn Docs';
      body.classList.remove('nav-open');
      if(id){ var el=active&&active.querySelector('#'+CSS.escape(id)); if(el){ el.scrollIntoView() } } else { window.scrollTo(0,0) }
      wireToc(active);
    }
    window.addEventListener('hashchange',route); route();
  } else { wireToc(document); }
  /* fermer le menu au clic sur un lien */
  [].slice.call(document.querySelectorAll('.side a')).forEach(function(a){ a.addEventListener('click',function(){ body.classList.remove('nav-open') }) });
})();
"""

LOGO = '''<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="2" y="2" width="28" height="28" rx="4" fill="var(--accent)"/><path d="M11 15V11.5a5 5 0 0 1 10 0" fill="none" stroke="var(--accent-on)" stroke-width="2.6" stroke-linecap="round" transform="rotate(-28 16 12)"/><rect x="8.5" y="15" width="15" height="11" rx="2" fill="var(--accent-on)"/><path d="M16 18.5v3" stroke="var(--accent)" stroke-width="2.4" stroke-linecap="round"/></svg>'''
ICO_SEARCH = '<svg class="ico" viewBox="0 0 16 16" aria-hidden="true"><circle cx="7" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'
ICO_THEME = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.5a6.5 6.5 0 1 0 0 13V1.5z" fill="currentColor"/><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
ICO_MENU = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
ICO_GH = '<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M8 .2a8 8 0 0 0-2.5 15.6c.4 0 .5-.2.5-.4v-1.5c-2.2.5-2.7-1-2.7-1-.4-.9-.9-1.2-.9-1.2-.7-.5.1-.5.1-.5.8.1 1.2.8 1.2.8.7 1.3 1.9.9 2.4.7.1-.5.3-.9.5-1.1-1.8-.2-3.6-.9-3.6-4 0-.9.3-1.6.8-2.1-.1-.2-.4-1 .1-2.1 0 0 .7-.2 2.2.8a7.5 7.5 0 0 1 4 0c1.5-1 2.2-.8 2.2-.8.4 1.1.2 1.9.1 2.1.5.6.8 1.3.8 2.1 0 3.1-1.9 3.7-3.6 3.9.3.3.5.8.5 1.5v2.2c0 .2.1.5.6.4A8 8 0 0 0 8 .2z"/></svg>'

def sidebar(pages, current, ctx):
    parts = []
    for group, _ in NAV:
        parts.append("<h4>%s</h4><ul>" % html.escape(group))
        for p in pages:
            if p.group != group: continue
            on = ' class="on"' if p is current else ""
            parts.append('<li><a href="%s" data-slug="%s"%s>%s</a></li>' % (ctx.page_href(p), p.slug, on, html.escape(p.label)))
        parts.append("</ul>")
    return "".join(parts)

def toc(page, ctx):
    hs = [(l, i, t) for l, i, t in page.headings if l in (2, 3)]
    if len(hs) < 2: return ""
    items = "".join('<li class="l%d"><a href="%s" data-id="%s">%s</a></li>' % (l, ctx.anchor_href(i), i, html.escape(t)) for l, i, t in hs)
    return '<h4>Sur cette page</h4><ul>%s</ul>' % items

START = {
    "demarrer/introduction": "Ce qu'est NoLockIn, pour qui, les trois garanties.",
    "demarrer/installation": "La CLI nlk, la connexion, les contextes.",
    "demarrer/premiere-app": "De nlk init à une URL en ligne, en cinq minutes.",
    "demarrer/environnements": "Staging et production dans un fichier, promotion, approbation.",
}
def home_cards(pages, ctx):
    cards = []
    for p in pages:
        if p.slug in START:
            cards.append('<a href="%s"><b>%s</b><span>%s</span></a>' % (ctx.page_href(p), html.escape(p.label), html.escape(START[p.slug])))
    return '<h2 id="commencer-vite">Commencer</h2><div class="cards">%s</div>' % "".join(cards)

def article(page, pages, ctx, mode):
    flat = pages; idx = flat.index(page)
    prev = flat[idx - 1] if idx > 0 else None
    nxt = flat[idx + 1] if idx + 1 < len(flat) else None
    crumbs = '<nav class="crumbs" aria-label="Fil d\'Ariane"><a href="%s">Docs</a><span>/</span><b>%s</b>%s</nav>' % (
        ctx.page_href(pages[0]), html.escape(page.group), "" if page.slug == "index" else "<span>/</span><b>%s</b>" % html.escape(page.label))
    status = ""
    if page.status:
        status = '<div class="status"><i></i>%s%s</div>' % (html.escape(page.status[0]), (" <span>· %s</span>" % html.escape(page.status[1])) if page.status[1] else "")
    body = page.html
    if page.slug == "index":
        k = body.find("<h2 ")
        body = (body[:k] + home_cards(pages, ctx) + body[k:]) if k >= 0 else home_cards(pages, ctx) + body
    pager = ""
    if prev or nxt:
        pager = '<nav class="pager" aria-label="Pagination">'
        if prev: pager += '<a class="prev" href="%s"><small>← Précédent</small><b>%s</b></a>' % (ctx.page_href(prev), html.escape(prev.label))
        if nxt: pager += '<a class="next" href="%s"><small>Suivant →</small><b>%s</b></a>' % (ctx.page_href(nxt), html.escape(nxt.label))
        pager += "</nav>"
    src = page.srcs[0] if not (ROOT / page.srcs[0]).is_dir() else page.srcs[0] + "/"
    edit = '<p class="edit">Source : <a href="%s%s" target="_blank" rel="noopener">%s</a></p>' % (GH if not src.endswith("/") else GH.replace("/blob/", "/tree/"), src, html.escape(src))
    return '''%s<article class="prose"><h1>%s</h1>%s
%s
%s%s</article>''' % (crumbs, html.escape(page.title), status, body, pager, edit)

def head_common(title, base, mode, inline_css):
    fonts = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="%s">' % FONTS
    css = "<style>%s</style>" % CSS if inline_css else '<link rel="stylesheet" href="%sassets/docs.css">' % base
    theme = "<script>try{var t=localStorage.getItem('nlk-theme');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>" if mode == "multi" else ""
    return "<title>%s</title>%s%s%s" % (html.escape(title), fonts, css, theme)

def topbar(base, mode):
    site = base + "../index.html" if mode == "multi" else "https://nolockin.io"
    themebtn = '<button class="iconbtn" id="themebtn" aria-label="Changer de thème">%s</button>' % ICO_THEME if mode == "multi" else ""
    return '''<header class="top"><div class="in">
<button class="iconbtn menubtn" id="menubtn" aria-label="Menu">%s</button>
<a class="brand" href="%s">%sNoLockIn<span class="sep">/</span><span class="docs">Docs</span></a>
<div class="search" role="search">%s<input id="q" type="search" placeholder="Rechercher dans la doc…" autocomplete="off" aria-label="Rechercher"><kbd>/</kbd><div class="results" id="results" role="listbox"></div></div>
<nav class="links"><a class="txt" href="%s">Site</a><a href="https://github.com/do-now-io/nolockin" target="_blank" rel="noopener" aria-label="GitHub">%s<span class="txt">GitHub</span></a>%s</nav>
</div></header>''' % (ICO_MENU, site, LOGO, ICO_SEARCH, site, ICO_GH, themebtn)

FOOT = '<footer class="foot"><span>NoLockIn · Documentation · Apache-2.0</span><span><a href="https://github.com/do-now-io/nolockin/tree/main/docs" target="_blank" rel="noopener">Proposer une modification</a></span></footer>'

def strip_tags(s):
    s = re.sub(r"<pre class=\"mermaid\">.*?</pre>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def search_index(pages, mode):
    entries = []
    for p in pages:
        ctx = Ctx(p, {}, mode, pages)
        ctx.page = p
        # href from docs root (index depth 0) in multi mode
        root_ctx = Ctx(pages[0], {}, mode, pages)
        chunks = re.split(r'(?=<h2 id=")', p.html)
        for ch in chunks:
            m = re.match(r'<h2 id="([^"]+)">(.*?) <a class="anchor"', ch, flags=re.S)
            sec = strip_tags(m.group(2)) if m else ""
            anchor = m.group(1) if m else ""
            text = strip_tags(ch[m.end():] if m else ch)[:500]
            if not text and not sec: continue
            entries.append({"t": p.title, "s": sec, "u": root_ctx.page_href(p, anchor), "x": text})
    return entries

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

def build_multi():
    pages, by_src = render_pages("multi")
    for p in pages:
        ctx = Ctx(p, by_src, "multi", pages)
        base = ctx.base()
        doc = '''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="%s">
%s
</head>
<body data-mode="multi" data-base="%s">
%s
<div class="scrim" id="scrim"></div>
<div class="shell">
<nav class="side" aria-label="Navigation de la documentation">%s</nav>
<main class="main">%s</main>
<aside class="toc" aria-label="Sommaire de la page">%s</aside>
</div>
%s
<script src="%s"></script>
<script src="%sassets/docs.js"></script>
</body>
</html>''' % (html.escape("Documentation NoLockIn : " + p.title), head_common(p.title + " · NoLockIn Docs", base, "multi", False), base,
             topbar(base, "multi"), sidebar(pages, p, ctx), article(p, pages, ctx, "multi"), toc(p, ctx), FOOT, MERMAID, base)
        out = OUT / ("index.html" if p.slug == "index" else p.slug + "/index.html")
        write(out, doc)
    write(OUT / "assets" / "docs.css", CSS.strip() + "\n")
    write(OUT / "assets" / "docs.js", JS.strip() + "\n")
    write(OUT / "assets" / "search-index.json", json.dumps(search_index(pages, "multi"), ensure_ascii=False))
    print("multi: %d pages → %s" % (len(pages), OUT.relative_to(ROOT)))

def build_bundle(dest):
    pages, by_src = render_pages("bundle")
    ctx0 = Ctx(pages[0], by_src, "bundle", pages)
    arts = []
    for p in pages:
        ctx = Ctx(p, by_src, "bundle", pages)
        arts.append('<section class="page%s" data-page="%s" data-title="%s"><main class="main">%s</main><aside class="toc">%s</aside></section>'
                    % (" active" if p.slug == "index" else "", p.slug, html.escape(p.title), article(p, pages, ctx, "bundle"), toc(p, ctx)))
    idx = json.dumps(search_index(pages, "bundle"), ensure_ascii=False).replace("</", "<\\/")
    doc = '''%s
<style>.bundle .shell{grid-template-columns:260px minmax(0,1fr)}.bundle .page{display:none;grid-column:2}.bundle .page.active{display:grid;grid-template-columns:minmax(0,1fr) 220px}.bundle .page .toc{position:sticky}@media (max-width:1100px){.bundle .page.active{grid-template-columns:1fr}.bundle .page .toc{display:none}}@media (max-width:860px){.bundle .shell{grid-template-columns:1fr}.bundle .page{grid-column:1}}</style>
%s
<div class="scrim" id="scrim"></div>
<div class="shell">
<nav class="side" aria-label="Navigation de la documentation">%s</nav>
%s
</div>
%s
<script>window.__NLK_INDEX=%s;</script>
<script>%s</script>''' % (head_common("NoLockIn Docs", "", "bundle", True), topbar("", "bundle"), sidebar(pages, None, ctx0), "".join(arts), FOOT, idx, JS)
    # body attrs are set by the host: emulate via a wrapper class + dataset on body at runtime
    doc = doc.replace('<div class="scrim"', '<script>document.body.classList.add("bundle");document.body.dataset.mode="bundle";</script>\n<div class="scrim"', 1)
    pathlib.Path(dest).write_text(doc)
    print("bundle: %d pages → %s" % (len(pages), dest))

if __name__ == "__main__":
    if "--bundle" in sys.argv:
        build_bundle(sys.argv[sys.argv.index("--bundle") + 1])
    else:
        build_multi()
