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
    screen
      .getByRole("link", { name: "Request early access" })
      .getAttribute("href"),
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
  const { container } = render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
  expect(container.querySelector("iframe")).toBeNull();
  fireEvent.click(
    screen.getByRole("button", {
      name: "Play World War II: Causes, Conflict, and Consequences",
    }),
  );
  expect(container.querySelectorAll("iframe")).toHaveLength(1);
  expect(container.querySelector("iframe").src).toContain(
    "youtube-nocookie.com/embed/EeKK9NKiiNg",
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Play Australia’s Great Emu War" }),
  );
  expect(container.querySelectorAll("iframe")).toHaveLength(1);
  expect(container.querySelector("iframe").src).toContain("mrEpfZUVlNA");
  expect(screen.getByRole("link", { name: /More on TikTok/ }).href).toBe(
    "https://www.tiktok.com/@viddieeducation",
  );
});

it("switches the product walkthrough and supports arrow-key navigation", () => {
  render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
  const edit = screen.getByRole("tab", { name: "Make it yours" });
  expect(edit.getAttribute("aria-selected")).toBe("true");
  expect(screen.getByRole("tabpanel").textContent).toContain(
    "Your first draft is just the beginning.",
  );
  fireEvent.click(screen.getByRole("tab", { name: "Plan your story" }));
  expect(screen.getByRole("tabpanel").getAttribute("aria-labelledby")).toBe(
    "workflow-tab-plan",
  );
  expect(
    screen
      .getByRole("img", { name: /Viddie storyboard review/ })
      .getAttribute("src"),
  ).toBe("/showcase/storyboard.png");
  fireEvent.keyDown(screen.getByRole("tab", { name: "Plan your story" }), {
    key: "End",
  });
  expect(
    screen
      .getByRole("tab", { name: "Find the highlights" })
      .getAttribute("aria-selected"),
  ).toBe("true");
  expect(document.activeElement).toBe(
    screen.getByRole("tab", { name: "Find the highlights" }),
  );
  expect(
    screen.getByRole("img", { name: /Viddie clip workspace/ }),
  ).toBeTruthy();
  fireEvent.keyDown(screen.getByRole("tab", { name: "Find the highlights" }), {
    key: "ArrowRight",
  });
  expect(
    screen
      .getByRole("tab", { name: "Plan your story" })
      .getAttribute("aria-selected"),
  ).toBe("true");
});

it("connects the public theme control to the app theme", () => {
  const toggleTheme = vi.fn();
  render(
    <MemoryRouter>
      <LandingPage theme="dark" toggleTheme={toggleTheme} />
    </MemoryRouter>,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Switch to light theme" }),
  );
  expect(toggleTheme).toHaveBeenCalledOnce();
});
