#!/usr/bin/env python3
"""
seo-geo-audit: WordPress REST helper. Backup first, then write. Stdlib only.

Credentials are read from .env in the project folder (never from the chat, never printed):
  WP_SITE=https://example.co.il
  WP_USER=your-wp-username
  WP_APP_PASSWORD=xxxx xxxx xxxx xxxx xxxx xxxx

Commands (all print JSON):
  check                         who am I, roles, REST ok, SEO plugin, can I write meta
  find <url>                    page/post id + type for a public URL
  backup <type:id> [...]        save title, content (raw), excerpt, meta, SEO fields -> seo-geo/backup/
  seo <type:id> [--title T] [--desc D]   set SEO title / meta description (Yoast or Rank Math)
  alt-missing                   media items with an empty alt text (first 100)
  alt <media_id> "<alt text>"   set alt text of one media item
  content-get <type:id> <file>  write raw content to a file (for a reviewed edit)
  content-put <type:id> <file>  replace raw content from a file (only after backup + "מאשר")
  restore <backup.json>         put back everything from a backup file
type = pages | posts
"""
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_FILE = os.environ.get("SEO_GEO_ENV", ".env")


def load_env():
    env = {}
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE, encoding="utf-8"):
            m = re.match(r"\s*([A-Z_]+)\s*=\s*(.*)\s*$", line)
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    for k in ("WP_SITE", "WP_USER", "WP_APP_PASSWORD"):
        env[k] = os.environ.get(k, env.get(k, ""))
    miss = [k for k in ("WP_SITE", "WP_USER", "WP_APP_PASSWORD") if not env[k] or "PASTE" in env[k]]
    if miss:
        out({"ok": False, "error": f"חסר ב-{ENV_FILE}: {', '.join(miss)}"})
        sys.exit(2)
    env["WP_SITE"] = env["WP_SITE"].rstrip("/")
    env["WP_APP_PASSWORD"] = env["WP_APP_PASSWORD"].replace(" ", "")
    return env


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def api(env, method, path, body=None, auth=True):
    url = env["WP_SITE"] + "/wp-json" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("User-Agent", "seo-geo-audit/1.0")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if auth:
        tok = base64.b64encode(f'{env["WP_USER"]}:{env["WP_APP_PASSWORD"]}'.encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", "replace")
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:500]
    except Exception as e:
        return 0, str(e)


def seo_plugin(env):
    st, idx = api(env, "GET", "/", auth=False)
    ns = idx.get("namespaces", []) if isinstance(idx, dict) else []
    if any(n.startswith("rankmath") for n in ns):
        return "rankmath", ns
    if any(n.startswith("yoast") for n in ns):
        return "yoast", ns
    return None, ns


def parse_ref(ref):
    t, i = ref.split(":")
    assert t in ("pages", "posts"), "type must be pages or posts"
    return t, int(i)


def cmd_check(env):
    st, me = api(env, "GET", "/wp/v2/users/me?context=edit")
    plugin, ns = seo_plugin(env)
    res = {"ok": st == 200, "status": st, "site": env["WP_SITE"], "seo_plugin": plugin}
    if st == 200:
        res.update({"user": me.get("name"), "roles": me.get("roles"),
                    "can_edit_pages": "edit_pages" in (me.get("capabilities") or {}) or "administrator" in (me.get("roles") or [])})
        # can the SEO fields be written through REST? Yoast: post meta must be registered (shows in schema)
        if plugin == "yoast":
            # Yoast registers its meta for REST only from 27.7 and only for the "post" type.
            # Pages need a helper plugin / register_post_meta. Check what this site really exposes.
            w = {}
            for t in ("pages", "posts"):
                s2, opt = api(env, "OPTIONS", f"/wp/v2/{t}")
                w[t] = s2 == 200 and "_yoast_wpseo_metadesc" in json.dumps(opt)[:400000]
            res["yoast_meta_writable"] = w
            if not w["pages"]:
                res["hint"] = ("Yoast לא חושף את הכותרת והתיאור של עמודים (pages) לכתיבה דרך ה-API. "
                               "ראו connect-wordpress.md, צעד 5, שורת 'Yoast, עמודים'.")
        elif plugin == "rankmath":
            res["hint"] = "Rank Math: כותבים דרך rankmath/v1/updateMeta (לא מתועד רשמית). שגיאה → צעדים בעורך."
        else:
            res["hint"] = "אין תוסף SEO. כותרת ותיאור צריכים Yoast או Rank Math (ראו connect-wordpress.md)."
    else:
        code = me.get("code") if isinstance(me, dict) else ""
        res["error"] = code or str(me)[:200]
        if code == "rest_not_logged_in":
            res["hint"] = "השרת כנראה מוחק את כותרת ה-Authorization (נפוץ ב-LiteSpeed/Apache). ראו connect-wordpress.md, 'תקלות'."
        elif code in ("incorrect_password", "invalid_username"):
            res["hint"] = "שם המשתמש או סיסמת האפליקציה לא נכונים. שם המשתמש הוא שם הכניסה לוורדפרס, לא האימייל (אלא אם נכנסים עם אימייל)."
    out(res)


