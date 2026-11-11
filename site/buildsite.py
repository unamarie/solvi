"""Wraps the page sources in site/src into full HTML documents for Vercel:
src/index.html -> site/index.html, src/demo.html -> site/demo/index.html."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
HEAD = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')

# Sun/moon switch on every page. Follows the device until the visitor picks; the choice is remembered.
THEME_HEAD = ('<script>try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")'
              'document.documentElement.setAttribute("data-theme",t)}catch(e){}</script>\n')
THEME_BUTTON = """
<button id="theme-toggle" type="button" aria-label="Switch light or dark mode">
<svg class="i-sun" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 1.5v2.5M12 20v2.5M1.5 12h2.5M20 12h2.5M4.6 4.6l1.8 1.8M17.6 17.6l1.8 1.8M4.6 19.4l1.8-1.8M17.6 6.4l1.8-1.8"/></g></svg>
<svg class="i-moon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z" fill="currentColor"/></svg>
</button>
<style>
#theme-toggle{position:fixed;right:max(14px,env(safe-area-inset-right,0px));bottom:max(14px,env(safe-area-inset-bottom,0px));z-index:50;
  width:44px;height:44px;border-radius:50%;border:1px solid var(--line);background:var(--surface);color:var(--ink);
  display:grid;place-items:center;cursor:pointer;box-shadow:0 2px 8px rgba(10,18,54,.18);padding:0}
#theme-toggle:hover{color:var(--stamp,#f85e0a)}
#theme-toggle:focus-visible{outline:2px solid #f85e0a;outline-offset:2px}
#theme-toggle .i-sun{display:none}
:root[data-theme="dark"] #theme-toggle .i-sun{display:block}:root[data-theme="dark"] #theme-toggle .i-moon{display:none}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) #theme-toggle .i-sun{display:block}:root:not([data-theme="light"]) #theme-toggle .i-moon{display:none}}
@media print{#theme-toggle{display:none}}
</style>
<script>
(function(){var b=document.getElementById("theme-toggle"),r=document.documentElement;
function dark(){var t=r.getAttribute("data-theme");return t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches}
b.addEventListener("click",function(){var t=dark()?"light":"dark";r.setAttribute("data-theme",t);try{localStorage.setItem("theme",t)}catch(e){}});})();
</script>"""

def wrap_text(s, dst):
    cut = s.index("</style>") + len("</style>")
    head, body = s[:cut], s[cut:]
    os.makedirs(os.path.dirname(os.path.join(HERE, dst)), exist_ok=True)
    with open(os.path.join(HERE, dst), "w", encoding="utf-8") as f:
        f.write(HEAD + THEME_HEAD + head + "\n</head>\n<body>" + body + THEME_BUTTON + "\n</body>\n</html>\n")
    print("wrote", dst)

def wrap(src, dst):
    wrap_text(open(os.path.join(HERE, "src", src), encoding="utf-8").read(), dst)

import json
APPS = {  # one app per user group; each shows only its own views
    "quality": {"title": "Solvi · Safety and quality", "owner": "For quality and HSE · data from the HSEQ, delivery, supply and assets domains", "views": ["risk", "compliance"]},
    "service": {"title": "Solvi · Service", "owner": "For the service team · data from the assets and core domains", "views": ["production"]},
    "sales":   {"title": "Solvi · Sales", "owner": "For sellers, sales lead and customer service · data from the sales and core domains", "views": ["proposals", "followup", "history"]},
}
def wrap_app(app, cfg):   # builds the app straight from the template, no temporary files
    s = open(os.path.join(HERE, "src", "demo.html"), encoding="utf-8").read()
    s = s.replace('<script src="https://cdn.jsdelivr.net', f'<script>window.SOLVI_APP = {json.dumps(cfg)};</script>\n<script src="https://cdn.jsdelivr.net', 1)
    wrap_text(s, f"solvi/{app}/index.html")

wrap("index.html", "index.html")
wrap("solvi.html", "solvi/index.html")
for app, cfg in APPS.items(): wrap_app(app, cfg)
wrap("play.html", "play/index.html")
wrap("cv.html", "cv/index.html")
wrap("hi.html", "hi/index.html")
# old links keep working
os.makedirs(os.path.join(HERE, "demo"), exist_ok=True)
open(os.path.join(HERE, "demo", "index.html"), "w").write('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0; url=../solvi/index.html"><title>Solvi</title><a href="../solvi/index.html">Solvi</a>\n')
