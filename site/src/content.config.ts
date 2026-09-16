import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const articles = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/articles" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    lang: z.enum(["en", "nl", "de", "es", "ja"]),
    story: z.string(),         // 言語をまたいで同じ記事を結ぶキー（`slug` は glob loader が id に使うので避ける）
    hero: z.string().optional(),
    heroAlt: z.string().optional(),
    heroCredit: z.string().optional(),
    sources: z.array(z.object({ name: z.string().optional(), title: z.string().optional(), url: z.string() })).default([]),
    sourceUrl: z.string().url(),
    sourceTitle: z.string(),
    sourceName: z.string(),
    region: z.string().optional(),
    regionEn: z.string().optional(),
    category: z.string().optional(),
    akita: z.boolean().default(false),
    tags: z.array(z.string()).default([]),
    products: z.array(z.string()).default([]),   // 関連する shop の商品ハンドル
  }),
});
export const collections = { articles };
