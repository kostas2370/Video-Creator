import { describe, expect, it } from "vitest";
import { isCreationPath } from "./creationModes";

describe("creation navigation", () => {
  it.each(["/", "/ai", "/ai/", "/story", "/story/", "/manual", "/manual/", "/captions", "/captions/", "/captions/project/"])("highlights creation for %s", path => {
    expect(isCreationPath(path)).toBe(true);
  });
  it.each(["/videos/", "/videos/project/", "/assets/", "/ai/other/"])("keeps other destinations separate for %s", path => {
    expect(isCreationPath(path)).toBe(false);
  });
});
