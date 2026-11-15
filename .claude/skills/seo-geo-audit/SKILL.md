---
name: seo-geo-audit
description: Audit a business website for classic SEO and for GEO (being cited by ChatGPT, Claude, Perplexity and Google AI Overviews), then fix it on the site's own platform. A deterministic Python checker crawls the site and scores 8 categories 0-100 (crawl and indexing, AI-crawler access, titles and descriptions, heading structure, image alt text, structured data, GEO content, technical), following Ahrefs' rules with sources. First run is a short onboarding that detects the platform (code / Next.js, WordPress, Wix, Shopify, Webflow, Framer, Squarespace), walks the owner through connecting it step by step, confirms key pages and an owner-approved business facts brief, and saves a profile. Then it shows a numbered plan and waits for "מאשר" before any change: code sites are edited on a git branch and built locally (never pushed without a second "מאשר"), WordPress through the REST API with a backup first, Wix / Shopify / others through their API or Composio when possible, otherwise paste-ready snippets and click-by-click steps. Page copy is never rewritten automatically: GEO blocks (answer-first intro, question headings, FAQ, last-updated) are proposed as diffs for approval. Ends with a before/after score and a branded Hebrew HTML + PDF report with a this-week / this-month / this-quarter plan. Use when the user says "תבדוק לי את ה-SEO של האתר", "בדיקת SEO", "SEO ו-GEO", "שהאתר יופיע ב-ChatGPT", "למה גוגל לא מוצא אותי", "תתקן לי את ה-SEO", "מפת אתר", "robots.txt", "תגיות מטא", "audit my website SEO", "GEO audit", "fix my site's SEO", or "/seo-geo-audit".
---

# בדיקת SEO ו-GEO לאתר, ותיקון על הפלטפורמה שלכם

הסקיל עושה שלושה דברים, בסדר הזה:

1. **בודק.** סקריפט Python סורק את האתר ומחשב ציון 0-100 בשמונה תחומים. אותו אתר = אותו ציון, בכל ריצה.
   קלוד לא מחשב ציונים בראש, הוא רק קורא את התוצאה ומסביר אותה.
2. **מתקן, אחרי "מאשר".** על הפלטפורמה של האתר: קוד, וורדפרס, Wix, Shopify ועוד. בפעם הראשונה אשף מזהה
   על מה האתר בנוי ומחבר אותו צעד אחר צעד.
3. **מדווח.** ציון לפני ואחרי, מה תוקן, ומה נשאר: השבוע, החודש, ברבעון. דוח HTML ו-PDF בעברית.

**SEO** = שגוגל ימצא את האתר ויציג אותו טוב. **GEO** = שמנועי AI (ChatGPT, Claude, Perplexity, התשובות של גוגל)
יקראו את האתר ויצטטו אותו. GEO נשען על SEO: 76% מהציטוטים ב-AI Overviews מגיעים מעמודים שכבר בטופ 10.

---

## הכללים שלא נשברים

1. **שום שינוי באתר לפני "מאשר".** עד האישור: קריאה בלבד. האישור חל רק על מה שהיה בתוכנית.
2. **לא מעלים לאוויר בלי "מאשר" שני.** באתר בקוד: עובדים בענף (branch) מקומי, בונים, ועוצרים. push או deploy
   רק אחרי שהמשתמש כתב "מאשר" לשאלה הנפרדת "להעלות לאתר החי?".
3. **גיבוי לפני כתיבה.** קוד: ענף + commit לפני שנוגעים. וורדפרס: `wp.py backup` לכל עמוד לפני שינוי.
   פלטפורמה אחרת: שומרים את הערכים הקיימים ב-`seo-geo/backup/` לפני הכתיבה.
4. **לא ממציאים עובדות.** שם, שירותים, אזור, טלפון, כתובת, שעות, מחירים: רק מה שבעל העסק אישר ב-brief (בפרופיל).
   מה שלא אושר לא נכנס ל-Schema, לתיאורים או לשאלות הנפוצות. חסר? כותבים "לבדיקה" ושואלים.
5. **לא משכתבים תוכן לבד.** פסקת פתיחה, כותרות-שאלה, שאלות נפוצות, "עודכן לאחרונה": מוצעים כהצעה עם "היה / עכשיו",
   בקול של העסק, ונכנסים רק אחרי אישור. תאריך "עודכן" = תאריך עריכה אמיתית בלבד.
