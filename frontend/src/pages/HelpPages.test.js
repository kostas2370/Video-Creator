// @vitest-environment happy-dom
import React from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GuidePage, WhatsNewPage } from "./HelpPages";
import { getNewsUpdates } from "../api/apiService";

vi.mock("../api/apiService", () => ({ getNewsUpdates: vi.fn() }));

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
const show = page => render(<MemoryRouter>{page}</MemoryRouter>);
const update = (id, title) => ({ id, title, content: "First paragraph.\n\nSecond paragraph.", published_at: "2026-11-22T12:00:00Z" });

it("finds guide sections by topic while keeping their instructions available", () => {
  show(<GuidePage />);
  const contents = screen.getByRole("navigation", { name: "Guide contents" });
  fireEvent.change(screen.getByRole("searchbox", { name: "Find a section" }), { target: { value: "  MUSIC " } });
  expect(within(contents).getAllByRole("link")).toHaveLength(1);
  expect(within(contents).getByRole("link").getAttribute("href")).toBe("#edit");
  expect(screen.getByRole("heading", { name: "Share a finished export" })).toBeTruthy();
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "unknown section" } });
  expect(within(contents).getByRole("status").textContent).toContain("No matching section");
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "" } });
  expect(within(contents).getAllByRole("link")).toHaveLength(8);
});

it("gives every guide jump link an existing destination", () => {
  const { container } = show(<GuidePage />);
  const links = [...container.querySelectorAll('a[href^="#"]')];
  expect(links.length).toBeGreaterThan(8);
  for (const link of links) {
    expect(container.querySelector(link.getAttribute("href"))).toBeTruthy();
  }
});

it("retains loaded news after a failure and retries the same older page without duplicates", async () => {
  const latest = update("latest", "Beta release");
  getNewsUpdates.mockResolvedValueOnce({ ok: true, data: { results: [latest], next: "page-2" } })
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce({ ok: true, data: { results: [latest, update("older", "Earlier release")], next: null } });
  show(<WhatsNewPage />);
  await screen.findByRole("heading", { name: "Beta release" });
  fireEvent.click(screen.getByRole("button", { name: "Load older updates" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("heading", { name: "Beta release" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByRole("heading", { name: "Earlier release" });
  expect(getNewsUpdates.mock.calls.map(([page]) => page)).toEqual([1, 2, 2]);
  expect(screen.getAllByRole("article")).toHaveLength(2);
  expect(screen.getAllByText("Latest update")).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Load older updates" })).toBeNull();
});

it("shows guide and feedback links when the news feed is empty", async () => {
  getNewsUpdates.mockResolvedValue({ ok: true, data: { results: [], next: null } });
  show(<WhatsNewPage />);
  await screen.findByRole("heading", { name: "No updates yet" });
  expect(screen.getByRole("link", { name: "Explore the guide →" }).getAttribute("href")).toBe("/guide/");
  expect(screen.getByRole("link", { name: "Send feedback →" }).getAttribute("href")).toBe("/contact/");
});

it("preserves plain text news and separates its paragraphs", async () => {
  const news = { ...update("one", "An update"), content: "<script>example</script>\n\nSecond paragraph." };
  getNewsUpdates.mockResolvedValue({ ok: true, data: { results: [news], next: null } });
  show(<WhatsNewPage />);
  await screen.findByRole("heading", { name: "An update" });
  const article = screen.getByRole("article");
  expect(within(article).getByText("<script>example</script>").tagName).toBe("P");
  expect(within(article).getByText("Second paragraph.").tagName).toBe("P");
  expect(article.querySelector("script")).toBeNull();
});

it("groups loaded releases by month without repeating a heading across pages", async () => {
  const current = update("one", "Series stories");
  const sameMonth = update("two", "Storyboard changes");
  const older = { ...update("three", "Earlier tools"), published_at: "2026-10-10T12:00:00Z" };
  getNewsUpdates.mockResolvedValueOnce({ ok: true, data: { results: [current], next: "page-2" } })
    .mockResolvedValueOnce({ ok: true, data: { results: [sameMonth, older], next: null } });
  show(<WhatsNewPage />);
  await screen.findByRole("heading", { name: "Series stories" });
  fireEvent.click(screen.getByRole("button", { name: "Load older updates" }));
  await screen.findByRole("heading", { name: "Earlier tools" });
  const monthName = value => new Date(value).toLocaleDateString(undefined, { month: "long", year: "numeric" });
  expect(screen.getAllByRole("heading", { name: monthName(current.published_at) })).toHaveLength(1);
  expect(screen.getByRole("heading", { name: monthName(older.published_at) })).toBeTruthy();
  expect(screen.getAllByText("Latest update")).toHaveLength(1);
  const navigation = screen.getByRole("navigation", { name: "Try a creation tool" });
  expect(within(navigation).getByRole("link", { name: "Create with AI" }).getAttribute("href")).toBe("/ai/");
});
