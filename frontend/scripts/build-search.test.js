import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";
import { writeSearchFiles } from "./build-search.mjs";
import { publicPages, siteOrigin } from "../src/content/search.mjs";
it("generates a public-only sitemap with a discoverable robots entry", async () => {
  const directory = await mkdtemp(join(tmpdir(), "viddie-search-"));
  try {
    await writeSearchFiles(directory, "https://viddie.example.com/");
    const sitemap = await readFile(join(directory, "sitemap.xml"), "utf8");
    expect(sitemap).toContain("<loc>https://viddie.example.com/</loc>");
    expect(sitemap).toContain("<loc>https://viddie.example.com/guide/</loc>");
    expect(sitemap).not.toMatch(/\/(login|register|videos|share|api|admin)\//);
    expect(sitemap).toContain("<loc>https://viddie.example.com/request-access/</loc>");
    expect((sitemap.match(/<loc>/g) || []).length).toBe(7);
    expect(await readFile(join(directory, "robots.txt"), "utf8")).toContain(
      "Sitemap: https://viddie.example.com/sitemap.xml",
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
it("does not invent a production hostname when none is configured", async () => {
  const directory = await mkdtemp(join(tmpdir(), "viddie-search-"));
  try {
    await writeSearchFiles(directory, "");
    expect(await readFile(join(directory, "robots.txt"), "utf8")).not.toContain(
      "Sitemap:",
    );
    await expect(stat(join(directory, "sitemap.xml"))).rejects.toThrow();
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
it.each([
  "https://user:secret@example.com",
  "https://example.com/path",
  "https://example.com/?token=secret",
  "http://example.com",
  "javascript:alert(1)",
])("rejects unsafe public origin %s", (value) => {
  expect(() => siteOrigin(value)).toThrow();
});


it("keeps public SPA routes from being shadowed by static files or directories", async () => {
  for (const route of Object.keys(publicPages).filter(path => path !== "/")) {
    const asset = new URL(`../public${route}`, import.meta.url);
    const entry = await stat(asset).catch(error => {
      if (error.code === "ENOENT") return null;
      throw error;
    });
    expect(entry, `Static asset shadows the ${route} page`).toBeNull();
  }
});
