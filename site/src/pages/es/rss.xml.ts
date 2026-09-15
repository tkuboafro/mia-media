import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import { SITE } from "../../config";
export async function GET(context: any) {
  const items = (await getCollection("articles", (a) => a.data.lang === "es")).sort((a, b) => b.data.pubDate.valueOf() - a.data.pubDate.valueOf());
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  return rss({ title: `${SITE.name} (es)`, description: SITE.tagline["es"], site: context.site,
    items: items.map((a) => ({ title: a.data.title, description: a.data.description, pubDate: a.data.pubDate, link: `${base}/es/${a.data.slug}/` })) });
}
