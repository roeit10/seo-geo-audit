# חיבור: וורדפרס

**מה צריך:** סיסמת אפליקציה (Application Password) של משתמש עם הרשאת עריכה. **למה:** כדי שאוכל לעדכן בעצמי כותרות,
תיאורים, alt ותוכן דרך ה-API של וורדפרס, עם גיבוי לפני כל שינוי. זו לא הסיסמה שלכם לכניסה, ואפשר לבטל אותה בלחיצה.
**ביטול:** Users > Profile > Application Passwords > **Revoke** ליד הסיסמה. הטבלה שם מראה גם מתי השתמשו בה לאחרונה.

וורדפרס.com (האתר מתארח אצל WordPress.com ולא אצל חברת אחסון)? שם עובדים דרך Composio (`composio link wordpress_com`),
לא דרך סיסמת אפליקציה. ממשיכים מצעד 4.

---

## צעד 1: לוודא שה-API פתוח (קלוד, בלי לשאול)

`detect.json` → `wp_rest.ok` ו-`wp_pages_readable`. אם `false`: ייתכן שתוסף אבטחה חוסם את `/wp-json/`
(Wordfence, iThemes, "Disable REST API"). אומרים: "תוסף אבטחה חוסם את ה-API. צריך לאפשר אותו למשתמשים מחוברים." ועוצרים
עד שזה פתוח. האתר חייב HTTPS (בלי HTTPS וורדפרס לא מציג את האפשרות ליצור סיסמת אפליקציה).

## צעד 2: יוצרים סיסמת אפליקציה (המשתמש, בדפדפן)

נותנים את הצעדים בדיוק כך:

1. נכנסים לניהול האתר: `<האתר>/wp-admin`.
2. בתפריט: **Users** (משתמשים) > **Profile** (פרופיל).
3. גוללים למטה עד **Application Passwords** (סיסמאות אפליקציה).
4. בשדה **New Application Password Name** כותבים: `seo-geo-audit`.
5. לוחצים **Add Application Password** (הוספת סיסמת אפליקציה).
6. מופיעה סיסמה של 24 תווים ברווחים. **היא מוצגת פעם אחת בלבד.** מעתיקים אותה.

המשתמש צריך להיות Administrator או Editor. אין את הסעיף בכלל? או שאין HTTPS, או שתוסף אבטחה כיבה אותו.
מקור: github.com/WordPress/wordpress-develop/blob/trunk/src/wp-admin/user-edit.php ·
make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/

## צעד 3: הסיסמה לקובץ, לא לצ'אט

קלוד יוצר `.env` (ומוודא ש-`.env` ב-`.gitignore`):

```
WP_SITE=https://example.co.il
WP_USER=<שם המשתמש של הכניסה>
WP_APP_PASSWORD=PASTE_HERE
```

`open .env` → "הדבק את הסיסמה במקום PASTE_HERE, ובשורה של WP_USER את שם המשתמש שלך בוורדפרס. שמור, וכתוב לי 'שמרתי'."

## צעד 4: בדיקה

```bash
python3 SKILL/scripts/wp.py check
```

מציגים: "מחובר כ-<שם>, הרשאה <role>. תוסף SEO: <Yoast / Rank Math / אין>. כתיבת כותרת ותיאור: <כן / לא, ולמה>."
**שום דבר לא נכתב בבדיקה.**

## צעד 5: תוסף ה-SEO, ואיך כותבים כותרת ותיאור

| מצב | מה עושים |
|---|---|
| **Rank Math** | כותבים דרך `rankmath/v1/updateMeta` (`wp.py seo`). לא צריך להפעיל שום הגדרה. ⚠ זה endpoint לא מתועד רשמית; אם הוא מחזיר שגיאה → צעדים בעורך (למטה) |
| **Yoast 27.7 ומעלה, פוסטים** | `_yoast_wpseo_title` ו-`_yoast_wpseo_metadesc` בתוך `meta` (`wp.py seo posts:<id>`) |
| **Yoast, עמודים (pages) / Yoast ישן** | Yoast לא חושף את השדות לכתיבה בעמודים (`wp.py check` → `yoast_meta_writable: false`). שתי דרכים, `AskUserQuestion`: **(1)** תוסף קטן שמאפשר את זה: "SEO Fields API Support" (Plugins > Add New > חיפוש > Install > Activate), אחר כך שוב `wp.py check`. **(2)** בלי תוסף: אני כותב בדוח את הכותרת והתיאור לכל עמוד, ואתם מדביקים: עורך העמוד > תיבת Yoast SEO למטה > SEO title / Meta description > Update |
| **אין תוסף SEO** | `AskUserQuestion`: **"אין באתר תוסף SEO. להתקין Yoast?"** `כן, אתקין` (Plugins > Add New Plugin > חיפוש "Yoast SEO" > Install Now > Activate, ואז שוב `wp.py check`) · `לא, רק דוח`. בלי תוסף, וורדפרס לא מציג תיאור לגוגל בכלל, ותבנית (theme) שמוסיפה מטא בקוד = עבודה של מפתח |

