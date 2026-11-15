# חיבור: Wix

Wix נותן היום API שכותב את ה-SEO של עמוד: כותרת, תיאור, Open Graph, canonical, Schema (JSON-LD) ו-robots של עמוד.
מה שאין לו API: robots.txt של האתר, alt לתמונות בעורך, וכותרות H בתוך העמוד. אלה נעשים בעורך, צעד אחר צעד מהדוח.

**מה צריך:** חיבור דרך Composio (הכי פשוט) **או** מפתח API של Wix עם הרשאת SEO. **למה:** כדי לכתוב בעצמי כותרות,
תיאורים ו-Schema לעמודים, במקום שתעברו עמוד-עמוד. **ביטול:** Composio: `composio connections` → למחוק את החיבור של Wix.
מפתח API: Account Settings > API Keys > **Delete** ליד המפתח.

---

## דרך 1 (מומלצת): Composio

1. `composio connections list --toolkit wix`. ACTIVE → ממשיכים לבדיקה.
2. אין → `AskUserQuestion`: "לחבר את Wix דרך Composio? נפתח חלון בדפדפן, מתחברים ל-Wix ומאשרים." `כן, תפתח` · `אחבר בעצמי`.
   "כן" → `composio link wix`, ושוב `connections list` עד ACTIVE.
   `composio` לא מותקן / לא מחובר → "יש על Composio שיעור במועדון (חיבור כלים). אחרי `composio login` תכתוב לי 'המשך'."
3. **בדיקה (קריאה):** `composio search "wix list site pages seo tags"` → הכלי שמחזיר את רשימת העמודים או את תגיות ה-SEO שלהם,
   וקריאה אחת שלו. (ב-Composio, Wix עובד דרך כלים כלליים כמו `WIX_MCP_CALL_WIX_SITE_API`, שמריצים כל קריאת REST של Wix.)

## דרך 2: מפתח API

צעדים למשתמש (מקור: support.wix.com/en/article/managing-your-wix-api-keys):
1. נכנסים ל-Wix, תפריט החשבון > **Account Settings** > **API Keys** > **Generate API Key**.
2. שם: `seo-geo-audit`. בהרשאות מסמנים **Manage SEO Settings**. ומגבילים את המפתח **לאתר הזה בלבד** (ברירת המחדל: כל האתרים).
3. Wix שולח קוד בן 6 ספרות למייל. מקלידים.
4. מעתיקים את המפתח. **מוצג פעם אחת בלבד.**
5. מזהה האתר (Site ID): בכתובת של הדשבורד, הקטע שאחרי `/dashboard/`.

רק בעלים או שותף-בעלים יכולים ליצור מפתח. קלוד יוצר `.env` עם `WIX_API_KEY=PASTE_HERE` ו-`WIX_SITE_ID=PASTE_HERE`, `open .env`,
והמשתמש מדביק ושומר.

**בדיקה (קריאה):**
```bash
set -a; . ./.env; set +a
curl -s -H "Authorization: $WIX_API_KEY" -H "wix-site-id: $WIX_SITE_ID" \
  "https://www.wixapis.com/promote/seo/v1/site-seo-tags" | head -c 400
```
(לא מדפיסים את המפתח. 401 = מפתח שגוי / בלי הרשאת SEO. 404 על האתר = Site ID שגוי.)

---

## מה כותבים ואיך (שלב 3)

**כתיבה מחליפה את כל התגיות של העמוד.** לכן תמיד: קוראים את התגיות הקיימות → שומרים ב-`seo-geo/backup/` → משנים
רק את מה שבתוכנית → שולחים את כל הסט.

| תיקון | API | בעורך (אם אין חיבור / אין API) |
|---|---|---|
| כותרת + תיאור של עמוד | `PATCH https://www.wixapis.com/promote/seo/v1/item-seo-tags/STATIC_PAGE/{pageId}` עם `{"itemSeoTags":{"tags":[...]},"fieldMask":"tags","publish":true}`. מוצר: `STORES_PRODUCT`, פוסט: `BLOG_POST` | Wix Editor: **Pages & Menu** > ליד העמוד **...** (More Actions) > **SEO basics** > כותרת ותיאור > **Publish**. Wix Studio: **Pages** > More Actions > **SEO Basics** |
| Schema (JSON-LD) לעמוד | אותו PATCH, תגית `script` עם ה-JSON-LD | הגדרות ה-SEO של העמוד > **Advanced SEO** > **Structured Data Markup** > **+ Add New Markup** (JSON-LD, עד 5) |
| robots.txt | אין API | דשבורד: **SEO** (או **SEO & GEO**) > **Tools and settings** > **Robots.txt Editor** > **View File** > עריכה > Save |
| alt לתמונה | אין API לעורך | לבחור את התמונה > אייקון **Settings** > **"What's in the image?"** (Studio: **Manage Media** > **Alt text**) > Publish |
| כותרות H | אין API | לבחור את הטקסט > **Themes** / סגנון טקסט > Heading 1/2/3 |
| sitemap | Wix מייצר לבד ומפנה אליו ב-robots.txt | לשלוח ב-Search Console |

- עמוד סטטי צריך `publish: true` כדי שהשינוי יעלה לאתר החי. אתר שמעולם לא פורסם מחזיר `DRAFT_SAVED_NOT_PUBLISHED`.
- רק בשפה הראשית של האתר. אתר רב-לשוני: שאר השפות בעורך.
- מקורות: dev.wix.com/docs/api-reference/business-management/seo/item-seo-tags-v1/set-item-seo-tags ·
  support.wix.com/en/article/adding-seo-title-tags-and-meta-descriptions-to-your-pages ·
  support.wix.com/en/article/adding-structured-data-markup-to-your-sites-pages-2546962 ·
  support.wix.com/en/article/editing-your-sites-robotstxt-file

אחרי כל כתיבה: קוראים את התגיות שוב ומשווים. ואחרי כל התיקונים: `audit.py` על האתר החי (`audit-after.json`).
