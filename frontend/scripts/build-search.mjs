import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { loadEnv } from "vite";
import { publicPages, siteOrigin } from "../src/content/search.mjs";

export async function writeSearchFiles(directory, publicUrl) {
  const origin = publicUrl ? siteOrigin(publicUrl) : null;
  const robots = `User-agent: *\nDisallow: /api/\nDisallow: /admin/\nDisallow: /media/\n${origin ? `\nSitemap: ${origin}/sitemap.xml\n` : ""}`;
  await writeFile(resolve(directory, "robots.txt"), robots);
  if (origin) {
    const urls = Object.keys(publicPages)
      .map((path) => `  <url><loc>${origin}${path}</loc></url>`)
      .join("\n");
    await writeFile(
      resolve(directory, "sitemap.xml"),
      `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
    );
  }
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(resolve(process.argv[1])).href
) {
  const env = loadEnv("production", process.cwd(), "VITE_");
  await writeSearchFiles(
    resolve("build"),
    process.env.VITE_PUBLIC_SITE_URL || env.VITE_PUBLIC_SITE_URL,
  );
}