מקורות: Yoast: github.com/Yoast/wordpress-seo/blob/trunk/inc/class-wpseo-meta.php (נרשם ל-REST מגרסה 27.7, לסוג post בלבד) ·
developer.yoast.com/customization/apis/rest-api/ (`yoast_head_json` לקריאה בלבד) ·
Rank Math: github.com/rankmath/seo-by-rank-math/blob/master/includes/rest/class-shared.php

## מה עושים בכל תיקון (שלב 3)

**תמיד קודם:** `python3 SKILL/scripts/wp.py backup pages:<id> posts:<id> ...` לכל עמוד שייגע. החזרה: `wp.py restore <קובץ>`.

| תיקון | איך |
|---|---|
| כותרת / תיאור | `wp.py find <url>` → `wp.py seo pages:<id> --title "..." --desc "..."` → הפלט מראה את הערך החדש |
| alt לתמונות | `wp.py alt-missing` → `wp.py alt <media_id> "<תיאור>"`. ⚠ alt בספריית המדיה חל על הכנסות חדשות. תמונה שכבר בתוך עמוד: ה-alt שמור בתוכן העמוד → `content-get`, תיקון ה-`alt=""` בבלוק התמונה, `content-put` |
| כותרות H (H1 כפולה, דילוג רמה) | `content-get` → עריכה מינימלית של הבלוקים (`<!-- wp:heading {"level":3} -->` + התג) → `content-put`. H1 כפולה שמגיעה מהתבנית (theme) → לא בתוכן, מדווחים כצעד בעורך התבנית |
| בלוקי GEO שאושרו | `content-get` → מוסיפים בלוק פסקה / כותרות / רשימת שאלות (בלוקי Gutenberg) במקום שאושר → `content-put` |
| Schema של העסק | Yoast: **Yoast SEO > Settings > Site representation** (ארגון או אדם, שם, לוגו, רשתות). Rank Math: **Rank Math SEO > Titles & Meta > Local SEO**. אלה הגדרות בממשק, לא API → צעדים בדוח |
| robots.txt | וירטואלי כברירת מחדל. Yoast: **Yoast SEO > Tools > File editor > Create robots.txt file** (צריך הרשאת כתיבה לקבצים). צעדים בדוח |
| sitemap | וורדפרס 5.5+: `/wp-sitemap.xml`. Yoast מחליף ל-`/sitemap_index.xml`. לרוב לא צריך לגעת; לשלוח ב-Search Console |

אחרי כל כתיבה: `wp.py` מדפיס את הערך שנקרא חזרה. ערך שלא תואם = "לא בוצע", בראש הדוח.
**מטמון (cache):** תוסף מטמון (WP Rocket, LiteSpeed Cache, W3TC) או Cloudflare יכולים להציג את הגרסה הישנה לבדיקה שאחרי.
אומרים, ומבקשים לנקות מטמון (Purge All) לפני ה-audit שאחרי.

## תקלות

| מה חוזר | מה זה | מה עושים |
|---|---|---|
| `rest_not_logged_in` עם סיסמה נכונה | השרת (Apache/LiteSpeed) מוחק את כותרת ה-Authorization | לבקש מהאחסון / מהמפתח להוסיף ל-`.htaccess`: `SetEnvIf Authorization "(.*)" HTTP_AUTHORIZATION=$1` (מקור: developer.wordpress.org/rest-api/frequently-asked-questions/). עד אז: דוח וצעדים בעורך |
| `incorrect_password` / `invalid_username` | שם משתמש או סיסמה | שם המשתמש של הכניסה (לא שם התצוגה). הרווחים בסיסמה לא משנים |
| `rest_cannot_edit` / 403 | אין הרשאה | משתמש Editor/Administrator |
| `rest_additional_properties_forbidden` | Yoast לא רושם את השדות לסוג הזה | שורת "Yoast, עמודים" בטבלה למעלה |
| 401/403 מתוסף אבטחה | Wordfence וכו' | לאפשר REST למשתמשים מחוברים |
