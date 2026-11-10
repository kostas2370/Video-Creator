import { expect, it } from "vitest";
import { mapSections } from "./cuts";

it("maps full-video cuts through scene gaps to the composed source", () => {
  expect(mapSections([{ start: 1, end: 3 }, { start: 5, end: 10 }], [{ start: 1, end: 4 }])).toEqual([{ start: 2, end: 3 }, { start: 5, end: 7 }]);
});
