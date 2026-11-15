# חיבור: אתר בקוד (Next.js, Astro, HTML, Gatsby, Hugo...)

**מה צריך:** תיקיית הקוד של האתר על המחשב (או גישה לריפו בגיטהאב). **למה:** כדי לערוך בעצמי את הקבצים של המטא,
מפת האתר, robots, הכותרות וה-Schema, ולבנות את האתר לבדיקה לפני שמשהו עולה. **ביטול:** אין גישה שנשארת פתוחה.
מה שנוצר הוא ענף מקומי; לא רוצים? `git switch main` ומוחקים את הענף. גיטהאב: `gh auth logout`.

---

## צעד 1: איפה הקוד

`AskUserQuestion`: **"איפה הקוד של האתר?"**
- `<תיקייה שמצאתי בפרויקט: ./site>` (אם נמצאה תיקייה עם `package.json` / `index.html` / `.git` שה-URL שלה מופיע בקוד)
- `בגיטהאב` → צעד 1א
- `אין לי את הקוד` → "בלי הקוד אפשר לבדוק ולתת דוח עם הוראות למי שבנה את האתר." פרופיל: `חיבור: אין`.

**1א, גיטהאב:**
1. `gh auth status`. לא מחובר → "פותחים טרמינל ומריצים `gh auth login`, בוחרים GitHub.com ו-Login with a web browser.
   כתוב לי 'התחברתי'." (התקנה: `brew install gh` במק, או https://cli.github.com.)
2. `gh repo list --limit 50` → `AskUserQuestion` עם הריפו שהשם שלו הכי דומה לדומיין (עד 3) + Other.
3. `gh repo clone <owner/repo> ./site` (או שם התיקייה שהמשתמש בחר). **לא** בתוך תיקייה של ריפו אחר.

**בדיקה:** `git -C <תיקייה> status` עובד, ו-`git -C <תיקייה> remote -v` מראה את הריפו. מציגים בשורה אחת.

## צעד 2: מה ה-framework ואיפה מה

קוראים `package.json` (dependencies + scripts) ומחפשים את הקבצים. **בודקים בפועל** עם `ls`/`grep`, לא מניחים:

| framework | מטא (title, description, canonical, OG) | sitemap | robots | Schema | build / הרצה מקומית |
|---|---|---|---|---|---|
| **Next.js, App Router** (`app/`) | `export const metadata` / `generateMetadata` ב-`app/**/page.tsx` ו-`layout.tsx`. `metadataBase` ב-layout הראשי. לפעמים קובץ מרכזי (`lib/seo.ts`) | `app/sitemap.ts` (או `public/sitemap.xml`) | `app/robots.ts` (או `public/robots.txt`) | `<script type="application/ld+json">` ברכיב / layout | `npm run build` · `npx next start -p 3999` |
| **Next.js, Pages Router** (`pages/`) | `<Head>` מ-`next/head` או `next-seo` | `next-sitemap` (בקונפיג) או `public/sitemap.xml` | `public/robots.txt` | בתוך `<Head>` | `npm run build` · `npx next start -p 3999` |
| **Astro** | ה-layout (`src/layouts/*.astro`) עם props לכל עמוד | `@astrojs/sitemap` ב-`astro.config` | `public/robots.txt` | ב-layout | `npm run build` · `npx astro preview --port 3999` |
| **HTML סטטי** | ה-`<head>` בכל קובץ `.html` | `sitemap.xml` בשורש | `robots.txt` בשורש | ב-`<head>` | אין build · `python3 -m http.server 3999` |
| **Gatsby / Hugo / Nuxt / אחר** | לפי התיעוד שלהם (חיפוש ברשת אם לא ברור) | | | | לפי `scripts` ב-package.json |

**אתר שהוא אפליקציית JavaScript בלבד** (React/Vite בלי רינדור בשרת, `detect.json` → "React/Vite (SPA)"): ה-HTML כמעט ריק,
ו-ChatGPT לא מריץ JavaScript. אומרים את זה בדוח כממצא מרכזי (`server_rendered`), ולא מנסים "לתקן" במסגרת הסקיל
(זה מעבר ל-SSR/prerender, פרויקט של מפתח).

**ההעלאה לאוויר:** מזהים לפי `detect.json` (`hosting`) + קבצים (`vercel.json`, `netlify.toml`, `.github/workflows`):
- **Vercel / Netlify מחוברים לגיט:** push לענף הראשי = עלייה לאתר החי. push לענף אחר = גרסת preview עם כתובת משלה
  (Vercel: מופיעה תחת Deployments; Netlify: deploy-preview, עם noindex). מקור: vercel.com/docs/git · docs.netlify.com/site-deploys/overview/
