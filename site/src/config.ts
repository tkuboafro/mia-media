// 媒体の基本設定。ドメインが決まったら site を差し替える（GitHub Pages の間は github.io）。
export const SITE = {
  name: "MADE IN AKITA Journal",
  tagline: {
    en: "News and stories from the world of Japanese sake, wine, beer and spirits — with a soft spot for Akita.",
    nl: "Nieuws en verhalen uit de wereld van Japanse sake, wijn, bier en gedistilleerd — met een zwak voor Akita.",
    de: "Nachrichten und Geschichten aus der Welt von japanischem Sake, Wein, Bier und Spirituosen – mit einer Schwäche für Akita.",
    es: "Noticias e historias del mundo del sake, el vino, la cerveza y los destilados japoneses — con debilidad por Akita.",
  },
  shop: "https://shop.made-in-akita.com",
  instagram: "https://www.instagram.com/made_in_akita/",
  langs: ["en", "nl", "de", "es"] as const,
  langNames: { en: "English", nl: "Nederlands", de: "Deutsch", es: "Español" },
  ui: {
    en: { latest: "Latest", source: "Source", readMore: "Read more", shopCta: "Shop Akita sake in the EU", akita: "Akita", allNews: "All stories", published: "Published", drink: "Enjoy responsibly. 18+ (20+ in SE/LT/JP)." },
    nl: { latest: "Laatste", source: "Bron", readMore: "Lees verder", shopCta: "Akita-sake kopen in de EU", akita: "Akita", allNews: "Alle verhalen", published: "Gepubliceerd", drink: "Geniet met mate. 18+ (20+ in SE/LT/JP)." },
    de: { latest: "Aktuell", source: "Quelle", readMore: "Weiterlesen", shopCta: "Akita-Sake in der EU kaufen", akita: "Akita", allNews: "Alle Beiträge", published: "Veröffentlicht", drink: "Bitte verantwortungsvoll genießen. 18+ (20+ in SE/LT/JP)." },
    es: { latest: "Lo último", source: "Fuente", readMore: "Leer más", shopCta: "Compra sake de Akita en la UE", akita: "Akita", allNews: "Todas las historias", published: "Publicado", drink: "Disfruta con responsabilidad. 18+ (20+ en SE/LT/JP)." },
  },
};
export const CATEGORY: Record<string, Record<string, string>> = {
  "新商品": { en: "New release", nl: "Nieuw product", de: "Neuheit", es: "Novedad" },
  "受賞": { en: "Awards", nl: "Onderscheiding", de: "Auszeichnung", es: "Premios" },
  "輸出": { en: "Export", nl: "Export", de: "Export", es: "Exportación" },
  "蔵元": { en: "Breweries", nl: "Brouwerijen", de: "Brauereien", es: "Bodegas" },
  "酒米": { en: "Sake rice", nl: "Sakerijst", de: "Sake-Reis", es: "Arroz para sake" },
  "イベント": { en: "Events", nl: "Evenementen", de: "Veranstaltungen", es: "Eventos" },
  "行政": { en: "Policy", nl: "Beleid", de: "Politik", es: "Política" },
  "研究": { en: "Research", nl: "Onderzoek", de: "Forschung", es: "Investigación" },
  "その他": { en: "Stories", nl: "Verhalen", de: "Geschichten", es: "Historias" },
};
export const catLabel = (c: string | undefined, l: Lang) => (c && CATEGORY[c]?.[l]) || c || "";
export type Lang = (typeof SITE.langs)[number];
