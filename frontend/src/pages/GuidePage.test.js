// @vitest-environment happy-dom
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import GuidePage from "./GuidePage";

beforeEach(() => {
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.spyOn(HTMLElement.prototype, "scrollIntoView").mockImplementation(
    () => {},
  );
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
function Back() {
  const navigate = useNavigate();
  return <button onClick={() => navigate(-1)}>Previous guide</button>;
}
const show = (url = "/guide/") =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <GuidePage />
      <Back />
    </MemoryRouter>,
  );

it("starts with a complete first video walkthrough that does not need API keys", () => {
  show();
  const article = screen.getByRole("article");
  expect(
    within(article).getByRole("heading", { name: "Make your first video" }),
  ).toBeTruthy();
  expect(within(article).getByText(/No API keys needed/)).toBeTruthy();
  expect(
    within(article)
      .getByRole("link", { name: "Start with my own media" })
      .getAttribute("href"),
  ).toBe("/manual/");
  expect(within(article).getAllByRole("heading", { level: 3 })).toHaveLength(5);
});

it("opens a chosen walkthrough and restores the previous guide with browser navigation", () => {
  show();
  fireEvent.click(screen.getByRole("link", { name: /I have an idea/ }));
  const heading = screen.getByRole("heading", {
    name: "Turn an idea into a video",
  });
  expect(heading).toBe(document.activeElement);
  expect(screen.getAllByRole("article")).toHaveLength(1);
  expect(
    screen.queryByRole("heading", { name: "Make your first video" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Previous guide" }));
  expect(
    screen.getByRole("heading", { name: "Make your first video" }),
  ).toBeTruthy();
});

it("searches the instruction text and opens the matching guide", () => {
  show();
  fireEvent.change(
    screen.getByRole("searchbox", { name: "Search the guide" }),
    { target: { value: "  DECIMAL seconds  " } },
  );
  const results = screen.getByRole("region", { name: "1 guide found" });
  expect(
    within(results).getByRole("heading", {
      name: "Turn a long video into Shorts",
    }),
  ).toBeTruthy();
  expect(screen.queryByRole("article")).toBeNull();
  fireEvent.click(within(results).getByRole("link"));
  expect(screen.getByRole("searchbox").value).toBe("");
  expect(
    within(screen.getByRole("article")).getByRole("heading", {
      name: "Turn a long video into Shorts",
    }),
  ).toBe(document.activeElement);
});

it("keeps the current topic when clearing an empty search and supports mobile topic selection", () => {
  show("/guide/#backup");
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "nothing-matches-this" },
  });
  expect(screen.getByRole("status").textContent).toContain("No matches");
  fireEvent.click(screen.getByRole("button", { name: "Clear search" }));
  expect(
    screen.getByRole("heading", {
      name: "Export or import an editable project",
    }),
  ).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Choose a guide"), {
    target: { value: "edit" },
  });
  expect(
    screen.getByRole("heading", { name: "Find your way around the editor" }),
  ).toBeTruthy();
  expect(screen.getByText("Editor map · simplified layout")).toBeTruthy();
});

it("retains existing topic URLs and searches troubleshooting answers", () => {
  show("/guide/#providers");
  expect(
    screen.getByRole("heading", { name: "Connect your AI providers" }),
  ).toBeTruthy();
  fireEvent.change(screen.getByRole("searchbox"), {
    target: { value: "revoked" },
  });
  const results = screen.getByRole("region", { name: /guides? found/ });
  fireEvent.click(
    within(results).getByRole("link", {
      name: /Fix a problem without starting over/,
    }),
  );
  expect(screen.getByText("Project import failed").tagName).toBe("SUMMARY");
  expect(
    screen.getByRole("link", { name: "Contact support" }).getAttribute("href"),
  ).toBe("/contact/");
});
