import { readdir, readFile, stat, utimes, writeFile } from "node:fs/promises";
import { extname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";
import { gzip } from "node:zlib";

const compress = promisify(gzip);
const extensions = new Set([".css", ".html", ".js", ".json", ".svg", ".ttf"]);

export async function precompress(directory) {
  const totals = { files: 0, original: 0, compressed: 0 };
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    if (entry.isDirectory()) {
      const nested = await precompress(file);
      for (const key of Object.keys(totals)) totals[key] += nested[key];
    } else if (entry.isFile() && extensions.has(extname(entry.name))) {
      const source = await readFile(file);
      if (source.length < 1024) continue;
      const packed = await compress(source, { level: 9 });
      if (packed.length >= source.length) continue;
      const { atime, mtime } = await stat(file);
      await writeFile(`${file}.gz`, packed);
      await utimes(`${file}.gz`, atime, mtime);
      totals.files += 1;
      totals.original += source.length;
      totals.compressed += packed.length;
    }
  }
  return totals;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const totals = await precompress(fileURLToPath(new URL("../build/", import.meta.url)));
  console.log(`Precompressed ${totals.files} assets: ${(totals.original / 1024).toFixed(0)} → ${(totals.compressed / 1024).toFixed(0)} KiB`);
}
