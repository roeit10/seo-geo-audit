#!/usr/bin/env python3
"""
seo-geo-audit: detect what a site is built on, from the outside, read-only.

Looks at headers, the HTML and a few well-known public endpoints. No login, no writes.
Output: JSON with platform, confidence, evidence, hosting, SEO plugin (WordPress)
and which connect-<platform>.md reference to follow.

Usage: python3 detect.py https://example.co.il [--out seo-geo/detect.json]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import fetch  # noqa: E402

REF = {
    "wordpress": "connect-wordpress.md", "wix": "connect-wix.md", "shopify": "connect-shopify.md",
    "webflow": "connect-other.md", "framer": "connect-other.md", "squarespace": "connect-other.md",
    "code": "connect-code.md", "unknown": "connect-other.md",
}
NAME_HE = {
    "wordpress": "וורדפרס", "wix": "Wix", "shopify": "Shopify", "webflow": "Webflow", "framer": "Framer",
    "squarespace": "Squarespace", "code": "אתר בקוד", "unknown": "לא זוהה",
}


def detect(url):
    if not url.startswith("http"):
        url = "https://" + url
    url = url.rstrip("/")
    r = fetch(url + "/")
    h = r["headers"]
    body = r["body"][:800_000]
    low = body.lower()
    gen = " ".join(re.findall(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', body, re.I) +
                   re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']generator["\']', body, re.I))
    ev = {k: [] for k in REF}
    if r["status"] == 0:
        return {"url": url, "reachable": False, "error": r["error"]}

    # --- builders
    if "wordpress" in gen.lower():
        ev["wordpress"].append(f"generator: {gen}")
    if "/wp-content/" in low or "/wp-includes/" in low:
        ev["wordpress"].append("wp-content / wp-includes ב-HTML")
    if "api.w.org" in low or "api.w.org" in h.get("link", ""):
        ev["wordpress"].append("קישור ל-REST API של וורדפרס (api.w.org)")
    if "wix.com" in gen.lower():
        ev["wix"].append(f"generator: {gen}")
    if any(k.startswith("x-wix") for k in h):
        ev["wix"].append("כותרת x-wix-* מהשרת")
    if "static.wixstatic.com" in low or "parastorage.com" in low:
        ev["wix"].append("קבצים מ-wixstatic / parastorage")
    if "shopify.theme" in low or "cdn.shopify.com/s/files" in low:
        ev["shopify"].append("Shopify.theme / קבצי חנות מ-cdn.shopify.com ב-HTML")
    if "x-shopid" in h or "x-shopify-stage" in h or "shopify" in h.get("powered-by", "").lower():
        ev["shopify"].append("כותרת Shopify מהשרת")
    if "webflow" in gen.lower() or "data-wf-site" in low:
        ev["webflow"].append("Webflow (generator / data-wf-site)")
    if "framer" in gen.lower() or "framerusercontent.com" in low or "data-framer-" in low:
        ev["framer"].append("Framer (generator / data-framer)")
    if "squarespace" in gen.lower() or "static1.squarespace.com" in low:
        ev["squarespace"].append("Squarespace")

    # --- code frameworks
    fw = None
    if "/_next/static" in low or "__next_data__" in low or "self.__next_f" in low or "x-nextjs-cache" in h or "x-nextjs-prerender" in h:
        fw = "Next.js"
    elif "astro" in gen.lower() or "astro-island" in low:
        fw = "Astro"
    elif "gatsby" in gen.lower() or "___gatsby" in low:
        fw = "Gatsby"
    elif "hugo" in gen.lower():
        fw = "Hugo"
    elif "/_nuxt/" in low or "__nuxt" in low:
        fw = "Nuxt"
    elif "docusaurus" in gen.lower():
        fw = "Docusaurus"
    elif re.search(r'id=["\']root["\']></div>|id=["\']app["\']></div>', low) and "/assets/index-" in low:
        fw = "React/Vite (SPA)"
    if fw:
        ev["code"].append(f"framework: {fw}")

    hosting = None
    if "x-vercel-id" in h or "vercel" in h.get("server", "").lower():
        hosting = "Vercel"
    elif "x-nf-request-id" in h or "netlify" in h.get("server", "").lower():
        hosting = "Netlify"
    elif "cf-ray" in h:
        hosting = "Cloudflare (CDN או Pages)"
    elif "github.com" in h.get("server", "").lower():
        hosting = "GitHub Pages"
    elif "x-litespeed-cache" in h or "litespeed" in h.get("server", "").lower():
        hosting = "LiteSpeed (אחסון שיתופי נפוץ לוורדפרס)"
    if hosting in ("Vercel", "Netlify", "GitHub Pages") and not any(ev[k] for k in ev if k != "code"):
        ev["code"].append(f"hosting: {hosting}")

    builder_hits = {k: sum(2 if x.startswith("generator") or "כותרת" in x else 1 for x in v)
                    for k, v in ev.items() if v and k != "code"}
    if builder_hits:
        platform = max(builder_hits, key=builder_hits.get)
    elif ev["code"]:
        platform = "code"
    else:
        platform = "unknown"
    n = len(ev.get(platform, []))
    confidence = "high" if n >= 2 else ("medium" if n == 1 else "low")

    out = {"url": url, "reachable": True, "status": r["status"], "final_url": r["url"],
           "platform": platform, "platform_he": NAME_HE[platform], "confidence": confidence,
           "framework": fw, "hosting": hosting, "evidence": ev[platform] if platform in ev else [],
           "connect_reference": REF[platform]}

    # --- WordPress extras: REST + SEO plugin, read-only and public
    if platform == "wordpress":
        j = fetch(url + "/wp-json/", max_bytes=400_000)
        ns = []
        try:
            ns = json.loads(j["body"]).get("namespaces", [])
        except Exception:
            pass
        out["wp_rest"] = {"status": j["status"], "ok": j["status"] == 200 and bool(ns)}
        plugin = None
        if any(x.startswith("yoast") for x in ns) or "yoast seo" in low:
            plugin = "Yoast SEO"
        elif any(x.startswith("rankmath") for x in ns) or "rank math" in low:
            plugin = "Rank Math"
        elif "aioseo" in low or any("aioseo" in x for x in ns):
            plugin = "All in One SEO"
        elif "seopress" in low:
            plugin = "SEOPress"
        out["wp_seo_plugin"] = plugin
        out["wp_namespaces"] = [x for x in ns if any(k in x for k in ("yoast", "rankmath", "aioseo", "seopress", "wp/v2"))]
        pg = fetch(url + "/wp-json/wp/v2/pages?per_page=1&_fields=id,link,title", max_bytes=50_000)
        out["wp_pages_readable"] = pg["status"] == 200
        out["wordpress_com"] = "wordpress.com" in h.get("host-header", "") or "wp.com" in low and "wpcomstaging" in low
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    res = detect(sys.argv[1])
    js = json.dumps(res, ensure_ascii=False, indent=2)
    if "--out" in sys.argv:
        p = sys.argv[sys.argv.index("--out") + 1]
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        open(p, "w", encoding="utf-8").write(js)
    print(js)


if __name__ == "__main__":
    main()