6. **הציון מהסקריפט בלבד.** לא מעגלים, לא משפרים "בערך". בדיקה שלא רצה (אתר לא זמין, עמוד חסום) נאמרת בראש הדוח.
7. **סודות בקובץ, לא בצ'אט.** סיסמת אפליקציה, טוקן API: נכנסים ל-`.env` שהמשתמש עורך בעצמו (`open .env`).
   לא מבקשים להדביק בצ'אט, לא מדפיסים, ו-`.env` תמיד ב-`.gitignore`. בפרופיל נשמרת **שיטת** החיבור, לא הסוד.
8. **לא חוסמים ולא משחררים בוטים של AI בלי לשאול.** חסימת בוטים של אימון (GPTBot, Google-Extended) היא בחירה של בעל
   האתר. חסימת בוטים של חיפוש (OAI-SearchBot, ChatGPT-User, PerplexityBot) מעלימה אותו מתשובות AI, ואומרים את זה.
9. **בלי מקף ארוך** בשום טקסט. מונח באנגלית מוסבר במשפט אחד בפעם הראשונה.
10. **כל תשובה בעברית, תמיד.** גם אחרי הודעה קצרה ("מאשר", "נכון"), גם בתיקון, בדוח הסיום ובהודעת שגיאה.
    שמות קבצים, פקודות ומונחים טכניים נשארים כמו שהם; כל השאר עברית. התיקון מוצג עם המילים "היה:" ו"עכשיו:", לא Before/Now.
11. **קבצים זמניים רק ב-`seo-geo/tmp/`.** לא בתיקייה שמעל הפרויקט, לא בתוך תיקיית הקוד, לא ב-`/tmp`.

> **איך שואלים (כלל קבוע):** כל שאלה למשתמש נשאלת דרך הכלי `AskUserQuestion`: 2-4 אפשרויות קונקרטיות,
> לשאלה פתוחה דוגמאות כאפשרויות ו-"Other". אישורים בצורת "נכון" / "לתקן". המשתמש כבר ענה בהודעה? לא שואלים שוב.
> החריגים: ה"מאשר" והתיקון במשפט אחד נכתבים חופשי בצ'אט. (אם `AskUserQuestion` לא זמין, למשל בהרצה לא אינטראקטיבית,
> שואלים את אותה שאלה כרשימה ממוספרת בטקסט ועוצרים.)

---

## איפה זה חי

| מה | איפה |
|---|---|
| העסק, הקול | `context/business.md` (מהמשרד הדיגיטלי) · `CLAUDE.md` · `context/voice.md` |
| **הפרופיל** (נוצר באשף, פעם אחת) | `context/seo-geo-audit.md` |
| כל הפלטים | `seo-geo/` בתיקייה: `detect.json`, `audit-before.json`, `audit-after.json`, `plan.md`, `geo-proposals.md`, `notes.json`, `report.html`, `report.pdf`, `backup/` |
| סודות (אם צריך) | `.env` בתיקייה (בגיטיגנור) |
| הסקריפטים | `scripts/audit.py` (בדיקה וציון) · `scripts/detect.py` (זיהוי פלטפורמה) · `scripts/report.py` + `scripts/render_pdf.sh` (דוח) · `scripts/wp.py` (וורדפרס) |
| הכללים | `references/ahrefs-rules.md` (כל כלל + מקור) · `references/fixes.md` (איך מתקנים כל בדיקה, לפי פלטפורמה) · `references/geo-content.md` |
| חיבור | `references/setup.md` (האשף) · `references/connect-code.md` · `connect-wordpress.md` · `connect-wix.md` · `connect-shopify.md` · `connect-other.md` |

`SKILL` = התיקייה של הסקיל הזה (`.claude/skills/seo-geo-audit`). פקודות רצות מתיקיית הפרויקט.

---

## שלב 0, בדיקת מצב (בלי לשאול)

1. **פרופיל:** קיים `context/seo-geo-audit.md`? מציגים שורה אחת ("האתר: X · פלטפורמה: Y · חיבור: Z · N עמודים מרכזיים")
   וממשיכים לשלב 1. אין → **האשף**, `references/setup.md`, ואחריו ממשיכים ישר לשלב 1.
