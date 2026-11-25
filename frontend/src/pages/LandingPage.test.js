// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
    screen.getByRole("link", { name: "Request early access" }).getAttribute("href"),
  ).toBe("/request-access/");
  expect(
    screen
      .getByRole("link", { name: "Request an invitation" })
      .getAttribute("href"),
  ).toBe("/request-access/");
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

it("loads only the selected YouTube player after an explicit play action", () => {
  const { container } = render(<MemoryRouter><LandingPage /></MemoryRouter>);
  expect(container.querySelector("iframe")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Play World War II: Causes, Conflict, and Consequences" }));
  expect(container.querySelectorAll("iframe")).toHaveLength(1);
  expect(container.querySelector("iframe").src).toContain("youtube-nocookie.com/embed/EeKK9NKiiNg");
  fireEvent.click(screen.getByRole("button", { name: "Play Australia’s Great Emu War" }));
  expect(container.querySelectorAll("iframe")).toHaveLength(1);
  expect(container.querySelector("iframe").src).toContain("mrEpfZUVlNA");
  expect(screen.getByRole("link", { name: /More on TikTok/ }).href).toBe("https://www.tiktok.com/@viddieeducation");
});
