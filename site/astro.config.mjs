import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// ドメイン決定後: site を https://<domain> に、base を "/" に変える
export default defineConfig({
  site: "https://sakewire.com",
  base: "/",
  trailingSlash: "always",
  integrations: [sitemap({ filter: (page) => page !== "https://sakewire.com/" })],   // / は言語の振り分けだけ（正規は /en/）
  i18n: {
    defaultLocale: "en",
    locales: ["en", "nl", "de", "es", "ja"],
    routing: { prefixDefaultLocale: true },
  },
});
