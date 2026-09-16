// 媒体の基本設定。ドメインが決まったら site を差し替える（GitHub Pages の間は github.io）。
export const SITE = {
  name: "MADE IN AKITA Journal",
  tagline: {
    en: "News and stories from the world of Japanese sake, wine, beer and spirits — with a soft spot for Akita.",
    nl: "Nieuws en verhalen uit de wereld van Japanse sake, wijn, bier en gedistilleerd — met een zwak voor Akita.",
    de: "Nachrichten und Geschichten aus der Welt von japanischem Sake, Wein, Bier und Spirituosen – mit einer Schwäche für Akita.",
    es: "Noticias e historias del mundo del sake, el vino, la cerveza y los destilados japoneses — con debilidad por Akita.",
    ja: "日本酒・ワイン・ビール・スピリッツの今を、ヨーロッパへ。秋田をすこし多めに。",
  },
  shop: "https://shop.made-in-akita.com",
  instagram: "https://www.instagram.com/made_in_akita/",
  langs: ["en", "nl", "de", "es", "ja"] as const,
  langNames: { en: "English", nl: "Nederlands", de: "Deutsch", es: "Español", ja: "日本語" },
  ui: {
    en: { latest: "Latest", source: "Source", readMore: "Read more", shopCta: "Shop Akita sake in the EU", akita: "Akita", allNews: "All stories", published: "Published", drink: "Enjoy responsibly. 18+ (20+ in SE/LT/JP).", sources: "Sources", sourcesNote: "This article was written by the MADE IN AKITA Journal editorial team, summarising the public sources listed above. Images are our own." },
    nl: { latest: "Laatste", source: "Bron", readMore: "Lees verder", shopCta: "Akita-sake kopen in de EU", akita: "Akita", allNews: "Alle verhalen", published: "Gepubliceerd", drink: "Geniet met mate. 18+ (20+ in SE/LT/JP).", sources: "Bronnen", sourcesNote: "Dit artikel is geschreven door de redactie van MADE IN AKITA Journal op basis van de bovenstaande openbare bronnen. De beelden zijn van onszelf." },
    de: { latest: "Aktuell", source: "Quelle", readMore: "Weiterlesen", shopCta: "Akita-Sake in der EU kaufen", akita: "Akita", allNews: "Alle Beiträge", published: "Veröffentlicht", drink: "Bitte verantwortungsvoll genießen. 18+ (20+ in SE/LT/JP).", sources: "Quellen", sourcesNote: "Dieser Beitrag wurde von der Redaktion des MADE IN AKITA Journal auf Grundlage der oben genannten öffentlichen Quellen verfasst. Die Bilder stammen von uns." },
    es: { latest: "Lo último", source: "Fuente", readMore: "Leer más", shopCta: "Compra sake de Akita en la UE", akita: "Akita", allNews: "Todas las historias", published: "Publicado", drink: "Disfruta con responsabilidad. 18+ (20+ en SE/LT/JP).", sources: "Sources", sourcesNote: "This article was written by the MADE IN AKITA Journal editorial team, summarising the public sources listed above. Images are our own." },
    ja: { latest: "最新", source: "出典", readMore: "続きを読む", shopCta: "EUで秋田の酒を買う", akita: "秋田", allNews: "すべての記事", published: "公開", drink: "お酒は20歳（EUでは18歳・SE/LTは20歳）になってから。", sources: "参考・出典", sourcesNote: "本記事は上記の公開情報をもとに MADE IN AKITA Journal 編集部が要約・執筆したものです。画像は自社素材を使用しています。" },
  },
};
export const CATEGORY: Record<string, Record<string, string>> = {
  "新商品": { en: "New release", nl: "Nieuw product", de: "Neuheit", es: "Novedad", ja: "新商品" },
  "受賞": { en: "Awards", nl: "Onderscheiding", de: "Auszeichnung", es: "Premios", ja: "受賞" },
  "輸出": { en: "Export", nl: "Export", de: "Export", es: "Exportación", ja: "輸出" },
  "蔵元": { en: "Breweries", nl: "Brouwerijen", de: "Brauereien", es: "Bodegas", ja: "蔵元" },
  "酒米": { en: "Sake rice", nl: "Sakerijst", de: "Sake-Reis", es: "Arroz para sake", ja: "酒米" },
  "イベント": { en: "Events", nl: "Evenementen", de: "Veranstaltungen", es: "Eventos", ja: "イベント" },
  "行政": { en: "Policy", nl: "Beleid", de: "Politik", es: "Política", ja: "行政" },
  "研究": { en: "Research", nl: "Onderzoek", de: "Forschung", es: "Investigación", ja: "研究" },
  "その他": { en: "Stories", nl: "Verhalen", de: "Geschichten", es: "Historias", ja: "話題" },
};
export const catLabel = (c: string | undefined, l: Lang) => (c && CATEGORY[c]?.[l]) || c || "";
export type Lang = (typeof SITE.langs)[number];
