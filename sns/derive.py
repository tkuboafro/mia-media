#!/usr/bin/env python3
"""公開済み記事 → Instagram（カルーセル3枚＋キャプション）と X（4言語）の下書き。
Notion の「MIA SNS投稿管理」DB に流し込むための JSON を sns_queue/ に置く（Notion キーが入れば直接登録）。"""
import json, os, re, subprocess, sys
HOME = os.path.expanduser("~/mia-media")
P = """From the article below (4 languages given), write social posts. Return ONLY JSON:
{{"instagram":{{"caption_en":"<= 2200 chars, hook first line, 3 short paragraphs, end with 'Link in bio' and 8 hashtags","slides":[{{"headline":"<= 8 words","sub":"<= 20 words"}},{{"headline":"","sub":""}},{{"headline":"","sub":""}}]}},
 "x":{{"en":"<= 240 chars + URL","nl":"<= 240 chars + URL","de":"<= 240 chars + URL","es":"<= 240 chars + URL"}}}}
Rules: no invented facts; the URL to use is {url}; tone editorial, not salesy; no 'drink responsibly' (added automatically).
ARTICLE JSON:
{art}"""
def main(meta_path):
    m = json.load(open(meta_path)); slug = m["slug"]
    art = {}
    for p in m["paths"]:
        L = p.split("/articles/")[1].split("/")[0]
        t = open(p).read(); parts = t.split("---\n", 2)
        art[L] = {"fm": parts[1], "body": parts[2][:2500]}
    base = "https://sakewire.com"
    url = f"{base}/en/{slug}/?utm_source=instagram&utm_medium=social&utm_campaign={slug}"
    r = subprocess.run(["claude", "-p", P.format(url=url, art=json.dumps(art, ensure_ascii=False)), "--output-format", "json", "--model", "sonnet", "--allowedTools", ""], capture_output=True, text=True, timeout=900)
    try: raw = json.loads(r.stdout).get("result", "")
    except Exception: raw = r.stdout
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    out = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    out["slug"] = slug; out["article_url"] = url; out["hero_prompt"] = m.get("hero_prompt")
    out["instagram"]["caption_en"] += "\n\nDrink responsibly. 18+"
    path = os.path.join(HOME, "sns_queue", f"{slug}.json")
    json.dump(out, open(path, "w"), ensure_ascii=False, indent=1); print(path)
if __name__ == "__main__":
    main(sys.argv[1])
