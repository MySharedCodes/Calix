"""Retrieve upstream license texts for crates whose archives omit them."""
import base64
import json
from pathlib import Path
import urllib.request

dest = Path(__file__).resolve().parents[1] / "docs/licenses"
dest.mkdir(parents=True, exist_ok=True)
sources = {"alloc-stdlib-LICENSE.txt": "dropbox/rust-alloc-no-stdlib",
           "webview2-rs-LICENSE.txt": "wravery/webview2-rs",
           "katex-fonts-LICENSE.txt": "KaTeX/katex-fonts",
           "remark-math-LICENSE.txt": "remarkjs/remark-math"}
for filename, repo in sources.items():
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/license", headers={"User-Agent": "Calix-License-Review"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    (dest / filename).write_bytes(base64.b64decode(data["content"]))
    print(filename, data["html_url"])
