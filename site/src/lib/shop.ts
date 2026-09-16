// shop.made-in-akita.com の公開 products.json をビルド時に取得（トークン不要）。
// 記事内モジュール③・右レール⑤の商品カードに使う。売り切れは除外（久保さん決定 2026-09-16）。
export type Product = { handle: string; title: string; type: string; tags: string[]; price: number; image: string | null; available: boolean; };
const SHOP = "https://shop.made-in-akita.com";
let cache: Product[] | null = null;

export async function allProducts(): Promise<Product[]> {
  if (cache) return cache;
  try {
    const r = await fetch(`${SHOP}/products.json?limit=250`);
    const j = await r.json();
    cache = (j.products as any[]).map((p) => ({
      handle: p.handle, title: p.title, type: p.product_type || "", tags: p.tags || [],
      price: Math.min(...p.variants.map((v: any) => parseFloat(v.price))),
      image: p.images?.[0]?.src ? p.images[0].src.replace(/(\.[a-z]+)(\?.*)?$/i, "_600x$1$2") : null,
      available: p.variants.some((v: any) => v.available),
    })).filter((p) => p.available);
  } catch (e) { cache = []; }
  return cache!;
}

const CAT: Record<string, string> = { "ワイン": "Wine", "ビール": "Beer", "ジン": "Gin" };
/** 記事の分類・タグ・地域から「この記事の味わい方」に出す商品を選ぶ。秋田以外の記事でも同じスタイルを秋田で提案する。 */
export async function pickFor(a: { category?: string; tags?: string[]; title?: string; description?: string; akita?: boolean }, n = 2, seed = ""): Promise<Product[]> {
  const all = await allProducts();
  const text = `${a.title ?? ""} ${a.description ?? ""} ${(a.tags ?? []).join(" ")}`.toLowerCase();
  let want = "Sake";
  if (/wine|wijn|wein|vino|ワイン/.test(text)) want = "Wine";
  else if (/beer|bier|cerveza|ビール/.test(text)) want = "Beer";
  else if (/\bgin\b|ジン/.test(text)) want = "Gin";
  let pool = all.filter((p) => p.tags.includes(want) || p.type.toLowerCase().includes(want.toLowerCase()));
  if (want === "Sake") {
    // 等級が本文に出ていれば合わせる（大吟醸 > 吟醸 > 純米）
    const grade = /daiginjo|大吟醸/.test(text) ? "daiginjo" : /ginjo|吟醸/.test(text) ? "ginjo" : /junmai|純米/.test(text) ? "junmai" : "";
    if (grade) { const g = pool.filter((p) => p.title.toLowerCase().includes(grade)); if (g.length >= n) pool = g; }
    // 180ml のお試しを1本混ぜる（価格の入口）
    const trial = pool.filter((p) => p.tags.includes("Trial")); const full = pool.filter((p) => !p.tags.includes("Trial"));
    const h = [...seed].reduce((s, c) => s + c.charCodeAt(0), 0);
    const out: Product[] = [];
    if (trial.length) out.push(trial[h % trial.length]);
    if (full.length) out.push(full[(h * 7) % full.length]);
    while (out.length < n && pool.length) { const p = pool[(h + out.length * 13) % pool.length]; if (!out.includes(p)) out.push(p); else break; }
    return out.slice(0, n);
  }
  const h = [...seed].reduce((s, c) => s + c.charCodeAt(0), 0);
  const out: Product[] = [];
  for (let i = 0; out.length < n && i < pool.length; i++) { const p = pool[(h + i * 7) % pool.length]; if (!out.includes(p)) out.push(p); }
  return out;
}

/** 右レール「今週のボトル」: 週替わりで 3 本（180ml お試し 1 本＋720ml 1 本＋ワイン/ビール/ジン 1 本） */
export async function weeklyPicks(weekSeed: number): Promise<Product[]> {
  const all = await allProducts();
  const pick = (f: (p: Product) => boolean, k: number) => { const l = all.filter(f); return l.length ? l[(weekSeed * k) % l.length] : null; };
  return [pick((p) => p.tags.includes("Trial"), 3), pick((p) => p.tags.includes("Sake") && !p.tags.includes("Trial"), 5), pick((p) => !p.tags.includes("Sake"), 7)].filter(Boolean) as Product[];
}

export const shopUrl = (handle: string, utm: { medium: string; campaign: string; content?: string }) =>
  `${SHOP}/products/${handle}?utm_source=sakewire&utm_medium=${utm.medium}&utm_campaign=${utm.campaign}${utm.content ? `&utm_content=${utm.content}` : ""}`;
export const shopHome = (utm: { medium: string; campaign: string; content?: string }) =>
  `${SHOP}/?utm_source=sakewire&utm_medium=${utm.medium}&utm_campaign=${utm.campaign}${utm.content ? `&utm_content=${utm.content}` : ""}`;