2. **החיבור עדיין עובד?** לפי הפרופיל: קוד → התיקייה קיימת ו-`git status` עובד; וורדפרס → `python3 SKILL/scripts/wp.py check`;
   Composio → `composio connections list --toolkit <toolkit>`. לא עובד → אומרים מה נשבר, ואת הצעד מ-`connect-<platform>.md`.
   בלי חיבור אפשר לבדוק ולדווח, אבל לא לתקן; אומרים את זה ושואלים אם להמשיך כ"דוח בלבד".

## שלב 1, בדיקה

```bash
python3 SKILL/scripts/audit.py --url <האתר> --key-pages "<נתיבים מהפרופיל>" --brand "<שם המותג>" --out seo-geo/audit-before.json
```

עד 30 עמודים, מכבד robots.txt, בלי מפתחות ובלי שירות בתשלום. אתר רגיל: פחות מדקה.
קוראים את `seo-geo/audit-before.json` (לא רק את הפלט הקצר) ומציגים:

```
הציון: <X>/100
<תחום>: <ציון> · <תחום>: <ציון> ...  (שמונה תחומים, מהנמוך לגבוה)

מה מצאתי (הכי חשוב קודם):
1. <בעיה במילים של בעל עסק> - <למה זה חשוב לעסק, משפט אחד> (<כמה עמודים>)
...
מה כבר טוב: <2-3 דברים שעברו, למשל "ChatGPT ו-Claude יכולים לקרוא את האתר, בדקתי עם הבוט האמיתי">
```

- סדר: `fail` לפני `warn`, ובתוך כל אחד לפי המשקל. בדיקה עם `evidence` → דוגמה אחת או שתיים, לא רשימה.
- **אל תמציא בעיות.** אתר חזק? אומרים "האתר במצב טוב", ומראים את מה שכן נמצא. גם 3 ממצאים אמיתיים זה סיפור.
- בדיקה שלא רצה או עמוד שלא נטען → שורה ראשונה, לפני הציון.

## שלב 2, תוכנית

מכינים את `seo-geo/plan.md` ומציגים אותו. רשימה ממוספרת, בשני חלקים:

**א. תיקונים טכניים** (לכל אחד: מה, איפה בדיוק (קובץ / עמוד / שדה), היה → עכשיו, ולמה זה טוב לעסק בשורה אחת).
איך מתקנים כל בדיקה בכל פלטפורמה: `references/fixes.md`.

**ב. הצעות תוכן (GEO)**: נכתבות ל-`seo-geo/geo-proposals.md` לפי `references/geo-content.md`, עם "היה / עכשיו" לכל עמוד,
רק מעובדות שאושרו ב-brief ובקול של העסק. בתוכנית: שורה לכל הצעה + הפניה לקובץ.

**ג. מה לא נוגעים ולמה** (למשל "Google Business Profile: רק המלצה בדוח", "מהירות: דורש מפתח, לא בסקיל הזה").

באתר בקוד, השורה לפני האחרונה: "אעבוד בענף נפרד `seo-geo/<תאריך>`, אבנה את האתר מקומית ואבדוק. שום דבר לא עולה לאתר החי בשלב הזה."
השורה האחרונה, מילה במילה:
**"משהו לתקן? כתוב לי במשפט אחד. אם הכל נכון, כתוב מאשר."**
ואז **עוצרים ומחכים.**

**תיקון:** המשתמש כתב תיקון ("בלי השאלות הנפוצות בעמוד הבית", "תקצר את הכותרת")? מעדכנים ומציגים **רק מה שהשתנה**:
מספר הסעיף, ושתי שורות בדיוק: **"היה:"** ו-**"עכשיו:"**. ואז שוב השורה האחרונה, ועוצרים.

## שלב 3, ביצוע אחרי "מאשר"

מבצעים **בדיוק את התוכנית, לא יותר**, לפי הפלטפורמה בפרופיל:

| פלטפורמה | איך |
|---|---|
| **קוד** | `references/connect-code.md`, "ביצוע": עץ עבודה נקי → ענף `seo-geo/<תאריך>` → עריכת הקבצים → build → commit בענף. **לא push.** |
| **וורדפרס** | `wp.py backup` לכל עמוד → `wp.py seo` / `wp.py alt` / `content-get` + עריכה + `content-put` → קריאה חוזרת לאימות |
| **Wix / Shopify / Webflow** | דרך ה-API או Composio לפי `connect-<platform>.md`: גיבוי ערכים → כתיבה → קריאה חוזרת. מה שאי אפשר דרך API → צעדים בעורך |
| **בלי חיבור לכתיבה** | קטעי קוד מוכנים להדבקה + צעד אחר צעד בעורך, לכל תיקון. נכנסים לדוח (`snippets` ב-notes.json) |

