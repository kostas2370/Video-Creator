import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, readdir, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gunzipSync } from "node:zlib";
import { precompress } from "./precompress.mjs";

test("build compression preserves asset bytes, originals, and modification times", async t => {
  const directory = await mkdtemp(join(tmpdir(), "viddie-compression-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  await mkdir(join(directory, "static"));
  await mkdir(join(directory, "fonts"));
  const assets = [
    ["static/app.js", Buffer.from("export const value = 'video';\n".repeat(100))],
    ["fonts/preview.ttf", Buffer.from(Array.from({ length: 4096 }, (_, i) => i % 256))],
    ["index.html", Buffer.from("<main>Video creator</main>".repeat(100))],
  ];
  for (const [name, bytes] of assets) await writeFile(join(directory, name), bytes);
  const totals = await precompress(directory);
  assert.equal(totals.files, assets.length);
  assert.ok(totals.compressed < totals.original);
  for (const [name, bytes] of assets) {
    const file = join(directory, name);
    assert.deepEqual(await readFile(file), bytes);
    assert.deepEqual(gunzipSync(await readFile(`${file}.gz`)), bytes);
    assert.ok(Math.abs((await stat(file)).mtimeMs - (await stat(`${file}.gz`)).mtimeMs) < 1);
  }
  assert.deepEqual(await precompress(directory), totals);
});

test("skips tiny, incompressible, and already compressed media files", async t => {
  const directory = await mkdtemp(join(tmpdir(), "viddie-compression-"));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const { randomBytes } = await import("node:crypto");
  const names = ["small.js", "noise.ttf", "image.png", "video.mp4", "packed.js.gz"];
  for (const name of names) {
    await writeFile(join(directory, name), name === "small.js" ? "small" : randomBytes(4096));
  }
  assert.deepEqual(await precompress(directory), { files: 0, original: 0, compressed: 0 });
  assert.deepEqual((await readdir(directory)).sort(), names.sort());
});
