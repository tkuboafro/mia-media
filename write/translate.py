#!/usr/bin/env python3
"""承認済みの日本語原稿 → EN/NL/DE/ES。忠実な翻訳（内容の追加・削除なし）。`claude -p`。"""
import json, re, subprocess, sys
LANGS = {"en": "English (British spelling)", "nl": "Dutch", "de": "German", "es": "Spanish (European)"}
P = """Translate the approved Japanese article below into {langs}. Faithful translation: keep every fact, number and name; do not add or drop information; adapt idioms naturally for each audience. Keep the Markdown structure (## headings and paragraphs). Lines of the form [[youtube:...]], [[image:URL|caption|credit]], [[x:...]], [[instagram:...]] are media embeds: keep them on their own line, keep the URL and credit unchanged, and translate only the caption text. Romanise Japanese proper nouns with macrons omitted (e.g. Dogo, Ehime). Return ONLY JSON:
{{"en":{{"title":"","description":"","body_md":""}},"nl":{{...}},"de":{{...}},"es":{{...}}}}
where description = the lead sentence (max 160 chars).

TITLE: {title}
LEAD: {lead}
BODY:
{body}"""
def translate(ja, model="opus"):
    p = P.format(langs=", ".join(f"{k} ({v})" for k, v in LANGS.items()), title=ja["title"], lead=ja["lead"], body=ja["body_md"])
    r = subprocess.run(["claude", "-p", p, "--output-format", "json", "--model", model, "--allowedTools", ""], capture_output=True, text=True, timeout=1200)
    try: raw = json.loads(r.stdout).get("result", "")
    except Exception: raw = r.stdout
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    out = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    for L in LANGS:
        assert out.get(L, {}).get("title") and out[L].get("body_md"), f"missing {L}"
    return out
if __name__ == "__main__":
    meta = json.load(open(sys.argv[1])); print(json.dumps(translate(meta["ja"]), ensure_ascii=False)[:500])
