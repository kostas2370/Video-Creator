// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import RequestAccessPage from "./RequestAccessPage";
import { requestAccess } from "../api/apiService";
vi.mock("../api/apiService", () => ({ requestAccess: vi.fn() }));
vi.mock("../store/DeploymentContext", () => ({ useDeployment: () => ({ invite_only: true }) }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
function mount() { render(<MemoryRouter><RequestAccessPage /></MemoryRouter>); }
function submit() {
  fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Ada" } });
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "ada@example.test" } });
  fireEvent.change(screen.getByLabelText("What would you like to create?"), { target: { value: "Educational videos for my students" } });
  fireEvent.submit(screen.getByLabelText("Your name").closest("form"));
}
it("waits for a successful save and blocks duplicate submissions", async () => {
  let finish;
  requestAccess.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  mount(); submit();
  fireEvent.submit(screen.getByLabelText("Your name").closest("form"));
  expect(requestAccess).toHaveBeenCalledTimes(1);
  expect(requestAccess).toHaveBeenCalledWith({ name: "Ada", email: "ada@example.test", message: "Educational videos for my students", website: "" });
  expect(screen.queryByRole("status")).toBeNull();
  finish({ ok: true });
  expect((await screen.findByRole("status")).textContent).toContain("Your request is in");
});
it("keeps failed saves visible and allows retry", async () => {
  requestAccess.mockResolvedValue({ ok: false, message: "Server unavailable" });
  mount(); submit();
  expect((await screen.findByRole("alert")).textContent).toBe("Server unavailable");
  expect(screen.queryByRole("status")).toBeNull();
  expect(screen.getByLabelText("Your name").closest("fieldset").disabled).toBe(false);
});
it("explains rate limits", async () => {
  requestAccess.mockResolvedValue({ ok: false, status: 429 });
  mount(); submit();
  expect((await screen.findByRole("alert")).textContent).toContain("try again in an hour");
});
it("handles unexpected failures without claiming success", async () => {
  requestAccess.mockRejectedValue(new Error("network"));
  mount(); submit();
  expect((await screen.findByRole("alert")).textContent).toContain("Please try again");
  expect(screen.queryByRole("status")).toBeNull();
});
