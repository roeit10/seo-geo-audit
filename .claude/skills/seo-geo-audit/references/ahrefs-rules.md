# הכללים: SEO ו-GEO לפי Ahrefs (עם מקורות)

כל בדיקה ב-`audit.py` נשענת על כלל מכאן. כשמסבירים ממצא למשתמש, אפשר לצטט: "לפי Ahrefs, ...".
המקורות נבדקו בנובמבר 2026. אם מקור השתנה, הכלל שבקוד הוא מה שקובע עד שמעדכנים את שניהם.

| # | נושא | הכלל | בדיקות בסקריפט | מקור |
|---|---|---|---|---|
| 1 | מפת אתר | עד 50,000 כתובות / 50MB לקובץ. רק כתובות שמחזירות 200, אינדקסביליות וקנוניות לעצמן (בלי noindex, הפניה או canonical לעמוד אחר). priority ו-changefreq: גוגל מתעלם. lastmod אופציונלי, ורק אם אמיתי | `sitemap_exists`, `sitemap_urls_ok`, `sitemap_host`, `noindex` | ahrefs.com/blog/how-to-create-a-sitemap/ |
| 2 | robots.txt | שורת `Sitemap:`, פחות מ-500KB. גוגל לא תומך ב-Noindex / Crawl-delay / Nofollow בקובץ. user-agent רגיש לאותיות. לא לחסום CSS/JS שנדרשים לרינדור. robots לא מוציא עמוד מהאינדקס (לזה יש noindex) | `robots_exists`, `robots_sitemap_line`, `robots_valid`, `robots_blocks_site` | ahrefs.com/blog/robots-txt/ |
| 3 | בוטים של AI | לא לחסום OAI-SearchBot (החיפוש של ChatGPT), ChatGPT-User, PerplexityBot: חסימה = לא מופיעים בתשובות. GPTBot, ClaudeBot, Google-Extended = אימון מודלים, בחירה של בעל האתר. ההגדרה "Block AI training bots" של Cloudflare עלולה לחסום יותר ממה שחושבים | `ai_robots`, `ai_firewall` | ahrefs.com/aeo/technical-aeo · ahrefs.com/blog/how-to-rank-on-chatgpt/ |
| 4 | כותרות H | H1 אחת לעמוד, עד ~70 תווים, קרובה ל-title. H2/H3 מקוננות לפי הסדר. כותרות בניסוח שאלה מצוטטות ב-ChatGPT בערך פי 2 (18% מול 8.9%) | `h1_single`, `h1_length`, `heading_order`, `h2_structure`, `question_headings` | ahrefs.com/blog/h1-tag/ |
| 5 | title | ייחודי, 50-60 תווים (עד ~600 פיקסלים), מילת המפתח קרוב להתחלה, כולל את המותג | `title_present`, `title_length`, `title_unique`, `title_brand` | ahrefs.com/blog/title-tag-seo/ |
| 6 | meta description | ייחודי, ~120 תווים (מובייל) עד ~160 (~920 פיקסלים). לא משפיע על הדירוג, כן על ההקלקות | `desc_present`, `desc_length`, `desc_unique` | ahrefs.com/blog/meta-description/ |
| 7 | canonical | אחת, ב-head, כתובת מלאה ב-HTTPS, מצביעה על העמוד עצמו. היעד מחזיר 200, לא הפניה, לא noindex, בלי שרשראות. לא לשלב canonical לעמוד אחר עם noindex | `canonical` | ahrefs.com/blog/canonical-tags/ |
| 8 | Open Graph | חובה: og:title, og:type, og:image (1200x630), og:url. מומלץ: og:description, og:locale. זה מה שרואים כשמשתפים לינק בוואטסאפ ובפייסבוק | `open_graph`, `og_image_ok` | ahrefs.com/blog/open-graph-meta-tags/ |
| 9 | alt | תמונה שמעבירה מידע: תיאור קצר ומדויק, בלי "תמונה של", בלי דחיסת מילות מפתח. תמונה דקורטיבית: `alt=""`. שמות קבצים תיאוריים, דחיסה, lazy-load מתחת לקפל | `alt_missing`, `alt_quality`, `img_filenames` | ahrefs.com/blog/alt-text/ · ahrefs.com/blog/image-seo/ |
| 10 | GEO | התשובה ב-30% הראשונים של העמוד (שם 44.2% מהציטוטים). ניסוח הגדרתי ("X הוא...") מצוטט יותר (36.2% מול 20.2%). ישויות ברורות (שם העסק, השירות, המקום). כל פסקה (~200 מילה) עומדת בפני עצמה. HTML סמנטי. תוכן שמרונדר בשרת: ChatGPT לא מריץ JavaScript. TTFB מתחת ל-200ms. "עודכן לאחרונה" גלוי + dateModified, ורק בעריכה אמיתית. 76% מהציטוטים ב-AI Overviews מהטופ 10. האורך לא קובע (53% מהמצוטטים מתחת ל-1,000 מילה) | `answer_first`, `question_headings`, `faq_block`, `freshness`, `server_rendered`, `ttfb` | ahrefs.com/blog/how-to-rank-on-chatgpt/ · ahrefs.com/blog/llm-search/ · ahrefs.com/blog/fresh-content/ · ahrefs.com/blog/search-rankings-ai-citations/ |
| 11 | llms.txt | לא עכשיו: 97% מהקבצים לא מקבלים אף בקשה. רק לאתר עם תיעוד למפתחים | `llms_txt` (מידע, בלי ציון) | ahrefs.com/blog/llms-txt/ |
| 12 | Schema | JSON-LD. Organization (עם sameAs לרשתות) בכל האתר; LocalBusiness בעמוד הבית לעסק מקומי (שם, כתובת, טלפון, שעות); Article / Product / Service + BreadcrumbList לפי סוג העמוד. FAQ rich results מוגבלים מאז 2023 לאתרי ממשלה ובריאות, אבל השאלות הגלויות עדיין עוזרות ל-AI. ההשפעה של Schema על AI "מעורבת": לא מבטיחים | `jsonld_valid`, `org_schema`, `website_schema`, `page_schema` | ahrefs.com/blog/schema-markup/ · ahrefs.com/seo/glossary/local-business-schema |
| 13 | בדיקה טכנית | אינדקסביליות, 4xx/5xx, עמודים יתומים (לפחות קישור פנימי אחד), viewport למובייל, HTTP→HTTPS בהפניה 301, בלי mixed content, Core Web Vitals, עומק קליקים ≤6, גרסת host אחת (עם/בלי www), HTML מתחת ל-2MB | `pages_status`, `noindex`, `soft_404`, `host_consistency`, `internal_links`, `viewport`, `https`, `mixed_content`, `html_size`, `lang_attr` | ahrefs.com/blog/seo-issues/ |

## הציון

- כל בדיקה מקבלת 0 עד 1 (בבדיקה לפי עמודים: החלק מהעמודים שעברו). `pass` / `warn` / `fail` לפי ספים קבועים בקוד.
- ציון תחום = ממוצע משוקלל של הבדיקות בו, ×100. בדיקות `info` ו-`na` לא נספרות.
- הציון הכולל = ממוצע משוקלל של התחומים: סריקה ואינדקס 20 · כותרות ותיאורים 15 · GEO 15 · גישה ל-AI 10 · מבנה כותרות 10 ·
  תמונות 10 · Schema 10 · טכני 10.
- הספים והמשקלים בקוד (`CATEGORIES` ובכל `self.add`). משנים שם, לא בראש.

## מה הציון לא אומר

ציון 100 לא אומר "תהיו ראשונים בגוגל". הוא אומר שאין חסם טכני ושהתוכן בנוי כך שגוגל ומנועי AI יכולים להבין ולצטט אותו.
הדירוג עצמו תלוי גם בתוכן, בקישורים ובתחרות, והסקיל לא בודק אותם.
