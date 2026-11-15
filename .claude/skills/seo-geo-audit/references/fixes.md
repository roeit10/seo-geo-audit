# איך מתקנים כל בדיקה, לפי פלטפורמה

המפתח הוא שדה `fix` בכל בדיקה ב-`audit-before.json`. לכל תיקון בתוכנית: **מה** (היה → עכשיו), **איפה בדיוק**,
**למה זה טוב לעסק** בשורה אחת. הכללים עצמם והמקורות: `ahrefs-rules.md`. איך כותבים לפלטפורמה: `connect-<platform>.md`.

| fix | מה עושים | למה (לבעל העסק) | קוד | וורדפרס | Wix / Shopify / אחר |
|---|---|---|---|---|---|
| `robots` | שורת `Sitemap:` עם הכתובת המלאה. מוחקים `Noindex:` / `Crawl-delay:` (גוגל מתעלם). לא חוסמים `/_next/`, `/wp-includes/`, CSS/JS | "זה השלט בכניסה לאתר: מה מותר לסרוק ואיפה המפה" | `app/robots.ts` / `public/robots.txt` | Yoast > Tools > File editor | Wix: Robots.txt Editor · Shopify: `robots.txt.liquid` · Webflow: SEO > Indexing |
| `sitemap` | להסיר מהמפה כתובות שמחזירות הפניה / 404 / noindex, או לתקן אותן. מפה על הדומיין הראשי ב-HTTPS. אין מפה? ליצור | "המפה אומרת לגוגל אילו עמודים קיימים. כתובת שבורה במפה מבזבזת לו זמן" | `app/sitemap.ts`, `@astrojs/sitemap`, `sitemap.xml` | לרוב אוטומטי (wp-sitemap / Yoast). כתובת שבורה = העמוד עצמו | אוטומטי. מתקנים את העמוד |
| `noindex` | להוריד noindex מעמוד שצריך להופיע. **רק אחרי אישור מפורש לכל עמוד**: לפעמים זה בכוונה (עמוד תודה, טיוטה) | "עמוד עם noindex לא יופיע בגוגל בכלל" | `robots: { index: false }` ב-metadata / `<meta name="robots">` | עורך העמוד > Yoast > Advanced > "Allow search engines" · Settings > Reading > "Discourage search engines" | הגדרות SEO של העמוד |
| `status` | 404 בעמוד מקושר: לתקן את הקישור או להוסיף הפניה 301. עמוד "לא קיים" שמחזיר 200: להחזיר 404 אמיתי | "קישור שבור = לקוח שנתקע" | `not-found.tsx`, redirects ב-`next.config` | תוסף הפניות (Redirection) / Yoast Premium | Wix: URL Redirect Manager · Shopify: Navigation > URL Redirects |
| `canonical` | canonical אחד, כתובת מלאה ב-HTTPS, לעמוד עצמו | "אומר לגוגל איזו כתובת היא המקור, כדי שלא יתחלק בין כפילויות" | `alternates: { canonical }` / `metadataBase` | Yoast > Advanced > Canonical URL (לרוב אוטומטי) | API: תגית canonical (Wix/Webflow) |
| `title` | 50-60 תווים, ייחודית, מילת המפתח קרוב להתחלה, המותג בסוף ("<מה> ב<איפה> \| <מותג>") | "זה הטקסט הכחול בגוגל. כותרת שנחתכת או כפולה מורידה הקלקות" | `metadata.title` / קובץ SEO מרכזי | `wp.py seo --title` | API / עורך (`connect-*`) |
| `description` | 120-160 תווים, ייחודי, מה הלקוח מקבל + קריאה לפעולה רכה. מעובדות שאושרו | "הטקסט מתחת לכותרת בגוגל. לא משפיע על הדירוג, כן על ההקלקה" | `metadata.description` | `wp.py seo --desc` | API / עורך |
| `open_graph` | og:title, og:description, og:image (1200x630), og:url, og:type, og:locale | "מה רואים כששולחים את הלינק בוואטסאפ" | `metadata.openGraph` | Yoast > Social (אוטומטי מהכותרת והתיאור, ותמונה) | API (Wix/Webflow) / עורך |
| `lang` | `<html lang="he" dir="rtl">` | "גוגל יודע שזה עברית ולמי להציג" | `app/layout.tsx` | Settings > General > Site Language | הגדרות שפה |
| `headings` | H1 אחת (אם יש שתיים: השנייה הופכת ל-H2). רמה שמדלגת (H2→H4): משנים את התג, **לא את העיצוב** (class נשאר). כותרות בפוטר/סרגל צד: תג לא-כותרת (`<p>` / `<div>` עם אותו class) או רמה נכונה | "המבנה עוזר לגוגל ול-AI להבין מה העיקר ומה פרט" | הרכיב (Footer, Section) | `content-get/put` (בלוק heading); מהתבנית → צעד בעורך | עורך |
| `alt` | alt קצר ומדויק לתמונה שמעבירה מידע (מה רואים + הקשר), `alt=""` לדקורטיבית. **לא מנחשים מה בתמונה בלי לראות**: מורידים את התמונה ומסתכלים, או לפי הטקסט סביבה, ומסמנים "לבדיקה" אם לא בטוח | "גוגל לא רואה תמונות, הוא קורא את התיאור. ככה מופיעים גם בחיפוש תמונות" | `alt` ברכיב / ב-MDX | `wp.py alt` + בתוך התוכן | Wix/Webflow: עורך · Shopify: API |
| `schema` | Organization / LocalBusiness / ProfessionalService בעמוד הבית: name, url, logo, sameAs, ולעסק מקומי address, telephone, openingHours, areaServed. **רק עובדות מה-brief.** Service + BreadcrumbList בעמודי שירות. WebSite פעם אחת. אחרי: Rich Results Test + validator.schema.org | "תעודת זהות של העסק: מי אתם, מה אתם עושים, איפה. גוגל ומנועי AI קוראים אותה" | רכיב JSON-LD (יש באתר? משתמשים בפונקציות הקיימות) | Yoast Site representation / Rank Math Local SEO | Wix: API / Structured Data Markup · Shopify: תבנית · Webflow: Custom code |
| `geo` | לפי `geo-content.md`: פסקת תשובה, כותרות-שאלה, שאלות נפוצות, "עודכן לאחרונה". **הצעה לאישור, לא שינוי אוטומטי** | "כך ChatGPT מבין מה אתם עושים ומצטט אתכם" | ברכיבי האתר + FAQPage מאותו מערך | `content-get/put` | עורך / API של התוכן |
| `ai_bots` | בוט חיפוש של AI חסום (OAI-SearchBot, ChatGPT-User, PerplexityBot) → להסיר את החסימה, באישור. בוט אימון (GPTBot, ClaudeBot, Google-Extended) → **רק להסביר**, ההחלטה של בעל האתר. נחסם בחומת האש (403 עם ה-User-Agent האמיתי) → Cloudflare: Security > Bots > "Block AI bots" / "AI Scrapers and Crawlers" | "אם ChatGPT לא יכול להיכנס, הוא לא יכול להמליץ עליכם" | `robots.ts` | Yoast File editor / תוסף אבטחה | Wix/Shopify: robots / הגדרות Cloudflare |
| `js_content` | התוכן לא ב-HTML (SPA) → ממצא בדוח: "מנועי AI רואים עמוד ריק". הפתרון (SSR / prerender) = פרויקט למפתח | "ChatGPT לא מריץ את הקוד של האתר. מה שלא ב-HTML, הוא לא רואה" | דוח בלבד | לרוב לא קורה בוורדפרס | |
| `tech` | HTTPS, הפניה 301 מ-http ומ-www לכתובת אחת, viewport, תוכן מעורב, גודל HTML, TTFB | "אבטחה, מובייל ומהירות. גוגל מוריד אתרים שנכשלים פה" | `next.config` / הגדרות הדומיין ב-Vercel | אחסון / תוסף SSL | הגדרות הדומיין בפלטפורמה |
| `links` | עמוד שאף עמוד לא מקשר אליו → קישור מעמוד רלוונטי (בדיקה חלקית: רק העמודים שנסרקו) | "עמוד בלי קישורים הוא עמוד שגוגל ולקוחות לא מגיעים אליו" | הרכיב / התוכן | תפריט / תוכן | תפריט / תוכן |

## כללי ביצוע

- **השינוי הכי קטן שפותר.** לא משנים עיצוב, לא מרפקטרים, לא "משפרים" קוד שלא בתוכנית.
- **מקור אחד.** יש קובץ SEO מרכזי? שם. יש פונקציות Schema קיימות? משתמשים בהן.
- **תמונות OG / קבצים שנוצרים בסקריפט:** אם שינוי בטקסט מחייב לבנות מחדש קבצים (תמונות שיתוף), אומרים בתוכנית.
- **אורך בעברית:** הספים בתווים. 61 תווים הם גבול ולא אסון; מציינים כ"לשפר", לא כ"לתקן".