def cmd_find(env, url):
    path = urllib.parse.urlparse(url).path.strip("/")
    slug = path.split("/")[-1] if path else ""
    if not slug:
        st, front = api(env, "GET", "/wp/v2/settings")  # needs manage_options
        pid = front.get("page_on_front") if isinstance(front, dict) else None
        out({"url": url, "type": "pages", "id": pid, "note": "עמוד הבית (page_on_front)" if pid else "עמוד הבית הוא רשימת פוסטים או שאין הרשאה לקרוא הגדרות"})
        return
    for t in ("pages", "posts"):
        st, items = api(env, "GET", f"/wp/v2/{t}?slug={urllib.parse.quote(slug)}&_fields=id,link,title&status=publish")
        if st == 200 and items:
            out({"url": url, "type": t, "id": items[0]["id"], "link": items[0]["link"], "title": items[0]["title"]["rendered"]})
            return
    out({"url": url, "found": False})


def get_item(env, t, i):
    st, it = api(env, "GET", f"/wp/v2/{t}/{i}?context=edit")
    if st != 200:
        raise SystemExit(json.dumps({"ok": False, "status": st, "error": str(it)[:300]}, ensure_ascii=False))
    return it


def snapshot(env, t, i, plugin):
    it = get_item(env, t, i)
    snap = {"type": t, "id": i, "link": it.get("link"), "title": it["title"]["raw"], "content": it["content"]["raw"],
            "excerpt": it.get("excerpt", {}).get("raw"), "meta": it.get("meta")}
    if plugin == "rankmath":
        snap["seo"] = {k: (it.get("meta") or {}).get(k) for k in ("rank_math_title", "rank_math_description")}
    else:
        snap["seo"] = {k: (it.get("meta") or {}).get(k) for k in ("_yoast_wpseo_title", "_yoast_wpseo_metadesc")}
        hj = it.get("yoast_head_json") or {}
        snap["seo_rendered"] = {"title": hj.get("title"), "description": hj.get("description")}
    return snap


