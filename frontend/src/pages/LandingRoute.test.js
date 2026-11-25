// @vitest-environment happy-dom
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import App from "../App";
const auth = vi.hoisted(() => ({ access_token: null }));
const refresh = vi.hoisted(() => vi.fn());
vi.mock("../hooks/useAuth", () => ({ default: () => auth }));
vi.mock("../hooks/useRefreshToken", () => ({ default: () => refresh }));
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => {} }));
vi.mock("../components/ui/myNavBar", () => ({
  default: () => <nav>Workspace navigation</nav>,
}));
vi.mock("./CreatePage", () => ({ default: () => <h1>Your workspace</h1> }));
afterEach(() => {
  cleanup();
  auth.access_token = null;
  vi.clearAllMocks();
});
it("shows a useful public homepage even while a guest session check is pending", async () => {
  refresh.mockReturnValue(new Promise(() => {}));
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { level: 1, name: /worth watching/ });
  expect(screen.getByRole("link", { name: "Get started" })).toBeTruthy();
  expect(screen.queryByText("Workspace navigation")).toBeNull();
});
it("keeps authenticated visitors in their existing workspace", async () => {
  auth.access_token = "existing-session";
  render(
    <MemoryRouter initialEntries={["/"]}>
      <App />
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { name: "Your workspace" });
  expect(screen.queryByRole("link", { name: "Get started" })).toBeNull();
  expect(refresh).not.toHaveBeenCalled();
});
