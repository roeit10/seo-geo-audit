# חיבור: Webflow, Framer, Squarespace, או "לא יודע על מה האתר בנוי"

בכל פלטפורמה: קודם בודקים אם יש חיבור ב-Composio (`composio search "<platform> update page seo"`), אחר כך API ישיר,
ואם אין, **צעד אחר צעד בעורך** לכל תיקון, בדוח. זה עדיין שווה: רשימה מסודרת של מה להקליד ואיפה.

---

## Webflow (יש API לכותרות, תיאורים ו-Open Graph)

**מה צריך:** Composio (`composio link webflow`) **או** טוקן אתר. **ביטול:** Site settings > Apps & integrations > API access > **Revoke**.

טוקן אתר (מקור: developers.webflow.com/data/reference/site-token):
1. **Site settings** > **Apps & integrations** > **API access** > **Generate API token**.
2. שם: `seo-geo-audit`. הרשאות: `pages:read`, `pages:write`, `sites:write` (לפרסום). **Generate token**, מעתיקים ל-`.env` (`WEBFLOW_TOKEN=PASTE_HERE`).
3. בדיקה: `GET https://api.webflow.com/v2/sites` (רשימת אתרים) → `GET /v2/sites/{id}/pages`.

| תיקון | API | בעורך |
|---|---|---|
| כותרת, תיאור, Open Graph | `PUT /v2/pages/{page_id}` עם `seo.title`, `seo.description`, `openGraph.*` (גיבוי ב-GET לפני) | Pages panel > ⚙ Page settings > SEO settings |
| פרסום | `POST /v2/sites/{id}/publish` (פעם בדקה לכל היותר), רק באישור | Publish |
| Schema (JSON-LD) | אין לטוקן אתר | Page settings > **Custom code** > **Inside <head> tag** |
| robots.txt / sitemap | אין | **Site settings > SEO > Indexing** / **Sitemap > Auto-generate sitemap** |
| alt | אין לטוקן אתר | לבחור תמונה > ⚙ Image settings > Alt text |

מקורות: developers.webflow.com/data/reference/pages-and-components/pages/update-page-settings · developers.webflow.com/data/reference/sites/publish

## Framer (בעיקר בעורך)

ל-Framer יש Server API לתוכן CMS וקוד כללי לאתר, אבל **לא לכותרת ותיאור של עמוד רגיל**. עמודי CMS שהכותרת שלהם
לקוחה משדה (`{{Title}}`) אפשר לעדכן דרך ה-CMS. בפועל: צעדים בעורך.

| תיקון | בעורך |
|---|---|
| כותרת ותיאור | **Page Settings** > Title / Description > Publish |
| Schema | Page Settings > **Custom Code** > Head |
| robots / sitemap | אוטומטי. להסתרת עמוד: "Show page in search engines" בהגדרות העמוד |

מקור: framer.com/help/articles/how-to-update-page-titles-descriptions-and-social-images/ · framer.com/developers/server-api-introduction
(⚠ חלק מהתוויות לא נבדקו ישירות בעורך; לבדוק מול המסך).

## Squarespace (בעורך בלבד)

אין API לעריכת עמודים או SEO של עמודים (support.squarespace.com/hc/en-us/articles/41325887099533).

| תיקון | בעורך |
|---|---|
| כותרת ותיאור | **Pages** > מעבר עם העכבר על העמוד > ⚙ > **SEO** > SEO Title / SEO Description |
| Schema | אותו חלון > **Advanced** > **Page Header Code Injection** |
| תבנית כותרות לכל האתר | פאנל **SEO** > SEO Settings > Search Appearance |

## לא יודעים על מה האתר בנוי

1. `detect.json` עם `unknown` → אומרים מה כן נמצא (אחסון, שרת).
2. `AskUserQuestion`: **"מי בנה את האתר / איפה עורכים אותו?"** `יש לי כניסה לניהול (שולחים צילום מסך של המסך הראשי)` ·
   `מפתח / חברה בנו לי` · `אני לא יודע` · Other.
3. "מפתח בנה" → הדוח כתוב גם בשבילו: כל תיקון עם קוד מוכן להדבקה (מטא, JSON-LD, robots) ואיפה זה בדרך כלל נמצא.
4. פרופיל: `חיבור: אין (דוח וקטעים להדבקה)`. אפשר לחזור לאשף בכל רגע: "תעדכן את הפרופיל של seo-geo-audit".
