// @vitest-environment happy-dom
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import LandingPage from "./LandingPage";
const deployment = vi.hoisted(() => ({ invite_only: true }));
vi.mock("../store/DeploymentContext", () => ({
  useDeployment: () => deployment,
}));
afterEach(() => {
  cleanup();
  deployment.invite_only = true;
});
it("introduces Viddie publicly with working sign-in, registration, guide, and invitation links", () => {
  render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
  expect(screen.getByRole("heading", { level: 1 }).textContent).toContain(
    "worth watching",
  );
  expect(
    screen.getByRole("link", { name: "Sign in" }).getAttribute("href"),
  ).toBe("/login/");
  expect(
    screen.getByRole("link", { name: "Get started" }).getAttribute("href"),
  ).toBe("/register/");
  expect(
    screen
      .getByRole("link", { name: "Request an invitation" })
      .getAttribute("href"),
  ).toBe("/contact/");
  expect(
    screen.getByText(/Provider usage may be billed separately/),
  ).toBeTruthy();
});
it("does not advertise an invitation requirement on an open workspace", () => {
  deployment.invite_only = false;
  render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
  expect(
    screen.queryByRole("link", { name: "Request an invitation" }),
  ).toBeNull();
  expect(screen.getByRole("link", { name: "Get started" })).toBeTruthy();
});
