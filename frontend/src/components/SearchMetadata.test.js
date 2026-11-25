// @vitest-environment happy-dom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { Link, MemoryRouter } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import SearchMetadata from "./SearchMetadata";
afterEach(() => {
  cleanup();
  document.head
    .querySelectorAll(
      'meta[name="robots"], meta[name="description"], meta[property^="og:"], link[rel="canonical"]',
    )
    .forEach((element) => element.remove());
});
it("sets route-specific public metadata and removes query parameters from canonical URLs", () => {
  render(
    <MemoryRouter initialEntries={["/guide/?campaign=test#edit"]}>
      <SearchMetadata />
    </MemoryRouter>,
  );
  expect(document.title).toBe("Viddie Guide — Create, Edit & Share Videos");
  expect(document.head.querySelector('link[rel="canonical"]').href).toMatch(
    /\/guide\/$/,
  );
  expect(document.head.querySelector('meta[name="robots"]').content).toBe(
    "index, follow",
  );
  expect(
    document.head.querySelector('meta[property="og:url"]').content,
  ).not.toContain("campaign");
});
it("removes public canonical and social URLs when navigating to a private page", () => {
  const page = render(
    <MemoryRouter>
      <SearchMetadata />
      <Link to="/videos/private-id/?token=secret">Private project</Link>
    </MemoryRouter>,
  );
  fireEvent.click(page.getByText("Private project"));
  expect(document.head.querySelector('meta[name="robots"]').content).toBe(
    "noindex, nofollow",
  );
  expect(document.head.querySelector('link[rel="canonical"]')).toBeNull();
  expect(document.head.querySelector('meta[property="og:url"]')).toBeNull();
  expect(document.head.innerHTML).not.toContain("token=secret");
});
