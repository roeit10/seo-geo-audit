# Third-party notices

This skill adapts ideas and a small amount of code from the following MIT-licensed projects.
Thank you to their authors.

| Project | What was adapted | Where |
|---|---|---|
| [AgriciDaniel/claude-seo](https://github.com/AgriciDaniel/claude-seo) | The AI-agent table with roles (search / user / training / control) and the real user-agent strings used to test firewall access (`scripts/agentic_check.py`). Ideas: training bots and control tokens are a business choice, llms.txt reported with zero weight | `scripts/audit.py` (`AI_BOTS`) |
| [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) | Idea: detect the "Cloudflare Managed content" block in robots.txt that silently blocks AI bots. Idea: LocalBusiness / Organization JSON-LD structure | `scripts/audit.py` (`cloudflare_managed`), `references/fixes.md` |
| [seo-skills/geo-audit-skill](https://github.com/seo-skills/geo-audit-skill) | Ideas: "the script computes, the model explains"; checks that cannot be computed are excluded from the score and listed (`completeness`); filler openers that delay the answer | `scripts/audit.py` |
| [umutxyp/Seo-Promt-Master](https://github.com/umutxyp/Seo-Promt-Master) | Idea: a blocker on a key page caps the total score (here: at 60) | `scripts/audit.py` (`score`) |

## MIT License notices

Copyright (c) 2026 agricidaniel (AgriciDaniel/claude-seo)
Copyright (c) 2026 Zubair Trabzada (zubair-trabzada/geo-seo-claude)
Copyright (c) 2026 SEOmator (seo-skills/geo-audit-skill)
Copyright (c) 2026 Umut Bayraktar (@umutxyp) (umutxyp/Seo-Promt-Master)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
