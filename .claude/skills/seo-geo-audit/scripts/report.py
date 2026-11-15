#!/usr/bin/env python3
"""
seo-geo-audit: render the Hebrew RTL report (HTML) from the audit JSON files.

The numbers come only from the audit JSON (before / after). The words Claude wrote
(owner summary, what was fixed, the plan, GEO proposals, snippets) come from notes.json.
Nothing here is invented: an empty notes field = the section is not shown.

Usage:
  python3 report.py --before seo-geo/audit-before.json [--after seo-geo/audit-after.json] \
      --notes seo-geo/notes.json --out seo-geo/report.html [--brand-color "#1f6feb"]
"""
import argparse
import html
import json
import os

STATUS_HE = {"fail": "לתקן", "warn": "לשפר", "pass": "תקין", "info": "מידע", "na": "לא רלוונטי"}
WHEN_HE = [("week", "השבוע"), ("month", "החודש"), ("quarter", "ברבעון הקרוב")]


def e(s):
    return html.escape(str(s if s is not None else ""))


def color_for(score):
    if score is None:
        return "var(--muted)"
    if score >= 90:
        return "var(--good)"
    if score >= 70:
        return "var(--mid)"
    return "var(--bad)"


def bar(score):
    if score is None:
        return '<div class="bar"><span style="width:0"></span></div>'
    return f'<div class="bar"><span style="width:{score}%;background:{color_for(score)}"></span></div>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after")
    ap.add_argument("--notes")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand-color", default="")
    a = ap.parse_args()

    b = json.load(open(a.before, encoding="utf-8"))
    af = json.load(open(a.after, encoding="utf-8")) if a.after and os.path.exists(a.after) else None
    n = json.load(open(a.notes, encoding="utf-8")) if a.notes and os.path.exists(a.notes) else {}
    accent = a.brand_color or n.get("brand_color") or "#1f4fd8"
    name = n.get("business_name") or b["site"]
    y, mo, d = b["date"].split(" ")[0].split("-")
    date_he = f"{int(d)}.{int(mo)}.{y}"
    after_label = "אחרי (בנייה מקומית, לפני עלייה לאוויר)" if af and af.get("mode") == "local-build" else "אחרי"

    parts = []
    w = parts.append

    # ---------- header
    w(f'''<header class="hero">
  <div class="kicker">דוח SEO ו-GEO · {e(date_he)}</div>
  <h1>{e(name)}</h1>
  <div class="site">{e(b["site"])}</div>
  <div class="scores">
    <div class="score"><div class="num" style="color:{color_for(b["score"])}">{b["score"]}</div><div class="lbl">ציון לפני</div></div>''')
    if af:
        delta = af["score"] - b["score"]
        w(f'''    <div class="arrow">←</div>
    <div class="score"><div class="num" style="color:{color_for(af["score"])}">{af["score"]}</div><div class="lbl">{e(after_label)}</div></div>
    <div class="delta" dir="ltr">{"+" if delta >= 0 else ""}{delta}</div>''')
    w('  </div>')
    s = b["summary"]
    w(f'  <div class="meta">נבדקו {s["pages_crawled"]} עמודים מרכזיים · {s["sitemap_urls"]} כתובות במפת האתר · '
      f'{s["fails"]} לתקן · {s["warns"]} לשפר · {s["passes"]} תקין (לפני)</div>')
    w('</header>')

    # ---------- owner summary
    if n.get("owner_summary"):
        w('<section class="card owner"><h2>בשורה התחתונה</h2><ul>')
        for line in n["owner_summary"]:
            w(f"<li>{e(line)}</li>")
        w("</ul></section>")

    # ---------- categories
    w('<section class="card"><h2>הציון לפי תחום</h2><table class="cats"><thead><tr><th>תחום</th><th>מה זה אומר</th>'
      '<th>לפני</th>' + ('<th>אחרי</th>' if af else '') + '</tr></thead><tbody>')
    for cid, v in b["categories"].items():
        av = af["categories"].get(cid, {}).get("score") if af else None
        w(f'<tr><td class="cn">{e(v["name"])}</td><td class="plain">{e(v["plain"])}</td>'
          f'<td class="sc"><b style="color:{color_for(v["score"])}">{v["score"] if v["score"] is not None else "-"}</b>{bar(v["score"])}</td>')
        if af:
            w(f'<td class="sc"><b style="color:{color_for(av)}">{av if av is not None else "-"}</b>{bar(av)}</td>')
        w("</tr>")
    w("</tbody></table>")
    w('<p class="note">הציון מחושב בסקריפט, באותן בדיקות בכל ריצה. אותו אתר = אותו ציון. '
      'משקל כל תחום בציון הכולל: ' + " · ".join(f'{e(v["name"])} {v["weight"]}%' for v in b["categories"].values()) + '.</p>')
    w("</section>")

    # ---------- per key page
    import urllib.parse as _up
    bp = {p["url"]: p for p in b.get("pages", [])}
    ap_ = {p["url"]: p for p in (af or {}).get("pages", [])}
    if bp:
        w('<section class="card"><h2>עמוד אחר עמוד</h2><table class="pages"><thead><tr><th>עמוד</th><th>מה נמצא</th>'
          + ('<th>אחרי</th>' if af else '') + '</tr></thead><tbody>')
        for u, p in bp.items():
            path = _up.urlparse(u).path or "/"
            iss = p.get("issues", [])
            w(f'<tr><td class="pg"><b dir="ltr">{e(path)}</b><div class="ttl">{e(p.get("title"))}</div></td><td>')
            w('<span class="pill pass">תקין</span>' if not iss else "<ul>" + "".join(f"<li>{e(i)}</li>" for i in iss) + "</ul>")
            w("</td>")
            if af:
                a2 = ap_.get(u, {})
                left = a2.get("issues", [])
                fixed = [i for i in iss if i not in left]
                cell = []
                if fixed:
                    cell.append(f'<span class="pill pass">תוקנו {len(fixed)}</span>')
                if left:
                    cell.append("<ul>" + "".join(f"<li>נשאר: {e(i)}</li>" for i in left) + "</ul>")
                if not iss and not left:
                    cell.append('<span class="pill pass">תקין</span>')
                w("<td>" + "".join(cell) + "</td>")
            w("</tr>")
        w('</tbody></table><p class="note">רק העמודים המרכזיים נבדקים. בדיקות של כל האתר (robots.txt, מפת האתר, בוטים של AI, HTTPS) מופיעות בהמשך.</p></section>')

    # ---------- fixed
    if n.get("fixed"):
        w('<section class="card"><h2>מה תוקן</h2><ol class="fixed">')
        for f in n["fixed"]:
            w(f'<li><b>{e(f.get("title"))}</b>')
            if f.get("why"):
                w(f'<div class="why">{e(f["why"])}</div>')
            if f.get("where"):
                w(f'<div class="where">{e(f["where"])}</div>')
            w("</li>")
        w("</ol></section>")

    # ---------- plan
    plan = n.get("plan") or {}
    if any(plan.get(k) for k, _ in WHEN_HE):
        w('<section class="card"><h2>מה נשאר: תוכנית עבודה</h2><div class="plan">')
        for k, label in WHEN_HE:
            items = plan.get(k) or []
            w(f'<div class="col"><h3>{label}</h3>')
            if not items:
                w('<p class="muted">אין.</p>')
            for it in items:
                w(f'<div class="item"><b>{e(it.get("title"))}</b>')
                if it.get("why"):
                    w(f'<div class="why">{e(it["why"])}</div>')
                if it.get("how"):
                    w(f'<div class="how">{e(it["how"])}</div>')
                w("</div>")
            w("</div>")
        w("</div></section>")

    # ---------- GEO proposals
    if n.get("geo_proposals"):
        w('<section class="card"><h2>הצעות לתוכן (GEO), לאישור שלכם</h2>'
          '<p class="note">הסקיל לא משכתב תוכן לבד. כל הצעה מחכה לאישור, ונכתבת בקול של העסק.</p><table class="geo">'
          '<thead><tr><th>עמוד</th><th>מה מוצע</th><th>מצב</th></tr></thead><tbody>')
        for g in n["geo_proposals"]:
            w(f'<tr><td>{e(g.get("page"))}</td><td>{e(g.get("what"))}</td><td>{e(g.get("status", "ממתין לאישור"))}</td></tr>')
        w("</tbody></table></section>")

    # ---------- snippets (Wix / Shopify / other)
    if n.get("snippets"):
        w('<section class="card"><h2>להדבקה: קוד והוראות</h2>')
        for sn in n["snippets"]:
            w(f'<div class="snip"><b>{e(sn.get("title"))}</b><div class="where">{e(sn.get("where"))}</div>'
              f'<pre dir="ltr">{e(sn.get("code"))}</pre></div>')
        w("</section>")

    # ---------- findings (from the after run if exists, else before)
    src = af or b
    w(f'<section class="card"><h2>כל הבדיקות {"(המצב אחרי)" if af else ""}</h2>')
    cats = {cid: v["name"] for cid, v in b["categories"].items()}
    for cid, cname in cats.items():
        cs = [c for c in src["checks"] if c["category"] == cid]
        if not cs:
            continue
        w(f'<h3>{e(cname)}</h3><table class="checks"><tbody>')
        for c in cs:
            st = c["status"]
            w(f'<tr class="{st}"><td class="st"><span class="pill {st}">{STATUS_HE.get(st, st)}</span></td>'
              f'<td><b>{e(c["title"])}</b><div class="detail">{e(c["detail"])}</div>')
            if c.get("evidence") and st in ("fail", "warn"):
                more = c.get("evidence_count", 0) - len(c["evidence"])
                w('<details><summary>איפה ' + f'({c.get("evidence_count", len(c["evidence"]))})</summary><ul dir="auto">')
                for ev in c["evidence"]:
                    w(f'<li dir="auto">{e(ev)}</li>')
                if more > 0:
                    w(f"<li>ועוד {more}</li>")
                w("</ul></details>")
            if c.get("source"):
                w(f'<div class="src">מקור: <a href="https://{e(c["source"])}">{e(c["source"])}</a></div>')
            w("</td></tr>")
        w("</tbody></table>")
    w("</section>")

    # ---------- validation + GBP
    vl = b.get("validation_links", {})
    w('<section class="card"><h2>איך בודקים בעצמכם</h2><ul class="links">')
    labels = [("rich_results", "Rich Results Test של גוגל: האם גוגל קורא את ה-Schema"),
              ("schema_validator", "Schema Validator: בדיקה מלאה של הנתונים המובנים"),
              ("pagespeed", "PageSpeed Insights: מהירות ומובייל"),
              ("search_console", "Google Search Console: לשלוח את מפת האתר ולראות מה באינדקס")]
    for k, lbl in labels:
        if vl.get(k):
            w(f'<li><a href="{e(vl[k])}">{e(lbl)}</a></li>')
    w("</ul>")
    gbp = n.get("gbp") or ("פרופיל עסק בגוגל (Google Business Profile): אם יש לכם לקוחות באזור מסוים, זה הצעד הכי משמעותי "
                           "לחיפוש מקומי ולתשובות AI על עסקים באזור. הסקיל לא נוגע בו, רק ממליץ.")
    w(f'<p class="gbp"><b>Google Business Profile:</b> {e(gbp)} <a href="{e(vl.get("business_profile", "https://www.google.com/business/"))}">פתיחה/עריכה</a></p>')
    w('<p class="note">ציפיות: שינויים טכניים נקלטים בגוגל תוך ימים עד שבועות. נראות במנועי AI לוקחת בדרך כלל 14-21 יום ויותר, '
      'ו-76% מהציטוטים ב-AI Overviews מגיעים מעמודים שכבר בטופ 10 בגוגל. SEO קלאסי הוא הבסיס.</p>')
    w("</section>")

    if b.get("notes") or (af and af.get("notes")):
        w('<section class="card small"><h2>הערות לריצה</h2><ul>')
        for x in (b.get("notes") or []) + ((af or {}).get("notes") or []):
            w(f"<li>{e(x)}</li>")
        w("</ul></section>")

    w('<footer>נוצר עם הסקיל seo-geo-audit. כללי ה-SEO לפי Ahrefs, עם מקור ליד כל בדיקה.</footer>')

    doc = f'''<!doctype html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>דוח SEO ו-GEO · {e(name)}</title>
<style>
:root{{--accent:{accent};--ink:#14161a;--muted:#6b7280;--line:#e5e7eb;--bg:#f6f7f9;--card:#fff;
--good:#15803d;--mid:#b45309;--bad:#b91c1c}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "Heebo","Assistant","Arial Hebrew",Arial,sans-serif;direction:rtl}}
main{{max-width:980px;margin:0 auto;padding:24px 16px 48px}}
.hero{{background:var(--card);border-top:6px solid var(--accent);border-radius:14px;padding:28px;margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kicker{{color:var(--accent);font-weight:700;font-size:14px;letter-spacing:.3px}}
h1{{margin:4px 0 0;font-size:30px}} .site{{color:var(--muted);direction:ltr;text-align:right}}
.scores{{display:flex;align-items:center;gap:22px;margin:18px 0 8px;flex-wrap:wrap}}
.score .num{{font-size:64px;font-weight:800;line-height:1}} .score .lbl{{color:var(--muted);font-size:14px}}
.arrow{{font-size:36px;color:var(--muted)}} .delta{{background:#ecfdf5;color:var(--good);font-weight:800;border-radius:999px;padding:6px 14px;font-size:20px}}
.meta{{color:var(--muted);font-size:14px}}
.card{{background:var(--card);border-radius:14px;padding:22px 24px;margin-bottom:18px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card h2{{margin:0 0 12px;font-size:22px}} .card h3{{margin:18px 0 8px;font-size:17px;color:var(--accent)}}
.owner ul{{margin:0;padding-inline-start:20px}} .owner li{{margin:6px 0;font-size:17px}}
table{{width:100%;border-collapse:collapse}} td,th{{padding:10px 8px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}}
th{{font-size:13px;color:var(--muted);font-weight:600}}
.cats .cn{{font-weight:700;white-space:nowrap}} .cats .plain{{color:var(--muted);font-size:14px}} .cats .sc{{width:120px}}
.bar{{height:6px;background:var(--line);border-radius:4px;margin-top:4px;overflow:hidden}} .bar span{{display:block;height:100%}}
.note{{color:var(--muted);font-size:13px;margin:10px 0 0}}
.fixed li{{margin:10px 0}} .why{{color:#374151;font-size:15px}} .where,.how{{color:var(--muted);font-size:13px}}
.plan{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}} .plan .col{{background:var(--bg);border-radius:10px;padding:12px}}
.plan h3{{margin:0 0 8px}} .plan .item{{margin:0 0 12px}}
.checks .st{{width:70px}} .pill{{display:inline-block;font-size:12px;font-weight:700;border-radius:999px;padding:2px 10px}}
.pill.fail{{background:#fee2e2;color:var(--bad)}} .pill.warn{{background:#fef3c7;color:var(--mid)}} .pill.pass{{background:#dcfce7;color:var(--good)}}
.pill.info,.pill.na{{background:#eef2ff;color:#4338ca}}
.detail{{font-size:14px;color:#374151}} .src{{font-size:12px;color:var(--muted)}} .src a{{color:var(--muted)}}
details{{font-size:13px;margin-top:4px}} details ul{{margin:4px 0;padding-inline-start:18px;word-break:break-all}}
.snip pre{{background:#0f172a;color:#e2e8f0;padding:12px;border-radius:8px;overflow:auto;font-size:13px;text-align:left}}
.pages .pg{{width:34%}} .pages .ttl{{color:var(--muted);font-size:13px}} .pages ul{{margin:0;padding-inline-start:18px;font-size:14px}}
.links li{{margin:6px 0}} a{{color:var(--accent)}} .gbp{{background:var(--bg);padding:12px;border-radius:10px}}
.small{{font-size:14px}} footer{{text-align:center;color:var(--muted);font-size:13px;margin-top:12px}}
@media (max-width:700px){{.plan{{grid-template-columns:1fr}} .score .num{{font-size:48px}} .cats .plain{{display:none}}}}
@media print{{body{{background:#fff}} .card,.hero{{box-shadow:none;border:1px solid var(--line);break-inside:avoid-page}} details{{display:block}} details>*{{display:block}}}}
</style></head><body><main>
{chr(10).join(parts)}
</main></body></html>'''
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(doc)
    print("report:", a.out)


if __name__ == "__main__":
    main()
