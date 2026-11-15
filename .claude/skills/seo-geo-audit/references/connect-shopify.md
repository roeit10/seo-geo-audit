# חיבור: Shopify

**מה צריך:** חיבור דרך Composio (הכי פשוט) **או** אפליקציה פרטית בחנות (Dev Dashboard) עם הרשאות תוכן ומוצרים.
**למה:** כדי לכתוב בעצמי כותרות ותיאורים לגוגל של מוצרים, קולקציות, עמודים ופוסטים, ואת robots.txt של התבנית.
**ביטול:** Composio: למחוק את החיבור. אפליקציה: **Settings > Apps** > תפריט ליד האפליקציה > **Uninstall**
(ולמחיקה מלאה: Dev Dashboard > האפליקציה > **Settings > Delete app**).

Shopify מייצר לבד את `/sitemap.xml` ואי אפשר לערוך אותו. robots.txt נערך דרך קובץ בתבנית (`robots.txt.liquid`).

---

## דרך 1 (מומלצת): Composio

1. `composio connections list --toolkit shopify`. ACTIVE → בדיקה.
2. אין → `AskUserQuestion`: "לחבר את Shopify דרך Composio? נפתח חלון, מזינים את כתובת החנות ומאשרים." → `composio link shopify`.
3. **בדיקה (קריאה):** `SHOPIFY_LIST_PAGES` (עמוד אחד) + מוצר אחד. מציגים שמות, בלי לשנות.

## דרך 2: אפליקציה פרטית (Dev Dashboard)

מאז 1.1.2026 אי אפשר ליצור "custom app" ישן מתוך הניהול. הדרך היום (מקור: help.shopify.com/en/manual/apps/install-setup-apps ·
changelog.shopify.com/posts/legacy-custom-apps-can-t-be-created-after-january-1-2026):

1. ניהול החנות > **Settings** > **Apps** > **Develop apps** > **Build apps in Dev Dashboard**.
2. **Create app** > שם: `seo-geo-audit` > **Create**.
3. ב-**Access** מוסיפים הרשאות: `read_content`, `write_content` (עמודים ובלוג), `read_products`, `write_products` (מוצרים וקולקציות),
   ורק אם רוצים לגעת ב-robots.txt: `read_themes`, `write_themes`. **Release** ושוב **Release**.
4. חזרה ל-**Settings > Apps > Develop apps > Build apps in Dev Dashboard** > האפליקציה > **Installs** > **Install app** > **Install**.
5. מעתיקים **Client ID** ו-**Client secret** לקובץ `.env` (`SHOPIFY_STORE=<name>.myshopify.com`, `SHOPIFY_CLIENT_ID=...`,
   `SHOPIFY_CLIENT_SECRET=PASTE_HERE`), `open .env`.
6. קלוד מקבל טוקן (תקף 24 שעות, מבקשים מחדש בכל ריצה):
   `POST https://$SHOPIFY_STORE/admin/oauth/access_token` עם `grant_type=client_credentials`, `client_id`, `client_secret`.
   עובד רק כשהאפליקציה והחנות באותו ארגון Shopify. צריך תפקיד **App developer**.
   (מקור: shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant)

## מה כותבים ואיך (שלב 3)

**תמיד קודם:** קוראים את הערכים הקיימים (כותרת ותיאור לגוגל) ושומרים ב-`seo-geo/backup/shopify-<תאריך>.json`.

| תיקון | API (Admin GraphQL) | בניהול (אם אין חיבור) |
|---|---|---|
| כותרת + תיאור של מוצר | `productUpdate` עם `seo { title, description }` | מוצר > למטה **Search engine listing** > **Edit** |
| כותרת + תיאור של עמוד / פוסט / קולקציה | metafields `global.title_tag` ו-`global.description_tag` (`single_line_text_field`), `metafieldsSet` | אותו **Search engine listing** בעורך העמוד |
| להסתיר עמוד מגוגל | metafield `seo.hidden` = 1 | |
| robots.txt | קובץ בתבנית: `templates/robots.txt.liquid` (צריך `write_themes`). **רק על עותק של התבנית, לא על התבנית החיה**, ופרסום באישור | **Online Store > Themes > ... > Edit code** > Add a new template > robots |
| alt לתמונות מוצר | `productUpdateMedia` / `fileUpdate` עם `alt` | מוצר > לחיצה על התמונה > **Add alt text** |
| Schema | רוב התבניות כבר כוללות Product schema. Organization: בקוד התבנית (`theme.liquid`) → צעדים בדוח, לא כתיבה אוטומטית לתבנית החיה | |

מקורות: shopify.dev/docs/apps/build/marketing/optimize-storefront-seo · shopify.dev/docs/api/admin-graphql/latest/input-objects/SEOInput ·
shopify.dev/docs/storefronts/themes/seo/robots-txt · help.shopify.com/en/manual/promoting-marketing/seo/find-site-map

אחרי כל כתיבה: קוראים שוב ומשווים. ואז `audit.py` על האתר החי.
