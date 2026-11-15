// @vitest-environment happy-dom
import { afterEach, expect, it } from "vitest";
import { libraryQuery, libraryReturnUrl, readLibraryNavigation, saveLibraryNavigation } from "./videoLibraryNavigation";
afterEach(() => sessionStorage.clear());
it("rejects invalid filters and page numbers from stored or shared URLs", () => {
  expect(libraryQuery("status=INVALID&creation_mode=BAD&ordering=secret&view=bad&page=-5")).toMatchObject({ status: "", creation_mode: "", ordering: "-updated_at", view: "grid", page: 1 });
  expect(libraryQuery("page=1.5").page).toBe(1);
});
it("keeps account navigation separate and builds only a local library URL", () => {
  saveLibraryNavigation("one", { query: "search=fox&page=2&next=https://example.com", scrollY: 650 });
  expect(readLibraryNavigation("two")).toBeNull();
  expect(libraryReturnUrl("one")).toBe("/videos/?search=fox&page=2");
  expect(libraryReturnUrl("")).toBe("/videos/");
});
