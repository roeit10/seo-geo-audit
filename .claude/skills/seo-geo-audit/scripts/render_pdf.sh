#!/bin/bash
# Render the HTML report to PDF with Chrome / Chromium headless (no install, no internet).
# Usage: render_pdf.sh seo-geo/report.html [seo-geo/report.pdf]
IN="$1"; OUT="${2:-${1%.html}.pdf}"
[ -f "$IN" ] || { echo "no such file: $IN"; exit 1; }
for c in "$CHROME_PATH" \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
  "$(command -v google-chrome 2>/dev/null)" "$(command -v chromium 2>/dev/null)" "$(command -v chromium-browser 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && CH="$c" && break
done
[ -n "$CH" ] || { echo "Chrome not found. Open $IN in the browser and print to PDF (Ctrl/Cmd+P)."; exit 2; }
ABS="$(cd "$(dirname "$IN")" && pwd)/$(basename "$IN")"
OUTABS="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
"$CH" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="$OUTABS" "file://$ABS" >/dev/null 2>&1
[ -s "$OUTABS" ] && echo "pdf: $OUT" || { echo "PDF failed. Open $IN and print to PDF."; exit 3; }
