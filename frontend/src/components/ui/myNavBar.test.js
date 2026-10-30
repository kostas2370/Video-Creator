// @vitest-environment happy-dom
import React from "react";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import Navbar from "./myNavBar";

vi.mock("./NotificationBell", () => ({ NotificationBell: () => null }));
vi.mock("../../hooks/useLogout", () => ({ default: () => vi.fn() }));
afterEach(cleanup);

function Page() {
  const { pathname } = useLocation();
  return <><Navbar theme="light" toggleTheme={vi.fn()} /><p data-testid="route">{pathname}</p></>;
}

it.each([
  ["/", "My projects"],
  ["/videos/video-1/", "My videos"],
  ["/series/series-1/", "My series"],
  ["/clips/project-1/", "My clips"],
  ["/clips-other/", "My projects"],
])("labels the project menu for %s", (path, label) => {
  render(<MemoryRouter initialEntries={[path]}><Page /></MemoryRouter>);
  expect(screen.getByRole("button", { name: label })).toBeTruthy();
  if (path.startsWith("/clips/") || path.startsWith("/series/") || path.startsWith("/videos/")) {
    expect(screen.getByRole("link", { name: "Create", exact: true }).getAttribute("aria-current")).toBeNull();
  }
});

it("navigates between project types through the desktop dropdown", async () => {
  render(<MemoryRouter initialEntries={["/clips/"]}><Page /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "My clips" }));
  const menu = screen.getByRole("menu");
  expect(within(menu).getByRole("menuitem", { name: "My clips" }).getAttribute("aria-current")).toBe("page");
  await userEvent.click(within(menu).getByRole("menuitem", { name: "My series" }));
  expect(screen.getByTestId("route").textContent).toBe("/series");
  expect(screen.getByRole("button", { name: "My series" })).toBeTruthy();
  expect(screen.queryByRole("menu")).toBeNull();
});

it("shows direct project links on phones and closes the menu after navigation", async () => {
  render(<MemoryRouter initialEntries={["/clips/"]}><Page /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "Open main menu" }));
  const mobile = screen.getByRole("navigation", { name: "Mobile navigation" });
  for (const name of ["My videos", "My series", "My clips"]) expect(within(mobile).getByRole("link", { name })).toBeTruthy();
  await userEvent.click(within(mobile).getByRole("link", { name: "My videos" }));
  expect(screen.getByTestId("route").textContent).toBe("/videos");
  expect(screen.queryByRole("navigation", { name: "Mobile navigation" })).toBeNull();
});
