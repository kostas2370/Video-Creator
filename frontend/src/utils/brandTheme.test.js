import { expect, it } from "vitest";
import { readFileSync } from "node:fs";
const themeCss = readFileSync(new URL("../components/BrandTheme.css", import.meta.url), "utf8");
import tailwind from "../../tailwind.config.js";

function luminance(hex) {
  const digits = hex.slice(1);
  const full = digits.length === 3 ? [...digits].map(value => value + value).join("") : digits;
  const channels = full.match(/../g).map(value => {
    const channel = parseInt(value, 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
}
function contrast(first, second) {
  const values = [luminance(first), luminance(second)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

it.each([":root", ":root.dark"])("keeps workspace text, selected controls and primary actions readable in %s", selector => {
  const block = themeCss.split(`${selector} {`)[1].split("}")[0];
  const tokens = Object.fromEntries([...block.matchAll(/--brand-([\w-]+):\s*(#[\da-f]+);/g)].map(match => [match[1], match[2]]));
  for (const surface of ["surface", "panel", "panel-soft", "selected"]) {
    for (const text of ["ink", "muted", "accent"]) {
      expect(contrast(tokens[text], tokens[surface]), `${text} on ${surface}`).toBeGreaterThanOrEqual(4.5);
    }
  }
  for (const surface of ["button", "button-hover"]) {
    expect(contrast(tokens["button-ink"], tokens[surface])).toBeGreaterThanOrEqual(4.5);
  }
});

it("keeps utility button labels and light-mode secondary text readable", () => {
  for (const shade of [600, 700]) expect(contrast("#fff", tailwind.theme.colors.blue[shade])).toBeGreaterThanOrEqual(4.5);
  expect(contrast(tailwind.theme.colors.gray[500], tailwind.theme.colors.gray[50])).toBeGreaterThanOrEqual(4.5);
});
