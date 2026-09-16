import { defineConfig } from "astro/config";
import sitemap from "@astrojs/sitemap";

// ドメイン決定後: site を https://<domain> に、base を "/" に変える
export default defineConfig({
  site: "https://tkuboafro.github.io",
  base: "/mia-media",
  trailingSlash: "always",
  integrations: [sitemap()],
  i18n: {
    defaultLocale: "en",
    locales: ["en", "nl", "de", "es", "ja"],
    routing: { prefixDefaultLocale: true },
  },
});
