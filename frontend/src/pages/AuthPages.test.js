// @vitest-environment happy-dom
import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import Login from "./LoginPage";
import Register from "./RegisterPage";
import { login, register } from "../api/apiService";
const auth = vi.hoisted(() => ({ setAccessToken: vi.fn(), setCSRFToken: vi.fn() }));
vi.mock("../hooks/useAuth", () => ({ default: () => auth }));
vi.mock("../api/apiService", () => ({ login: vi.fn(), register: vi.fn() }));
vi.mock("js-cookie", () => ({ default: { get: vi.fn() } }));
vi.mock("react-toastify", () => ({ toast: { success: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
function mount(Page, path) {
  render(<MemoryRouter initialEntries={[{ pathname: path, state: { from: { pathname: "/videos/" } } }]}><Routes><Route path={path} element={<Page />} /><Route path="/videos/" element={<p>Video library</p>} /><Route path="/login/" element={<p>Check your email then sign in</p>} /></Routes></MemoryRouter>);
}
function fillLogin() {
  fireEvent.change(screen.getByLabelText("Username"), { target: { value: "creator" } });
  fireEvent.change(screen.getByLabelText("Password", { exact: true }), { target: { value: "Password1!" } });
}
function fillRegister(confirm = "Password1!") {
  fillLogin();
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "creator@example.com" } });
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: confirm } });
}
it("shows passwords on request and prevents repeat sign-ins while pending, then restores the destination", async () => {
  let finish;
  login.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  mount(Login, "/signin/");
  fillLogin();
  fireEvent.click(screen.getByRole("button", { name: "Show password" }));
  expect(screen.getByLabelText("Password", { exact: true }).type).toBe("text");
  fireEvent.click(screen.getByLabelText("Remember me"));
  fireEvent.click(screen.getByRole("button", { name: "Sign in", exact: true }));
  expect(screen.getByRole("button", { name: "Signing in…" }).disabled).toBe(true);
  fireEvent.submit(screen.getByLabelText("Username").closest("form"));
  expect(login).toHaveBeenCalledTimes(1);
  expect(login).toHaveBeenCalledWith({ username: "creator", password: "Password1!", remember_me: true });
  finish({ ok: true, data: { tokens: { access: "access" } }, headers: { "x-csrftoken": "csrf" } });
  await screen.findByText("Video library");
  expect(auth.setAccessToken).toHaveBeenCalledWith("access");
  expect(auth.setCSRFToken).toHaveBeenCalledWith("csrf");
});
it("keeps login errors inline and allows retry", async () => {
  login.mockResolvedValue({ ok: false, message: "Invalid credentials" });
  mount(Login, "/signin/"); fillLogin();
  fireEvent.click(screen.getByRole("button", { name: "Sign in", exact: true }));
  expect((await screen.findByRole("alert")).textContent).toBe("Invalid credentials");
  expect(screen.getByRole("button", { name: "Sign in", exact: true }).disabled).toBe(false);
});
it("blocks mismatched passwords and updates guidance before registering", async () => {
  register.mockResolvedValue({ ok: true });
  mount(Register, "/register/"); fillRegister("Different1!");
  fireEvent.click(screen.getByRole("button", { name: "Create your account" }));
  expect(register).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain("don’t match");
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "Password1!" } });
  expect(screen.getByRole("status").textContent).toContain("Passwords match");
  fireEvent.click(screen.getByRole("button", { name: "Create your account" }));
  await screen.findByText("Check your email then sign in");
  expect(register).toHaveBeenCalledWith({ username: "creator", email: "creator@example.com", password: "Password1!" });
});
it("reports registration network failures and re-enables submission", async () => {
  register.mockRejectedValue(new Error("offline"));
  mount(Register, "/register/"); fillRegister();
  fireEvent.click(screen.getByRole("button", { name: "Create your account" }));
  expect((await screen.findByRole("alert")).textContent).toContain("couldn’t create");
  await waitFor(() => expect(screen.getByRole("button", { name: "Create your account" }).disabled).toBe(false));
});
