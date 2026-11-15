#!/usr/bin/env python3
"""
seo-geo-audit: deterministic SEO + GEO checker.

Fetches a site (live, or a local build), runs every check in code and writes one
JSON file with findings and a 0-100 score per category. Claude only reads the
JSON and explains it; it never recomputes a score.

Stdlib only (no pip install). Respects robots.txt for its own user agent.

Usage:
  python3 audit.py --url https://example.co.il --out seo-geo/audit-before.json
  python3 audit.py --url https://example.co.il --key-pages /,/services,/contact
  # audit a local build as if it were the live site (the "after" score for code sites):
  python3 audit.py --url https://example.co.il --fetch-base http://localhost:3999 \
      --inherit-live seo-geo/audit-before.json --out seo-geo/audit-after.json
  # compare two runs:
  python3 audit.py --compare seo-geo/audit-before.json seo-geo/audit-after.json
"""
import argparse
import concurrent.futures as cf
import gzip
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
import zlib
from html.parser import HTMLParser

VERSION = "1.0"
UA = "Mozilla/5.0 (compatible; seo-geo-audit/1.0; +https://github.com/roeit10/seo-geo-audit)"
UA_TOKEN = "seo-geo-audit"

AI_BOTS = [
    # (robots token, what it is, real UA string for the firewall test or None)
    ("OAI-SearchBot", "החיפוש של ChatGPT", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot"),
    ("ChatGPT-User", "ChatGPT כשמשתמש שולח לינק", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot"),
    ("GPTBot", "אימון המודלים של OpenAI", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.1; +https://openai.com/gptbot"),
    ("ClaudeBot", "Claude של Anthropic", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)"),
    ("PerplexityBot", "Perplexity", "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)"),
    ("Google-Extended", "Gemini (ההרשאה של גוגל ל-AI)", None),
]
SEARCH_BOTS = {"OAI-SearchBot", "ChatGPT-User", "PerplexityBot"}  # blocking these hides you from AI answers

CATEGORIES = [
    # id, Hebrew name, weight in total score, one plain line for business owners
    ("crawl", "סריקה ואינדקס", 20, "האם גוגל יכול למצוא ולהכניס לאינדקס את העמודים שלכם"),
    ("ai", "גישה למנועי AI", 10, "האם ChatGPT, Claude ו-Perplexity יכולים לקרוא את האתר"),
    ("meta", "כותרות ותיאורים בגוגל", 15, "מה רואים בתוצאת החיפוש ובשיתוף בוואטסאפ"),
    ("headings", "מבנה כותרות", 10, "האם לכל עמוד יש כותרת ראשית אחת ומבנה ברור"),
    ("images", "תמונות וטקסט חלופי", 10, "האם גוגל מבין מה יש בתמונות"),
    ("schema", "נתונים מובנים (Schema)", 10, "תעודת זהות של העסק שגוגל ו-AI קוראים"),
    ("geo", "תוכן ש-AI מצטט (GEO)", 15, "האם התוכן כתוב כך שמנוע AI יצטט אותו"),
    ("tech", "טכני: אבטחה, מובייל, מהירות", 10, "HTTPS, מובייל ומהירות תגובה"),
]
CAT_NAME = {c[0]: c[1] for c in CATEGORIES}

QUESTION_RE = re.compile(
    r"\?|^\s*(מה|איך|למה|מדוע|כמה|מתי|האם|מי|איפה|איזה|אילו|באיזה|כיצד|what|how|why|when|which|who|where|is|are|can|do|does|should)\b",
    re.I,
)
FAQ_HEAD_RE = re.compile(r"שאלות\s*(ו?תשובות|נפוצות)|FAQ|frequently asked", re.I)
UPDATED_RE = re.compile(r"(עודכן|עדכון אחרון|תאריך עדכון|last updated|updated on|updated:)", re.I)
BAD_ALT_RE = re.compile(r"^(image|img|photo|picture|תמונה|צילום)( of| של)?\b|^(תמונה של|image of|picture of)", re.I)
BAD_FILE_RE = re.compile(r"/(img|dsc|image|screenshot|screen shot|whatsapp image|photo|untitled)[-_ ]?\d*[^/]*\.(jpe?g|png|webp|gif)$", re.I)
DEFINITION_RE = re.compile(r"\b(הוא|היא|הם|הן|זה|זו)\b|\bis\b|\bare\b|\bmeans\b", re.I)
BRAND_TYPES = {"Organization", "LocalBusiness", "Corporation", "ProfessionalService", "Store", "Restaurant",
               "MedicalBusiness", "LegalService", "HomeAndConstructionBusiness", "FinancialService",
               "Dentist", "Physician", "AutomotiveBusiness", "HealthAndBeautyBusiness", "EducationalOrganization",
               "OnlineStore", "OnlineBusiness", "Person"}


# --------------------------------------------------------------------------- fetching

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_CTX = ssl.create_default_context()
_OPENER = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=_CTX))


def fetch(url, ua=UA, method="GET", timeout=15, follow=True, max_bytes=6_000_000):
    """Returns dict: status, url (final), chain [(url,status)], headers, body (str), bytes, ttfb, error."""
    chain = []
    cur = url
    t0 = time.time()
    for _ in range(6):
        req = urllib.request.Request(cur, method=method, headers={
            "User-Agent": ua, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate", "Accept-Language": "he,en;q=0.8"})
        start = time.time()
        try:
            resp = _OPENER.open(req, timeout=timeout)
            status, headers = resp.status, resp.headers
        except urllib.error.HTTPError as e:
            resp, status, headers = e, e.code, e.headers
        except Exception as e:  # DNS, TLS, timeout
            return {"status": 0, "url": cur, "chain": chain, "headers": {}, "body": "", "bytes": 0,
                    "ttfb": None, "error": f"{type(e).__name__}: {e}"[:200], "elapsed": time.time() - t0}
        ttfb = time.time() - start
        chain.append((cur, status))
        if status in (301, 302, 303, 307, 308) and follow:
            loc = headers.get("Location")
            try:
                resp.close()
            except Exception:
                pass
            if not loc:
                break
            cur = urllib.parse.urljoin(cur, loc)
            continue
        raw = b""
        if method != "HEAD":
            try:
                raw = resp.read(max_bytes)
            except Exception:
                raw = b""
        try:
            resp.close()
        except Exception:
            pass
        enc = (headers.get("Content-Encoding") or "").lower()
        try:
            if "gzip" in enc:
                raw = gzip.decompress(raw)
            elif "deflate" in enc:
                raw = zlib.decompress(raw)
        except Exception:
            pass
        ctype = headers.get("Content-Type") or ""
        m = re.search(r"charset=([\w-]+)", ctype)
        try:
            body = raw.decode(m.group(1) if m else "utf-8", errors="replace")
        except LookupError:
            body = raw.decode("utf-8", errors="replace")
        return {"status": status, "url": cur, "chain": chain, "headers": {k.lower(): v for k, v in headers.items()},
                "body": body, "bytes": len(raw), "ttfb": ttfb, "error": None, "elapsed": time.time() - t0}
    return {"status": chain[-1][1] if chain else 0, "url": cur, "chain": chain, "headers": {}, "body": "",
            "bytes": 0, "ttfb": None, "error": "too many redirects", "elapsed": time.time() - t0}


# --------------------------------------------------------------------------- html parsing

class PageParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = None
        self._in_title = False
        self.metas = []          # dicts of attrs
        self.links = []          # <link> attrs
        self.anchors = []        # hrefs
        self.nav_anchors = []    # hrefs inside nav/header
        self.imgs = []           # attrs
        self.headings = []       # (level, text)
        self.jsonld = []         # raw strings
        self.scripts_src = []
        self.css_src = []
        self.blocks = []         # ordered text blocks: ("p"|"h1".., text)
        self._skip = 0
        self._ld = None
        self._head_stack = None  # current heading [level, text]
        self._p = None
        self._nav = 0
        self.text_parts = []
        self.details = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title" and self.title is None:
            self._in_title = True
            self.title = ""
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
            if "stylesheet" in a.get("rel", "") and a.get("href"):
                self.css_src.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
            if self._nav:
                self.nav_anchors.append(a["href"])
        elif tag in ("nav", "header"):
            self._nav += 1
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "script":
            if (a.get("type") or "").lower() == "application/ld+json":
                self._ld = ""
            if a.get("src"):
                self.scripts_src.append(a["src"])
            self._skip += 1
        elif tag in self.SKIP:
            self._skip += 1
        elif re.fullmatch(r"h[1-6]", tag):
            self._head_stack = [int(tag[1]), ""]
        elif tag in ("p", "li", "dd", "summary", "blockquote", "td"):
            self._p = [tag, ""]
        elif tag == "details":
            self.details += 1
        elif tag == "br":
            if self._head_stack is not None:
                self._head_stack[1] += " "
            if self._p is not None:
                self._p[1] += " "

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
        elif tag in ("nav", "header") and self._nav:
            self._nav -= 1
        elif tag == "script":
            if self._ld is not None:
                self.jsonld.append(self._ld)
                self._ld = None
            self._skip = max(0, self._skip - 1)
        elif tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif re.fullmatch(r"h[1-6]", tag) and self._head_stack:
            lvl, txt = self._head_stack
            txt = re.sub(r"\s+", " ", txt).strip()
            self.headings.append((lvl, txt))
            self.blocks.append((f"h{lvl}", txt))
            self._head_stack = None
        elif tag in ("p", "li", "dd", "summary", "blockquote", "td") and self._p and self._p[0] == tag:
            txt = re.sub(r"\s+", " ", self._p[1]).strip()
            if txt:
                self.blocks.append(("p" if tag != "summary" else "q", txt))
            self._p = None

    def handle_data(self, data):
        if self._ld is not None:
            self._ld += data
            return
        if self._in_title:
            self.title += data
            return
        if self._skip:
            return
        if self._head_stack is not None:
            self._head_stack[1] += data
        if self._p is not None:
            self._p[1] += data
        self.text_parts.append(data)

    # helpers
    def meta(self, name=None, prop=None):
        for m in self.metas:
            if name and m.get("name", "").lower() == name:
                return m.get("content")
            if prop and m.get("property", "").lower() == prop:
                return m.get("content")
        return None

    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.text_parts)).strip()


def words(s):
    return len(re.findall(r"[\w֐-׿]+", s or ""))


def flatten_ld(obj, out):
    if isinstance(obj, list):
        for o in obj:
            flatten_ld(o, out)
    elif isinstance(obj, dict):
        if "@graph" in obj:
            flatten_ld(obj["@graph"], out)
        if "@type" in obj:
            out.append(obj)
        for k, v in obj.items():
            if k != "@graph" and isinstance(v, (dict, list)):
                flatten_ld(v, out)


def ld_types(node):
    t = node.get("@type")
    return set(t) if isinstance(t, list) else {t} if t else set()


# --------------------------------------------------------------------------- audit

class Audit:
    def __init__(self, args):
        self.args = args
        self.public = args.url.rstrip("/")
        pu = urllib.parse.urlparse(self.public)
        self.pub_host = pu.netloc.lower()
        self.pub_scheme = pu.scheme
        self.base = (args.fetch_base or self.public).rstrip("/")
        self.local = bool(args.fetch_base)
        self.checks = []
        self.pages = {}
        self.notes = []
        self.t0 = time.time()
        self.robots_txt = None
        self.rp = None

    # url mapping between public site and the server we actually fetch
    def to_fetch(self, url):
        u = urllib.parse.urlparse(url)
        host = u.netloc.lower()
        if host in (self.pub_host, "www." + self.pub_host, self.pub_host.removeprefix("www.")) or not host:
            path = u.path or "/"
            return self.base + path + (("?" + u.query) if u.query else "")
        return url

    def to_public(self, url):
        if url.startswith(self.base):
            return self.public + (url[len(self.base):] or "/")
        return url

    def norm(self, url):
        u = urllib.parse.urlparse(url)
        path = u.path or "/"
        return f"{u.scheme}://{u.netloc.lower()}{path}"

    def internal(self, url):
        host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
        return host == self.pub_host.removeprefix("www.")

    def add(self, cid, cat, weight, title, status, score, detail="", evidence=None, fix=None, source=None,
            live_only=False, value=None):
        self.checks.append({
            "id": cid, "category": cat, "weight": weight, "title": title, "status": status,
            "score": round(max(0.0, min(1.0, score)), 3), "detail": detail,
            "evidence": (evidence or [])[:15], "evidence_count": len(evidence or []),
            "fix": fix, "source": source, "live_only": live_only, "value": value,
        })

    # ------------------------------------------------------------------ robots + sitemap
    def load_robots(self):
        r = fetch(self.base + "/robots.txt")
        ok = r["status"] == 200 and "html" not in r["headers"].get("content-type", "")
        self.robots_txt = r["body"] if ok else ""
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.parse(self.robots_txt.splitlines())
        src = "ahrefs.com/blog/robots-txt/"
        if not ok:
            self.add("robots_exists", "crawl", 2, "קובץ robots.txt קיים", "fail", 0,
                     f"/robots.txt החזיר {r['status']}. בלי הקובץ אין לגוגל הפניה למפת האתר.",
                     fix="robots", source=src)
            return
        self.add("robots_exists", "crawl", 2, "קובץ robots.txt קיים", "pass", 1, "נמצא.", source=src)
        lines = [l.strip() for l in self.robots_txt.splitlines()]
        sm = [l.split(":", 1)[1].strip() for l in lines if l.lower().startswith("sitemap:")]
        self.robots_sitemaps = sm
        self.add("robots_sitemap_line", "crawl", 1, "robots.txt מפנה למפת האתר",
                 "pass" if sm else "fail", 1 if sm else 0,
                 ("שורת Sitemap: " + ", ".join(sm)) if sm else "אין שורת Sitemap: בקובץ.", fix="robots", source=src)
        bad = [l for l in lines if re.match(r"(noindex|nofollow|crawl-delay)\s*:", l, re.I)]
        big = len(self.robots_txt.encode()) > 500_000
        st = "warn" if bad or big else "pass"
        self.add("robots_valid", "crawl", 1, "robots.txt בלי הוראות שגוגל לא תומך בהן", st, 0.5 if st == "warn" else 1,
                 ("הוראות שגוגל מתעלם מהן: " + "; ".join(bad[:5])) if bad else ("הקובץ גדול מ-500KB" if big else "תקין."),
                 fix="robots", source=src)
        # blocking everything?
        blocked_home = not self.rp.can_fetch("Googlebot", self.public + "/")
        if blocked_home:
            self.add("robots_blocks_site", "crawl", 4, "robots.txt לא חוסם את האתר מגוגל", "fail", 0,
                     "Googlebot חסום מעמוד הבית. האתר לא יופיע בגוגל.", fix="robots", source=src)

    def load_sitemap(self):
        src = "ahrefs.com/blog/how-to-create-a-sitemap/"
        cands = list(getattr(self, "robots_sitemaps", [])) or [self.public + "/sitemap.xml", self.public + "/sitemap_index.xml", self.public + "/wp-sitemap.xml"]
        urls, found, err = [], None, ""
        seen_maps = set()

        def read_map(u, depth=0):
            nonlocal found, err
            if u in seen_maps or depth > 2 or len(seen_maps) > 40:
                return
            seen_maps.add(u)
            r = fetch(self.to_fetch(u))
            if r["status"] != 200:
                err = f"{u} החזיר {r['status']}"
                return
            try:
                root = ET.fromstring(r["body"].encode("utf-8", errors="ignore").strip())
            except ET.ParseError as e:
                err = f"{u}: XML לא תקין ({e})"
                return
            found = found or u
            tag = root.tag.split("}")[-1]
            locs = [el.text.strip() for el in root.iter() if el.tag.split("}")[-1] == "loc" and el.text]
            if tag == "sitemapindex":
                for child in locs:
                    read_map(child, depth + 1)
            else:
                # only <url><loc>, not image:loc
                for el in root:
                    if el.tag.split("}")[-1] == "url":
                        for c in el:
                            if c.tag.split("}")[-1] == "loc" and c.text:
                                urls.append(c.text.strip())

        for c in cands:
            read_map(c)
            if urls:
                break
        self.sitemap_urls = list(dict.fromkeys(urls))
        if not self.sitemap_urls:
            self.add("sitemap_exists", "crawl", 2, "מפת אתר (sitemap.xml) קיימת ותקינה", "fail", 0,
                     "לא נמצאה מפת אתר תקינה. " + err, fix="sitemap", source=src)
            return
        too_many = len(self.sitemap_urls) > 50_000
        self.add("sitemap_exists", "crawl", 2, "מפת אתר (sitemap.xml) קיימת ותקינה",
                 "warn" if too_many else "pass", 0.5 if too_many else 1,
                 f"{found}: {len(self.sitemap_urls)} כתובות.", value=len(self.sitemap_urls), fix="sitemap", source=src)
        foreign = [u for u in self.sitemap_urls if not self.internal(u) or not u.startswith(self.pub_scheme + "://")]
        if foreign:
            self.add("sitemap_host", "crawl", 1, "כל הכתובות במפה על הדומיין הראשי וב-HTTPS", "fail",
                     1 - len(foreign) / len(self.sitemap_urls),
                     f"{len(foreign)} כתובות על דומיין או פרוטוקול אחר.", foreign, fix="sitemap", source=src)

    def check_sitemap_urls(self):
        src = "ahrefs.com/blog/how-to-create-a-sitemap/"
        urls = self.sitemap_urls[: self.args.max_sitemap_check]
        if not urls:
            return
        bad = []

        def one(u):
            r = fetch(self.to_fetch(u), method="GET", follow=False, max_bytes=1)
            return u, r["status"]

        with cf.ThreadPoolExecutor(max_workers=self.args.workers) as ex:
            for u, st in ex.map(one, urls):
                if st != 200:
                    bad.append(f"{u} ({st})")
        sc = 1 - len(bad) / len(urls)
        self.add("sitemap_urls_ok", "crawl", 3, "כל הכתובות במפת האתר מחזירות 200 (בלי הפניות ושגיאות)",
                 "pass" if not bad else ("warn" if sc > 0.9 else "fail"), sc,
                 f"נבדקו {len(urls)} כתובות, {len(bad)} לא החזירו 200." + (
                     f" (נבדקו רק {len(urls)} מתוך {len(self.sitemap_urls)})" if len(urls) < len(self.sitemap_urls) else ""),
                 bad, fix="sitemap", source=src, value={"checked": len(urls), "bad": len(bad)})

    # ------------------------------------------------------------------ choose + crawl pages
    def choose_pages(self):
        key = []
        for p in (self.args.key_pages or "").split(","):
            p = p.strip()
            if p:
                key.append(self.public + (p if p.startswith("/") else "/" + p) if not p.startswith("http") else p)
        if self.public + "/" not in key:
            key.insert(0, self.public + "/")
        home = fetch(self.base + "/")
        self.home_fetch = home
        hp = PageParser()
        try:
            hp.feed(home["body"])
        except Exception:
            pass
        nav = []
        for h in hp.nav_anchors:
            absu = urllib.parse.urljoin(self.public + "/", h)
            if self.internal(absu) and not re.search(r"\.(pdf|jpe?g|png|zip)$|#|mailto:|tel:", absu):
                nav.append(self.norm(absu))
        if not self.args.key_pages:
            key += [u for u in dict.fromkeys(nav)][:6]
        key = list(dict.fromkeys(self.norm(u) for u in key))
        rest = [self.norm(u) for u in self.sitemap_urls if self.internal(u)]
        rest += nav
        chosen = list(dict.fromkeys(key + rest))[: self.args.max_pages]
        self.key_pages = [u for u in key if u in chosen]
        # respect robots for our own UA
        allowed = [u for u in chosen if self.rp is None or self.rp.can_fetch(UA_TOKEN, u)]
        skipped = len(chosen) - len(allowed)
        if skipped:
            self.notes.append(f"{skipped} עמודים לא נסרקו כי robots.txt חוסם אותם.")
        return allowed

    def crawl(self, urls):
        def one(u):
            r = fetch(self.to_fetch(u))
            return u, r

        with cf.ThreadPoolExecutor(max_workers=self.args.workers) as ex:
            for u, r in ex.map(one, urls):
                p = PageParser()
                try:
                    p.feed(r["body"])
                except Exception:
                    pass
                self.pages[u] = {"fetch": r, "p": p}

    # ------------------------------------------------------------------ page checks
    def page_checks(self):
        pages = {u: d for u, d in self.pages.items()}
        ok_pages = {u: d for u, d in pages.items() if d["fetch"]["status"] == 200 and
                    "html" in d["fetch"]["headers"].get("content-type", "html")}
        key = [u for u in self.key_pages if u in ok_pages]
        n = len(pages)

        # status
        bad = [f"{u} ({d['fetch']['status'] or d['fetch']['error']})" for u, d in pages.items() if d["fetch"]["status"] != 200]
        redirected = [u for u, d in pages.items() if len(d["fetch"]["chain"]) > 1 and d["fetch"]["status"] == 200]
        self.add("pages_status", "crawl", 3, "העמודים שנסרקו עונים 200", "pass" if not bad else "fail",
                 1 - len(bad) / max(n, 1), f"{n} עמודים נסרקו, {len(bad)} עם שגיאה." +
                 (f" {len(redirected)} הגיעו דרך הפניה." if redirected else ""), bad + redirected, fix="status",
                 source="ahrefs.com/blog/seo-issues/")

        # noindex
        noidx = []
        for u, d in ok_pages.items():
            mr = (d["p"].meta(name="robots") or "") + " " + (d["p"].meta(name="googlebot") or "") + " " + d["fetch"]["headers"].get("x-robots-tag", "")
            if "noindex" in mr.lower():
                d["noindex"] = True
                noidx.append(u)
        key_noidx = [u for u in noidx if u in key]
        sm_set = {self.norm(x) for x in self.sitemap_urls}
        sm_noidx = [u for u in noidx if u in sm_set]
        st = "fail" if key_noidx else ("warn" if sm_noidx else "pass")
        self.add("noindex", "crawl", 3, "אין noindex על עמודים שצריכים להופיע בגוגל", st,
                 0 if key_noidx else (1 - len(sm_noidx) / max(len(ok_pages), 1)),
                 (f"עמודים מרכזיים חסומים לאינדקס: {len(key_noidx)}. " if key_noidx else "") +
                 (f"עמודים במפת האתר עם noindex: {len(sm_noidx)}." if sm_noidx else ("" if key_noidx else "תקין.")),
                 key_noidx + sm_noidx, fix="noindex", source="ahrefs.com/blog/how-to-create-a-sitemap/")

        # canonical
        canon_bad = []
        for u, d in ok_pages.items():
            cans = [l.get("href", "") for l in d["p"].links if "canonical" in l.get("rel", "").lower().split()]
            d["canonical"] = cans[0] if cans else None
            if len(cans) != 1:
                canon_bad.append(f"{u} ({'חסר' if not cans else str(len(cans)) + ' תגיות'})")
                continue
            c = cans[0]
            if not c.startswith("https://"):
                canon_bad.append(f"{u} (לא כתובת מלאה ב-HTTPS: {c})")
            elif self.norm(c).rstrip("/") != u.rstrip("/"):
                canon_bad.append(f"{u} → {c}")
            elif d.get("noindex"):
                canon_bad.append(f"{u} (canonical + noindex יחד)")
        self.add("canonical", "meta", 2, "תגית canonical אחת, מלאה, שמצביעה על העמוד עצמו",
                 "pass" if not canon_bad else ("warn" if len(canon_bad) / max(len(ok_pages), 1) < 0.2 else "fail"),
                 1 - len(canon_bad) / max(len(ok_pages), 1), f"{len(canon_bad)} מתוך {len(ok_pages)} עמודים עם בעיה.",
                 canon_bad, fix="canonical", source="ahrefs.com/blog/canonical-tags/")

        idx_pages = {u: d for u, d in ok_pages.items() if not d.get("noindex")}
        m = max(len(idx_pages), 1)

        # titles
        brand = (self.args.brand or "").strip()
        titles = {u: (d["p"].title or "").strip() for u, d in idx_pages.items()}
        missing = [u for u, t in titles.items() if not t]
        self.add("title_present", "meta", 2, "לכל עמוד יש כותרת (title)", "pass" if not missing else "fail",
                 1 - len(missing) / m, f"{len(missing)} עמודים בלי כותרת.", missing, fix="title",
                 source="ahrefs.com/blog/title-tag-seo/")
        long_t = [f"{u} ({len(t)} תווים): {t}" for u, t in titles.items() if t and len(t) > 60]
        short_t = [f"{u} ({len(t)} תווים): {t}" for u, t in titles.items() if t and len(t) < 25]
        lt = long_t + short_t
        self.add("title_length", "meta", 1, "אורך כותרת 25-60 תווים (לא נחתכת בגוגל)",
                 "pass" if not lt else "warn", 1 - len(lt) / m,
                 f"{len(long_t)} ארוכות מ-60 תווים (גוגל חותך בערך ב-600 פיקסלים), {len(short_t)} קצרות מדי.",
                 long_t + short_t, fix="title", source="ahrefs.com/blog/title-tag-seo/",
                 value={"long": len(long_t), "short": len(short_t)})
        dup = {}
        for u, t in titles.items():
            if t:
                dup.setdefault(t, []).append(u)
        dups = [f"\"{t}\": {', '.join(us[:3])}" for t, us in dup.items() if len(us) > 1]
        self.add("title_unique", "meta", 1, "כל כותרת ייחודית", "pass" if not dups else "fail",
                 1 - sum(len(v) for v in dup.values() if len(v) > 1) / m, f"{len(dups)} כותרות כפולות.", dups,
                 fix="title", source="ahrefs.com/blog/title-tag-seo/")
        if brand:
            nob = [u for u, t in titles.items() if t and brand.lower() not in t.lower()]
            self.add("title_brand", "meta", 0.5, f"שם המותג ({brand}) מופיע בכותרת", "pass" if not nob else "warn",
                     1 - len(nob) / m, f"{len(nob)} כותרות בלי שם המותג.", nob, fix="title",
                     source="ahrefs.com/blog/title-tag-seo/")

        # descriptions
        descs = {u: (d["p"].meta(name="description") or "").strip() for u, d in idx_pages.items()}
        dmiss = [u for u, t in descs.items() if not t]
        self.add("desc_present", "meta", 2, "לכל עמוד יש תיאור (meta description)", "pass" if not dmiss else "fail",
                 1 - len(dmiss) / m, f"{len(dmiss)} עמודים בלי תיאור. גוגל ימציא טקסט מהעמוד.", dmiss,
                 fix="description", source="ahrefs.com/blog/meta-description/")
        dl = [f"{u} ({len(t)} תווים)" for u, t in descs.items() if t and (len(t) > 160 or len(t) < 70)]
        self.add("desc_length", "meta", 1, "אורך תיאור 70-160 תווים", "pass" if not dl else "warn", 1 - len(dl) / m,
                 f"{len(dl)} תיאורים ארוכים או קצרים מדי (במובייל נחתך אחרי ~120).", dl, fix="description",
                 source="ahrefs.com/blog/meta-description/")
        dd = {}
        for u, t in descs.items():
            if t:
                dd.setdefault(t, []).append(u)
        ddup = [f"{', '.join(us[:3])}" for t, us in dd.items() if len(us) > 1]
        self.add("desc_unique", "meta", 1, "כל תיאור ייחודי", "pass" if not ddup else "fail",
                 1 - sum(len(v) for v in dd.values() if len(v) > 1) / m, f"{len(ddup)} תיאורים כפולים.", ddup,
                 fix="description", source="ahrefs.com/blog/meta-description/")

        # open graph
        og_req = ["og:title", "og:type", "og:image", "og:url"]
        og_bad = []
        for u, d in idx_pages.items():
            miss = [k for k in og_req + ["og:description"] if not d["p"].meta(prop=k)]
            if miss:
                og_bad.append(f"{u} (חסר: {', '.join(miss)})")
        self.add("open_graph", "meta", 1.5, "תגיות Open Graph (תצוגה בשיתוף בוואטסאפ/פייסבוק)",
                 "pass" if not og_bad else "warn", 1 - len(og_bad) / m, f"{len(og_bad)} עמודים חסרים תגיות.", og_bad,
                 fix="open_graph", source="ahrefs.com/blog/open-graph-meta-tags/")
        home = self.pages.get(self.public + "/") or self.pages.get(self.norm(self.public + "/"))
        if home and home["p"].meta(prop="og:image"):
            img = urllib.parse.urljoin(self.public + "/", home["p"].meta(prop="og:image"))
            r = fetch(self.to_fetch(img), max_bytes=64)
            okimg = r["status"] == 200 and r["headers"].get("content-type", "").startswith("image")
            self.add("og_image_ok", "meta", 0.5, "תמונת השיתוף של עמוד הבית נטענת", "pass" if okimg else "fail",
                     1 if okimg else 0, f"{img} → {r['status']}", fix="open_graph",
                     source="ahrefs.com/blog/open-graph-meta-tags/")

        # lang
        if home:
            lang = home["p"].lang
            self.add("lang_attr", "tech", 0.5, "שפת העמוד מוגדרת (<html lang>)", "pass" if lang else "warn",
                     1 if lang else 0, f"lang=\"{lang}\"" if lang else "אין מאפיין lang.", fix="lang")

        # headings
        h1bad, h1long, order_bad, h2none = [], [], [], []
        for u, d in idx_pages.items():
            hs = d["p"].headings
            h1s = [t for l, t in hs if l == 1]
            if len(h1s) != 1:
                h1bad.append(f"{u} ({len(h1s)} H1)")
            elif len(h1s[0]) > 70:
                h1long.append(f"{u} ({len(h1s[0])} תווים)")
            prev = 0
            for l, t in hs:
                if prev and l > prev + 1:
                    order_bad.append(f"{u}: H{prev} → H{l} (\"{t[:40]}\")")
                    break
                prev = l
            if u in key and u.rstrip("/") != self.public and len([1 for l, _ in hs if l == 2]) < 2:
                h2none.append(u)
        self.add("h1_single", "headings", 3, "כותרת H1 אחת בדיוק בכל עמוד", "pass" if not h1bad else "fail",
                 1 - len(h1bad) / m, f"{len(h1bad)} עמודים בלי H1 או עם יותר מאחת.", h1bad, fix="headings",
                 source="ahrefs.com/blog/h1-tag/")
        self.add("h1_length", "headings", 1, "H1 עד 70 תווים", "pass" if not h1long else "warn", 1 - len(h1long) / m,
                 f"{len(h1long)} ארוכות מדי.", h1long, fix="headings", source="ahrefs.com/blog/h1-tag/")
        self.add("heading_order", "headings", 1.5, "כותרות לפי הסדר (בלי לדלג מ-H2 ל-H4)",
                 "pass" if not order_bad else "warn", 1 - len(order_bad) / m, f"{len(order_bad)} עמודים מדלגים רמה.",
                 order_bad, fix="headings", source="ahrefs.com/blog/h1-tag/")
        if key:
            self.add("h2_structure", "headings", 1, "בעמודים המרכזיים יש לפחות 2 כותרות משנה (H2)",
                     "pass" if not h2none else "warn", 1 - len(h2none) / max(len(key), 1), f"{len(h2none)} עמודים.",
                     h2none, fix="headings", source="ahrefs.com/blog/h1-tag/")

        # images
        total, with_alt, empty_alt, bad_alt, bad_file = 0, 0, 0, [], []
        miss_alt = []
        for u, d in idx_pages.items():
            for im in d["p"].imgs:
                srcv = im.get("src") or im.get("data-src") or ""
                if srcv.startswith("data:") and not im.get("alt"):
                    pass
                total += 1
                if "alt" not in im:
                    miss_alt.append(f"{u}: {srcv[:90]}")
                else:
                    with_alt += 1
                    a = im.get("alt", "").strip()
                    if not a:
                        empty_alt += 1
                    elif BAD_ALT_RE.search(a) or re.search(r"\.(jpe?g|png|webp)$", a, re.I):
                        bad_alt.append(f"{u}: alt=\"{a[:60]}\"")
                path = urllib.parse.urlparse(urllib.parse.unquote(srcv)).path
                if BAD_FILE_RE.search(path) or re.search(r"[?&]url=.*(IMG|DSC)[-_]\d", srcv, re.I):
                    bad_file.append(f"{u}: {srcv[:90]}")
        if total:
            self.add("alt_missing", "images", 3, "לכל תמונה יש מאפיין alt", "pass" if not miss_alt else "fail",
                     with_alt / total, f"{total} תמונות בעמודים שנסרקו, {len(miss_alt)} בלי alt בכלל"
                     f" ({empty_alt} עם alt ריק, שזה תקין לתמונה דקורטיבית).", miss_alt, fix="alt",
                     source="ahrefs.com/blog/alt-text/", value={"total": total, "missing": len(miss_alt), "empty": empty_alt})
            self.add("alt_quality", "images", 1, "טקסט ה-alt מתאר (בלי \"תמונה של\" או שם קובץ)",
                     "pass" if not bad_alt else "warn", 1 - len(bad_alt) / max(with_alt, 1), f"{len(bad_alt)} תיאורים חלשים.",
                     bad_alt, fix="alt", source="ahrefs.com/blog/alt-text/")
            self.add("img_filenames", "images", 0.5, "שמות קבצי תמונה תיאוריים (לא IMG_1234)",
                     "pass" if not bad_file else "warn", 1 - len(bad_file) / total, f"{len(bad_file)} קבצים.", bad_file,
                     fix="alt", source="ahrefs.com/blog/image-seo/")
        else:
            self.add("alt_missing", "images", 3, "לכל תמונה יש מאפיין alt", "na", 1, "לא נמצאו תמגיות <img> ב-HTML.",
                     fix="alt", source="ahrefs.com/blog/alt-text/")

        # schema
        ld_bad, page_types = [], {}
        for u, d in idx_pages.items():
            nodes = []
            for raw in d["p"].jsonld:
                try:
                    flatten_ld(json.loads(raw), nodes)
                except Exception as e:
                    ld_bad.append(f"{u}: {str(e)[:80]}")
            d["ld_nodes"] = nodes
            page_types[u] = sorted({t for n in nodes for t in ld_types(n) if t})
        any_ld = any(page_types.values()) or ld_bad
        self.add("jsonld_valid", "schema", 2, "קוד ה-Schema (JSON-LD) תקין", "pass" if not ld_bad else "fail",
                 1 - len(ld_bad) / m if any_ld else 0, (f"{len(ld_bad)} בלוקים לא נקראים." if ld_bad else
                                                        ("כל הבלוקים נקראים." if any_ld else "אין JSON-LD באתר.")),
                 ld_bad, fix="schema", source="ahrefs.com/blog/schema-markup/")
        org = None
        if home:
            for nd in home.get("ld_nodes", []):
                if ld_types(nd) & BRAND_TYPES:
                    org = nd
                    break
        if org:
            t = ", ".join(sorted(ld_types(org)))
            gaps = [k for k in ("name", "url") if not org.get(k)]
            has_same = bool(org.get("sameAs"))
            local_fields = [k for k in ("address", "telephone") if org.get(k)]
            sc = 1.0 - 0.3 * len(gaps) - (0 if has_same else 0.25)
            detail = f"נמצא {t}: \"{org.get('name', '')}\"." + ("" if has_same else " אין sameAs (קישורים לרשתות).") + \
                     (f" חסר: {', '.join(gaps)}." if gaps else "")
            if "Person" in ld_types(org) and not (ld_types(org) - {"Person"}):
                detail += " העסק מוצג כאדם (Person). לעסק עם שירותים אפשר להוסיף גם ProfessionalService/LocalBusiness עם אזור שירות."
            self.add("org_schema", "schema", 3, "תעודת הזהות של העסק (Organization / LocalBusiness) בעמוד הבית",
                     "pass" if sc >= 0.99 else "warn", sc, detail, fix="schema", source="ahrefs.com/blog/schema-markup/",
                     value={"types": sorted(ld_types(org)), "sameAs": has_same, "local_fields": local_fields})
        else:
            self.add("org_schema", "schema", 3, "תעודת הזהות של העסק (Organization / LocalBusiness) בעמוד הבית", "fail", 0,
                     "אין Schema שמזהה את העסק בעמוד הבית: שם, כתובת, טלפון, רשתות.", fix="schema",
                     source="ahrefs.com/seo/glossary/local-business-schema")
        site_types = {t for ts in page_types.values() for t in ts}
        self.add("website_schema", "schema", 1, "Schema מסוג WebSite", "pass" if "WebSite" in site_types else "warn",
                 1 if "WebSite" in site_types else 0, "נמצא." if "WebSite" in site_types else "חסר.", fix="schema",
                 source="ahrefs.com/blog/schema-markup/")
        inner = [u for u in idx_pages if u.rstrip("/") != self.public]
        no_page_ld = [u for u in inner if not (set(page_types.get(u, [])) - {"WebSite", "Person", "Organization"})]
        if inner:
            self.add("page_schema", "schema", 1, "לעמודים הפנימיים יש Schema משלהם (Service / Article / Breadcrumb)",
                     "pass" if not no_page_ld else "warn", 1 - len(no_page_ld) / len(inner),
                     f"{len(no_page_ld)} מתוך {len(inner)} עמודים בלי Schema ייעודי.", no_page_ld, fix="schema",
                     source="ahrefs.com/blog/schema-markup/")

        # GEO (key pages)
        geo_pages = [u for u in key if u in idx_pages] or list(idx_pages)[:5]
        g = max(len(geo_pages), 1)
        no_answer, no_q, no_faq, no_upd, thin = [], [], [], [], []
        for u in geo_pages:
            d = idx_pages[u]
            blocks = d["p"].blocks
            # answer-first: a paragraph of 15+ words before the first H2
            first_h2 = next((i for i, (k, _) in enumerate(blocks) if k == "h2"), len(blocks))
            intro = [t for k, t in blocks[:first_h2] if k == "p" and words(t) >= 15]
            if not intro:
                no_answer.append(u)
            qs = [t for l, t in d["p"].headings if l in (2, 3) and QUESTION_RE.search(t)]
            if not qs:
                no_q.append(u)
            has_faq = any(FAQ_HEAD_RE.search(t) for _, t in d["p"].headings) or d["p"].details >= 2 or \
                "FAQPage" in page_types.get(u, [])
            if not has_faq:
                no_faq.append(u)
            txt = d["p"].text()
            mod = any(n.get("dateModified") for n in d.get("ld_nodes", []))
            if not UPDATED_RE.search(txt) and not mod:
                no_upd.append(u)
            if words(txt) < 150:
                thin.append(f"{u} ({words(txt)} מילים ב-HTML)")
        self.add("answer_first", "geo", 3, "פסקת תשובה ישירה בראש העמוד, לפני כותרת המשנה הראשונה",
                 "pass" if not no_answer else "warn", 1 - len(no_answer) / g,
                 f"{len(no_answer)} מתוך {len(geo_pages)} עמודים מרכזיים פותחים בלי פסקה שעונה מה העסק עושה. "
                 "44% מהציטוטים ב-ChatGPT מגיעים מ-30% הראשונים של העמוד.", no_answer, fix="geo",
                 source="ahrefs.com/blog/how-to-rank-on-chatgpt/")
        self.add("question_headings", "geo", 2, "כותרות משנה בניסוח של שאלה", "pass" if not no_q else "warn",
                 1 - len(no_q) / g, f"{len(no_q)} עמודים מרכזיים בלי אף כותרת-שאלה. כותרות-שאלה מצוטטות פי 2.",
                 no_q, fix="geo", source="ahrefs.com/blog/h1-tag/")
        self.add("faq_block", "geo", 2, "בלוק שאלות נפוצות גלוי בעמודים המרכזיים", "pass" if not no_faq else "warn",
                 1 - len(no_faq) / g, f"{len(no_faq)} עמודים מרכזיים בלי שאלות ותשובות.", no_faq, fix="geo",
                 source="ahrefs.com/blog/how-to-rank-on-chatgpt/")
        self.add("freshness", "geo", 1.5, "\"עודכן לאחרונה\" גלוי או dateModified", "pass" if not no_upd else "warn",
                 1 - len(no_upd) / g, f"{len(no_upd)} עמודים מרכזיים בלי תאריך עדכון.", no_upd, fix="geo",
                 source="ahrefs.com/blog/fresh-content/")
        self.add("server_rendered", "ai", 3, "התוכן קיים ב-HTML עצמו (מנועי AI לא מריצים JavaScript)",
                 "pass" if not thin else "fail", 1 - len(thin) / g,
                 f"{len(thin)} עמודים מרכזיים עם פחות מ-150 מילים ב-HTML הגולמי. אם התוכן נטען רק ב-JavaScript, ChatGPT לא רואה אותו.",
                 thin, fix="js_content", source="ahrefs.com/blog/javascript-seo/")

        # tech
        mixed, big, nov = [], [], []
        for u, d in idx_pages.items():
            b = d["fetch"]["body"]
            if not self.local and re.search(r"<(img|script|iframe|link)[^>]+(src|href)=[\"']http://", b, re.I):
                mixed.append(u)
            if d["fetch"]["bytes"] > 2_000_000:
                big.append(f"{u} ({d['fetch']['bytes'] // 1024}KB)")
            if not d["p"].meta(name="viewport"):
                nov.append(u)
        self.add("viewport", "tech", 1, "מותאם למובייל (meta viewport)", "pass" if not nov else "fail",
                 1 - len(nov) / m, f"{len(nov)} עמודים בלי viewport.", nov, fix="tech", source="ahrefs.com/blog/seo-issues/")
        self.add("html_size", "tech", 1, "גודל HTML מתחת ל-2MB", "pass" if not big else "warn", 1 - len(big) / m,
                 f"{len(big)} עמודים כבדים.", big, fix="tech", source="ahrefs.com/blog/seo-issues/")
        if not self.local:
            self.add("mixed_content", "tech", 1, "בלי תוכן לא מאובטח (http://) בתוך עמוד HTTPS",
                     "pass" if not mixed else "fail", 1 - len(mixed) / m, f"{len(mixed)} עמודים.", mixed, fix="tech",
                     source="ahrefs.com/blog/seo-issues/", live_only=True)
            tt = sorted(d["fetch"]["ttfb"] for d in idx_pages.values() if d["fetch"]["ttfb"])
            if tt:
                med = tt[len(tt) // 2] * 1000
                st = "pass" if med < 600 else ("warn" if med < 1200 else "fail")
                self.add("ttfb", "tech", 1.5, "זמן תגובה ראשונה של השרת (TTFB)", st,
                         1 if st == "pass" else (0.5 if st == "warn" else 0),
                         f"חציון {med:.0f}ms (נמדד מהמחשב שהריץ, כולל חיבור). יעד מומלץ למנועי AI: מתחת ל-200ms בשרת.",
                         fix="tech", source="ahrefs.com/blog/how-to-rank-on-chatgpt/", live_only=True, value=round(med))

        # internal-link discovery of sitemap pages (light orphan check over crawled pages)
        linked = set()
        for u, d in idx_pages.items():
            for h in d["p"].anchors:
                absu = urllib.parse.urljoin(u, h)
                if self.internal(absu):
                    linked.add(self.norm(absu).rstrip("/"))
        orphans = [u for u in idx_pages if u.rstrip("/") not in linked and u.rstrip("/") != self.public]
        self.add("internal_links", "crawl", 1, "כל עמוד מקבל לפחות קישור פנימי אחד (מתוך העמודים שנסרקו)",
                 "pass" if not orphans else "warn", 1 - len(orphans) / m,
                 f"{len(orphans)} עמודים שאף עמוד שנסרק לא מקשר אליהם (בדיקה חלקית, רק על {len(idx_pages)} עמודים).",
                 orphans, fix="links", source="ahrefs.com/blog/seo-issues/")

        self.idx_pages = idx_pages
        self.page_types = page_types

    # ------------------------------------------------------------------ site-level live checks
    def live_checks(self):
        if self.local:
            return
        src = "ahrefs.com/blog/seo-issues/"
        https = self.public.startswith("https://")
        self.add("https", "tech", 2, "האתר ב-HTTPS", "pass" if https else "fail", 1 if https else 0,
                 self.public, fix="tech", source=src, live_only=True)
        host = self.pub_host.removeprefix("www.")
        variants = [f"http://{host}/", f"http://www.{host}/", f"https://www.{host}/", f"https://{host}/"]
        bad = []
        for v in variants:
            if self.norm(v) == self.norm(self.public + "/"):
                continue
            r = fetch(v, follow=True, max_bytes=1)
            first = r["chain"][0][1] if r["chain"] else r["status"]
            final = self.norm(r["url"])
            if r["status"] == 0:
                continue  # variant does not exist (no DNS) - fine
            if final.rstrip("/") != self.public or first not in (301, 308):
                bad.append(f"{v} → {r['url']} ({first})")
        self.add("host_consistency", "crawl", 1, "כל הגרסאות (http / www) מפנות בהפניה קבועה לכתובת אחת",
                 "pass" if not bad else "warn", 1 - len(bad) / 3, f"{len(bad)} גרסאות לא מפנות כמו שצריך.", bad,
                 fix="tech", source=src, live_only=True)
        rnd = fetch(self.public + "/this-page-should-not-exist-seo-geo-audit-404", max_bytes=1000)
        ok404 = rnd["status"] in (404, 410)
        self.add("soft_404", "crawl", 1, "עמוד שלא קיים מחזיר 404 אמיתי", "pass" if ok404 else "warn",
                 1 if ok404 else 0, f"כתובת אקראית החזירה {rnd['status']}.", fix="status", source=src, live_only=True)

        # AI bots through the firewall (real user agents)
        blocked = []
        base_status = self.home_fetch["status"] if getattr(self, "home_fetch", None) else 200
        for tok, name, ua in AI_BOTS:
            if not ua:
                continue
            r = fetch(self.public + "/", ua=ua, max_bytes=20000)
            body = r["body"][:20000].lower()
            challenged = r["status"] in (401, 403, 429, 503) or ("cf-chl" in body or "just a moment" in body)
            if challenged and base_status == 200:
                blocked.append(f"{tok} ({name}): {r['status']}")
        self.add("ai_firewall", "ai", 2, "חומת האש לא חוסמת בוטים של AI (בדיקה עם ה-User-Agent האמיתי)",
                 "pass" if not blocked else "fail", 1 - len(blocked) / 5,
                 ("נחסמו: " + "; ".join(blocked)) if blocked else "כל הבוטים קיבלו את העמוד.", blocked,
                 fix="ai_bots", source="ahrefs.com/aeo/technical-aeo", live_only=True)

    def robots_ai(self):
        if self.rp is None:
            return
        key = self.key_pages or [self.public + "/"]
        rows, blocked_search, blocked_train = [], [], []
        for tok, name, _ in AI_BOTS:
            can = all(self.rp.can_fetch(tok, u) for u in key)
            explicit = bool(re.search(r"user-agent:\s*" + re.escape(tok) + r"\b", self.robots_txt or "", re.I))
            rows.append({"bot": tok, "what": name, "allowed": can, "explicit": explicit})
            if not can:
                (blocked_search if tok in SEARCH_BOTS else blocked_train).append(f"{tok} ({name})")
        st = "fail" if blocked_search else ("warn" if blocked_train else "pass")
        sc = 1 - 0.3 * len(blocked_search) - 0.1 * len(blocked_train)
        detail = ("חסומים בוטים של חיפוש AI: " + ", ".join(blocked_search) + ". " if blocked_search else "") + \
                 ("חסומים בוטים של אימון (בחירה של בעל האתר): " + ", ".join(blocked_train) + "." if blocked_train else "")
        if not detail:
            detail = "כל בוטי ה-AI מורשים ב-robots.txt" + (" (דרך הכלל הכללי *, בלי אזכור מפורש)." if not any(r["explicit"] for r in rows) else ".")
        self.add("ai_robots", "ai", 3, "robots.txt מאפשר ל-ChatGPT, Claude ו-Perplexity לקרוא את האתר", st, sc,
                 detail, blocked_search + blocked_train, fix="ai_bots", source="ahrefs.com/aeo/technical-aeo", value=rows)
        # llms.txt - informational only
        r = fetch(self.base + "/llms.txt", max_bytes=2000)
        has = r["status"] == 200 and "html" not in r["headers"].get("content-type", "")
        self.add("llms_txt", "ai", 0, "llms.txt (מידע בלבד, לא משפיע על הציון)", "info", 1,
                 ("קיים. " if has else "לא קיים. ") + "לפי Ahrefs, 97% מקבצי llms.txt לא מקבלים אף בקשה. לא צריך להשקיע בזה.",
                 fix=None, source="ahrefs.com/blog/llms-txt/")

    # ------------------------------------------------------------------ inherit + score
    def inherit(self, path):
        try:
            prev = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            self.notes.append(f"לא הצלחתי לקרוא את {path}: {e}")
            return
        have = {c["id"] for c in self.checks}
        n = 0
        for c in prev.get("checks", []):
            if c.get("live_only") and c["id"] not in have:
                c = dict(c)
                c["detail"] = (c.get("detail") or "") + " (נמדד באתר החי, לא משתנה בבנייה מקומית)"
                c["inherited"] = True
                self.checks.append(c)
                n += 1
        self.notes.append(f"{n} בדיקות שאפשר למדוד רק באתר החי (HTTPS, הפניות, חומת אש, מהירות) נלקחו מהריצה הקודמת.")

    def score(self):
        cats = {}
        for cid, name, w, plain in CATEGORIES:
            cs = [c for c in self.checks if c["category"] == cid and c["status"] not in ("na", "info") and c["weight"] > 0]
            tw = sum(c["weight"] for c in cs)
            s = sum(c["weight"] * c["score"] for c in cs) / tw if tw else None
            cats[cid] = {"name": name, "weight": w, "plain": plain,
                         "score": round(s * 100) if s is not None else None,
                         "fails": sum(1 for c in cs if c["status"] == "fail"),
                         "warns": sum(1 for c in cs if c["status"] == "warn")}
        valid = [(v["weight"], v["score"]) for v in cats.values() if v["score"] is not None]
        total = round(sum(w * s for w, s in valid) / sum(w for w, _ in valid)) if valid else 0
        return total, cats

    def run(self):
        t = time.time()
        self.load_robots()
        self.load_sitemap()
        t_sm = time.time()
        urls = self.choose_pages()
        self.crawl(urls)
        t_crawl = time.time()
        self.check_sitemap_urls()
        self.page_checks()
        self.robots_ai()
        self.live_checks()
        if self.args.inherit_live:
            self.inherit(self.args.inherit_live)
        total, cats = self.score()
        sev = {"fail": 0, "warn": 1, "pass": 2, "info": 3, "na": 4}
        self.checks.sort(key=lambda c: (sev.get(c["status"], 5), -c["weight"] * (1 - c["score"])))
        pages_out = []
        for u, d in self.pages.items():
            p = d["p"]
            pages_out.append({
                "url": u, "status": d["fetch"]["status"], "key": u in self.key_pages,
                "title": (p.title or "").strip(), "description": p.meta(name="description"),
                "canonical": d.get("canonical"), "noindex": bool(d.get("noindex")),
                "h1": [t for l, t in p.headings if l == 1], "h2": [t for l, t in p.headings if l == 2][:20],
                "words": words(p.text()), "images": len(p.imgs),
                "images_no_alt": sum(1 for i in p.imgs if "alt" not in i),
                "schema_types": self.page_types.get(u, []) if hasattr(self, "page_types") else [],
                "ttfb_ms": round(d["fetch"]["ttfb"] * 1000) if d["fetch"]["ttfb"] else None,
            })
        return {
            "tool": "seo-geo-audit", "version": VERSION,
            "site": self.public, "fetched_from": self.base, "mode": "local-build" if self.local else "live",
            "date": time.strftime("%Y-%m-%d %H:%M"),
            "score": total, "categories": cats,
            "summary": {"pages_crawled": len(self.pages), "key_pages": self.key_pages,
                        "sitemap_urls": len(getattr(self, "sitemap_urls", [])),
                        "fails": sum(1 for c in self.checks if c["status"] == "fail"),
                        "warns": sum(1 for c in self.checks if c["status"] == "warn"),
                        "passes": sum(1 for c in self.checks if c["status"] == "pass")},
            "timings_sec": {"robots_sitemap": round(t_sm - t, 1), "crawl": round(t_crawl - t_sm, 1),
                            "total": round(time.time() - self.t0, 1)},
            "notes": self.notes,
            "validation_links": {
                "rich_results": "https://search.google.com/test/rich-results?url=" + urllib.parse.quote(self.public + "/", safe=""),
                "schema_validator": "https://validator.schema.org/#url=" + urllib.parse.quote(self.public + "/", safe=""),
                "pagespeed": "https://pagespeed.web.dev/analysis?url=" + urllib.parse.quote(self.public + "/", safe=""),
                "search_console": "https://search.google.com/search-console",
                "business_profile": "https://www.google.com/business/",
            },
            "checks": self.checks, "pages": pages_out,
        }


# --------------------------------------------------------------------------- compare

def compare(a_path, b_path):
    a = json.load(open(a_path, encoding="utf-8"))
    b = json.load(open(b_path, encoding="utf-8"))
    out = {"before": a["score"], "after": b["score"], "categories": {}, "fixed": [], "still_open": [], "new": []}
    for cid, v in a["categories"].items():
        out["categories"][cid] = {"name": v["name"], "before": v["score"], "after": b["categories"].get(cid, {}).get("score")}
    bc = {c["id"]: c for c in b["checks"]}
    ac = {c["id"]: c for c in a["checks"]}
    for cid, c in ac.items():
        if c["status"] in ("fail", "warn"):
            nb = bc.get(cid)
            if nb and nb["status"] == "pass":
                out["fixed"].append({"id": cid, "title": c["title"], "before": c["detail"], "after": nb["detail"]})
            else:
                out["still_open"].append({"id": cid, "title": c["title"], "status": nb["status"] if nb else "?",
                                          "detail": nb["detail"] if nb else c["detail"],
                                          "improved": bool(nb and nb["score"] > c["score"])})
    for cid, c in bc.items():
        if c["status"] in ("fail", "warn") and (cid not in ac or ac[cid]["status"] == "pass"):
            out["new"].append({"id": cid, "title": c["title"], "detail": c["detail"]})
    return out


def main():
    ap = argparse.ArgumentParser(description="seo-geo-audit deterministic checker")
    ap.add_argument("--url", help="public site URL, e.g. https://example.co.il")
    ap.add_argument("--key-pages", default="", help="comma list of paths: /,/services,/contact")
    ap.add_argument("--brand", default="", help="brand name expected in titles")
    ap.add_argument("--max-pages", type=int, default=30)
    ap.add_argument("--max-sitemap-check", type=int, default=300)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--fetch-base", default="", help="fetch from here instead (local build), keep --url as the public site")
    ap.add_argument("--inherit-live", default="", help="copy live-only checks from a previous JSON (for local builds)")
    ap.add_argument("--out", default="")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    a = ap.parse_args()
    if a.compare:
        res = compare(*a.compare)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not a.url:
        ap.error("--url is required")
    if not a.url.startswith("http"):
        a.url = "https://" + a.url
    res = Audit(a).run()
    js = json.dumps(res, ensure_ascii=False, indent=2)
    if a.out:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(js)
    # short human summary on stdout (Claude reads the JSON file for details)
    print(f"SCORE {res['score']}/100  ({res['mode']}, {res['summary']['pages_crawled']} pages, "
          f"{res['timings_sec']['total']}s)")
    for cid, v in res["categories"].items():
        print(f"  {v['name']}: {v['score'] if v['score'] is not None else '-'}  (fail {v['fails']}, warn {v['warns']})")
    print(f"fails {res['summary']['fails']} · warns {res['summary']['warns']} · passes {res['summary']['passes']}")
    for c in res["checks"]:
        if c["status"] in ("fail", "warn"):
            print(f"  [{c['status']}] {c['id']}: {c['title']} - {c['detail'][:140]}")
    if a.out:
        print("json:", a.out)


if __name__ == "__main__":
    main()