- **אחר (FTP, שרת):** ההעלאה ידנית אצל המשתמש. הסקיל רק מכין את הענף.

**בדיקה:** מריצים את ה-build פעם אחת **לפני** שינויים (בשלב 3, לא באשף, כי זה לוקח זמן). באשף רק מוודאים שיש
`node_modules` או שאפשר `npm ci`, ורושמים את הפקודות בפרופיל.

---

## ביצוע (שלב 3 בסקיל)

1. `git status --porcelain`. **יש שינויים שלא נשמרו?** עוצרים: "יש שינויים שלא שמורים בתיקייה. לא אגע בהם.
   תשמור אותם (commit) או תגיד לי להמשיך בענף נפרד מעליהם." לא עושים stash ולא reset בלי אישור.
2. ענף: `git switch -c seo-geo/<YYYY-MM-DD>` (קיים? `-<HHMM>` בסוף).
3. עורכים **רק** את מה שבתוכנית. שומרים על הסגנון של הקוד הקיים (קובץ SEO מרכזי? עורכים שם, לא בעמוד).
   אם יש באתר קובץ מקור אחד לכותרות ותיאורים (כמו `lib/seo.ts`), כל שינוי מטא נעשה שם.
4. build: `npm run build` (או מה שבפרופיל). נכשל בגלל שינוי שלנו → מתקנים. לא בטוחים שזה מאיתנו? בודקים את main
   בתיקייה נפרדת (`git worktree add /tmp/seo-geo-base main`, build שם). גם שם נכשל → הבעיה הייתה לפני; אומרים ועוצרים.
5. `git add <הקבצים ששונו>` + `git commit -m "seo-geo: <תקציר>"`. **לא push.**
6. `git diff main --stat` לדוח.

## ציון אחרי (שלב 4)

```bash
# מריצים את הגרסה הבנויה ברקע, על פורט פנוי
npx next start -p 3999 > /tmp/seo-geo-server.log 2>&1 &      # Next.js (Astro: npx astro preview --port 3999)
# מחכים שיענה (עד 30 שניות)
for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}" http://localhost:3999/ | grep -q 200 && break; sleep 1; done
python3 SKILL/scripts/audit.py --url <האתר החי> --fetch-base http://localhost:3999 --inherit-live seo-geo/audit-before.json \
  --key-pages "..." --brand "..." --out seo-geo/audit-after.json
# עוצרים את השרת
pkill -f "next start -p 3999"
```

הבדיקה המקומית משתמשת בכתובות של האתר החי (canonical, sitemap), אז ההשוואה הוגנת. בחזרה על roei.ai: אתר חי
וגרסה מקומית בלי שינויים קיבלו את אותו ציון בדיוק.

## העלאה (שלב 6, רק אחרי "מאשר" לשאלה "להעלות לאתר החי?")

1. `git remote -v` → יש remote ל-push? (`no-push` / שגיאה = המשתמש חסם push בכוונה. אומרים ועוצרים.)
2. ה-flow של המשתמש (מהפרופיל):
   - **Vercel/Netlify מ-main:** `git switch main && git merge --ff-only seo-geo/<תאריך> && git push origin main`.
     ff-only נכשל? לא מכריחים. אומרים, ומציעים push של הענף בלבד + Pull Request (`gh pr create`).
   - **רוצים לראות קודם:** `git push -u origin seo-geo/<תאריך>` → כתובת preview (Vercel/Netlify), בלי לגעת באתר החי.
3. אחרי push ל-main: מחכים ל-deploy (`gh run list` / `vercel ls` אם מותקן, או בודקים שהאתר החי מציג את השינוי),
   ואז `audit.py` על האתר החי → `seo-geo/audit-live.json`.

## תקלות

| מה קרה | מה עושים |
|---|---|
| `npm ci` נכשל | גרסת Node (`node -v`) מול `engines` ב-package.json. אומרים מה חסר. לא מעדכנים חבילות |
| build נכשל על משתני סביבה (Supabase, API) | `.env.example` → מבקשים מהמשתמש `.env.local` עם ערכי פיתוח, או בודקים אם יש fallback בקוד. לא ממציאים מפתחות |
| הפורט תפוס | פורט אחר (4010, 4011) |
| `gh: command not found` | התקנה (`brew install gh`) או clone ידני: `git clone https://github.com/<owner>/<repo>.git` |
| ענף ראשי הוא `master` | משתמשים בשם האמיתי מ-`git symbolic-ref refs/remotes/origin/HEAD` |
