#!/usr/bin/env python3
"""fal.ai で記事用のイメージ画像を作る（引用できる素材が無い見出しの穴埋め専用）。
方針（久保さん 2026-09-24）: 生成は最小限。実在の銘柄・ラベル・人物・特定の建物は描かせない。
生成画像には必ず「イメージ画像（AI生成）」と表示する。残高不足などで失敗したら None を返し、記事は画像なしで進む。"""
import json, os, sys, time, urllib.request, urllib.error

HOME = os.path.expanduser("~/mia-media")
MODEL = os.environ.get("FAL_IMAGE_MODEL", "fal-ai/flux-pro/v1.1")  # 約 $0.04/枚
CREDIT_JA = "イメージ画像（AI生成）"
GUARD = ("editorial photograph, natural light, shallow depth of field, no text, no letters, no logos, "
         "no labels, no brand names, no recognizable people, no faces")

def _key():
    k = os.environ.get("FAL_KEY")
    if k: return k
    for line in open(os.path.join(HOME, "secrets.env")):
        if line.startswith("FAL_KEY="): return line.split("=", 1)[1].strip()
    return None

class FalError(Exception): pass

def generate(prompt, size="landscape_16_9"):
    """prompt: 英語。成功時は画像URL（fal CDN）を返す。"""
    key = _key()
    if not key: raise FalError("FAL_KEY がありません")
    body = json.dumps({"prompt": f"{prompt}. {GUARD}", "image_size": size, "num_images": 1,
                       "safety_tolerance": "2", "output_format": "jpeg"}).encode()
    req = urllib.request.Request(f"https://fal.run/{MODEL}", data=body, method="POST",
                                 headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r: out = json.load(r)
    except urllib.error.HTTPError as e:
        raise FalError(f"{e.code} {e.read()[:200].decode(errors='replace')}")
    imgs = out.get("images") or []
    if not imgs: raise FalError(f"画像が返らない: {str(out)[:200]}")
    return imgs[0]["url"]

def try_generate(prompt, size="landscape_16_9"):
    try: return generate(prompt, size)
    except FalError as e:
        print(f"[genimg] 生成できず: {e}", file=sys.stderr); return None

def rehost(url, slug, n):
    """公開時に fal の URL を自サイト配下へ保存し直す（fal 側の保持期間に依存しない）。戻り値はサイト内パス。"""
    d = os.path.join(HOME, "site", "public", "img", "gen"); os.makedirs(d, exist_ok=True)
    name = f"{slug}-{n}.jpg"
    urllib.request.urlretrieve(url, os.path.join(d, name))
    return f"/img/gen/{name}"

if __name__ == "__main__":
    print(try_generate(" ".join(sys.argv[1:]) or "a glass of clear shochu on the rocks on a wooden counter"))