- כל פעולה שנכשלה פותחת את הדוח: `**לא בוצע: <מה>.** <מה חזר>. מה לעשות: <צעד אחד>.` לא כותבים "בוצע" על מה שלא אומת.
- באתר בקוד: build שנכשל = לא ממשיכים. מתקנים רק מה שהסקיל שבר; שגיאה שהייתה לפני → אומרים ועוצרים.

## שלב 4, ציון אחרי

- **קוד:** אחרי build מוצלח מריצים את האתר מקומית ובודקים אותו כאילו הוא החי (`connect-code.md`, "ציון אחרי"):
  ```bash
  python3 SKILL/scripts/audit.py --url <האתר> --fetch-base http://localhost:<port> --inherit-live seo-geo/audit-before.json \
    --key-pages "..." --brand "..." --out seo-geo/audit-after.json
  ```
  בדיקות שאפשר למדוד רק באתר החי (HTTPS, הפניות, חומת אש, מהירות) נלקחות מהריצה הקודמת, והדוח אומר את זה.
- **וורדפרס / API:** השינוי כבר באוויר → בודקים שוב את האתר החי (`--out seo-geo/audit-after.json`). מטמון (cache)
  של האתר עלול להראות ערך ישן; אם ערך שנכתב לא מופיע, אומרים שזה מטמון ומציעים לנקות אותו.
- **רק קטעים להדבקה:** אין "אחרי". בדוח: "אחרי שתדביקו, תריצו שוב ותקבלו ציון אחרי".
- השוואה: `python3 SKILL/scripts/audit.py --compare seo-geo/audit-before.json seo-geo/audit-after.json`.

## שלב 5, דוח

1. כותבים `seo-geo/notes.json` לפי `references/notes-json.md` (סיכום לבעל העסק, מה תוקן, תוכנית השבוע/החודש/הרבעון,
   הצעות GEO והמצב שלהן, Google Business Profile, קטעים להדבקה).
2. `python3 SKILL/scripts/report.py --before seo-geo/audit-before.json --after seo-geo/audit-after.json --notes seo-geo/notes.json --out seo-geo/report.html`
3. `bash SKILL/scripts/render_pdf.sh seo-geo/report.html` → `seo-geo/report.pdf`. ואז `open seo-geo/report.html`.

ובצ'אט, קצר:

```
הציון: <לפני> → <אחרי> (<בנייה מקומית / האתר החי>)
מה תוקן: <N> · מה נשאר: השבוע <a>, החודש <b>, ברבעון <c>
בשפה פשוטה: <2-3 שורות לבעל העסק>

מה לבדוק עכשיו:
- הדוח: seo-geo/report.html (וה-PDF לידו)
- <קוד: git diff בענף / האתר המקומי ב-localhost> · <וורדפרס: לינק לעמוד ששונה>
- Rich Results Test: <לינק מה-JSON>, אחרי שזה באוויר
```

## שלב 6, העלאה לאוויר (רק באתר בקוד, רק אם ביקשו)

שואלים בשורה אחת: **"להעלות את השינויים לאתר החי? כתוב מאשר. אחרת הם נשארים בענף המקומי, ואפשר להעלות מתי שתרצה."**
רק אחרי "מאשר": לפי `connect-code.md`, "העלאה" (push של הענף, ומיזוג ל-main רק אם זה ה-flow של המשתמש, למשל Vercel
שמעלה מ-main). אחרי ההעלאה: בודקים שהאתר החי עונה 200, ומריצים שוב את `audit.py` על האתר החי כשה-deploy מסתיים.

---

## גבולות תפקיד

אתר אחד, ריצה אחת. הסקיל לא: מנהל קמפיין קישורים, בודק מתחרים (דורש API בתשלום), מתחבר ל-Search Console בתוך הריצה,
משפר מהירות (Core Web Vitals) מעבר להמלצה, יוצר עמודי ערים, כותב מאמרים חדשים, או נוגע ב-Google Business Profile
(רק ממליץ). llms.txt לא נוצר: לפי Ahrefs, 97% מהקבצים האלה לא מקבלים בקשות. נראות ב-AI לוקחת בדרך כלל 14-21 יום ויותר,
ואומרים את זה בדוח, בלי הבטחות.
