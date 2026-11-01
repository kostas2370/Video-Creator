import { describe, expect, it } from "vitest";
import {
  visualProviderNames, isBuiltinVisualProvider, supportsVisualReference,
  isBuiltinVideoProvider, isReservedVisualProvider,
} from "./visualProviders";

describe("visual provider capabilities", () => {
  it("reserves picker providers regardless of case or surrounding whitespace", () => {
    for (const name of Object.keys(visualProviderNames)) {
      expect(isReservedVisualProvider("  " + name.toUpperCase() + "  ")).toBe(true);
    }
    expect(isReservedVisualProvider("STABLE_DIFFUSION")).toBe(true);
    expect(isReservedVisualProvider("My studio")).toBe(false);
  });

  it("keeps web mode from activating a saved AI reference capability", () => {
    expect(supportsVisualReference("runway", "AI")).toBe(true);
    expect(supportsVisualReference("runway", "WEB")).toBe(false);
    expect(isBuiltinVideoProvider("OPENAI")).toBe(false);
    expect(supportsVisualReference("midjourney", "AI")).toBe(false);
  });

  it("does not mistake inherited object properties or custom names for built-ins", () => {
    for (const name of ["toString", "__proto__", "Studio", undefined]) {
      expect(isBuiltinVisualProvider(name)).toBe(false);
      expect(isBuiltinVideoProvider(name)).toBe(false);
      expect(supportsVisualReference(name, "AI")).toBe(false);
    }
  });
});
