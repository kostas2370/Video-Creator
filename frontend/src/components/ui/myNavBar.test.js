import React from "react";
import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, within } from "@testing-library/react";
import Navbar from "./myNavBar";
jest.mock("../../hooks/useLogout", () => () => jest.fn());
jest.mock("./NotificationBell", () => ({ NotificationBell: () => null }));
beforeAll(() => { global.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }; });
test("navigation highlights the video library for an editor route", () => {
  render(<MemoryRouter initialEntries={["/videos/31/"]}><Navbar theme="light" toggleTheme={jest.fn()} /></MemoryRouter>);
  const main = within(screen.getByRole("navigation", { name: "Main navigation" }));
  expect(main.getByRole("link", { name: "My videos" })).toHaveAttribute("aria-current", "page");
  expect(main.getByRole("link", { name: "Generate" })).not.toHaveAttribute("aria-current");
  expect(main.getByRole("link", { name: "Providers" })).toHaveAttribute("href", "/api-keys");
});
test("mobile menu reports its state and closes on selection or Escape", () => {
  render(<MemoryRouter><Navbar theme="light" toggleTheme={jest.fn()} /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", { name: "Open main menu" }));
  expect(screen.getByRole("button", { name: "Close main menu" })).toHaveAttribute("aria-expanded", "true");
  fireEvent.click(within(screen.getByRole("navigation", { name: "Mobile navigation" })).getByRole("link", { name: "Providers" }));
  expect(screen.queryByRole("navigation", { name: "Mobile navigation" })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open main menu" }));
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("navigation", { name: "Mobile navigation" })).not.toBeInTheDocument();
});