def cmd_backup(env, refs):
    plugin, _ = seo_plugin(env)
    os.makedirs("seo-geo/backup", exist_ok=True)
    data = {"site": env["WP_SITE"], "time": time.strftime("%Y-%m-%d %H:%M:%S"), "plugin": plugin,
            "items": [snapshot(env, *parse_ref(r), plugin) for r in refs]}
    p = f"seo-geo/backup/wp-{time.strftime('%Y%m%d-%H%M%S')}.json"
    json.dump(data, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    out({"ok": True, "backup": p, "items": len(data["items"])})


def cmd_seo(env, ref, title, desc):
    t, i = parse_ref(ref)
    plugin, _ = seo_plugin(env)
    if plugin == "rankmath":
        meta = {}
        if title is not None:
            meta["rank_math_title"] = title
        if desc is not None:
            meta["rank_math_description"] = desc
        st, r = api(env, "POST", "/rankmath/v1/updateMeta", {"objectType": "post", "objectID": i, "meta": meta})
    elif plugin == "yoast":
        meta = {}
        if title is not None:
            meta["_yoast_wpseo_title"] = title
        if desc is not None:
            meta["_yoast_wpseo_metadesc"] = desc
        st, r = api(env, "POST", f"/wp/v2/{t}/{i}", {"meta": meta})
    else:
        out({"ok": False, "error": "אין Yoast או Rank Math באתר. ראו connect-wordpress.md."})
        return
    after = snapshot(env, t, i, plugin)
    ok = st == 200 and all(v is None or v in json.dumps(after["seo"], ensure_ascii=False) for v in (title, desc))
    out({"ok": ok, "status": st, "plugin": plugin, "now": after["seo"],
         "error": None if ok else (r if isinstance(r, str) else r.get("message") if isinstance(r, dict) else str(r))})


def cmd_alt_missing(env):
    st, items = api(env, "GET", "/wp/v2/media?per_page=100&media_type=image&_fields=id,source_url,alt_text,post&context=edit")
    if st != 200:
        out({"ok": False, "status": st})
        return
    miss = [{"id": m["id"], "url": m["source_url"], "attached_to": m.get("post")} for m in items if not (m.get("alt_text") or "").strip()]
    out({"ok": True, "checked": len(items), "missing": len(miss), "items": miss})


def cmd_alt(env, mid, text):
    st0, before = api(env, "GET", f"/wp/v2/media/{mid}?context=edit&_fields=id,alt_text,source_url")
    os.makedirs("seo-geo/backup", exist_ok=True)
    with open("seo-geo/backup/wp-alt.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": time.strftime("%F %T"), "id": mid, "alt_before": (before or {}).get("alt_text")}, ensure_ascii=False) + "\n")
    st, r = api(env, "POST", f"/wp/v2/media/{mid}", {"alt_text": text})
    out({"ok": st == 200 and r.get("alt_text") == text, "id": mid, "alt": r.get("alt_text") if isinstance(r, dict) else None,
         "note": "שימו לב: alt של קובץ במדיה חל על הכנסות חדשות. תמונה שכבר בתוך עמוד שומרת את ה-alt שלה בתוכן העמוד."})


def cmd_content_get(env, ref, path):
    t, i = parse_ref(ref)
    it = get_item(env, t, i)
    open(path, "w", encoding="utf-8").write(it["content"]["raw"])
    out({"ok": True, "file": path, "chars": len(it["content"]["raw"])})


def cmd_content_put(env, ref, path):
    t, i = parse_ref(ref)
    newc = open(path, encoding="utf-8").read()
    st, r = api(env, "POST", f"/wp/v2/{t}/{i}", {"content": newc})
    out({"ok": st == 200, "status": st, "link": r.get("link") if isinstance(r, dict) else None})


def cmd_restore(env, path):
    data = json.load(open(path, encoding="utf-8"))
    res = []
    for it in data["items"]:
        body = {"title": it["title"], "content": it["content"]}
        if it.get("excerpt") is not None:
            body["excerpt"] = it["excerpt"]
        st, _ = api(env, "POST", f"/wp/v2/{it['type']}/{it['id']}", body)
        seo = {k: v for k, v in (it.get("seo") or {}).items() if v is not None}
        if seo and data.get("plugin") == "rankmath":
            api(env, "POST", "/rankmath/v1/updateMeta", {"objectType": "post", "objectID": it["id"], "meta": seo})
        elif seo:
            api(env, "POST", f"/wp/v2/{it['type']}/{it['id']}", {"meta": seo})
        res.append({"id": it["id"], "status": st})
    out({"ok": all(r["status"] == 200 for r in res), "restored": res})


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return
    env = load_env()
    c = a[0]
    if c == "check":
        cmd_check(env)
    elif c == "find":
        cmd_find(env, a[1])
    elif c == "backup":
        cmd_backup(env, a[1:])
    elif c == "seo":
        title = a[a.index("--title") + 1] if "--title" in a else None
        desc = a[a.index("--desc") + 1] if "--desc" in a else None
        cmd_seo(env, a[1], title, desc)
    elif c == "alt-missing":
        cmd_alt_missing(env)
    elif c == "alt":
        cmd_alt(env, int(a[1]), a[2])
    elif c == "content-get":
        cmd_content_get(env, a[1], a[2])
    elif c == "content-put":
        cmd_content_put(env, a[1], a[2])
    elif c == "restore":
        cmd_restore(env, a[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
