// @vitest-environment happy-dom
import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DeploymentProvider, useDeployment } from "./DeploymentContext";
import { getDeployment } from "../api/apiService";

vi.mock("../api/apiService", () => ({ getDeployment: vi.fn() }));
afterEach(cleanup);

function Features() {
  const deployment = useDeployment();
  return <div>{deployment.sadtalker_enabled ? "Presenters available" : "Presenters disabled"} · {deployment.invite_only ? "Invitation required" : "Open registration"}</div>;
}

it("uses the server policy for production features", async () => {
  getDeployment.mockResolvedValue({ ok: true, data: { sadtalker_enabled: false, invite_only: true } });
  render(<DeploymentProvider><Features /></DeploymentProvider>);
  expect(await screen.findByText("Presenters disabled · Invitation required")).toBeTruthy();
});

it("allows presenters and open registration when the server enables them", async () => {
  getDeployment.mockResolvedValue({ ok: true, data: { sadtalker_enabled: true, invite_only: false } });
  render(<DeploymentProvider><Features /></DeploymentProvider>);
  expect(await screen.findByText("Presenters available · Open registration")).toBeTruthy();
});

it("keeps restricted defaults when policy loading fails", async () => {
  getDeployment.mockRejectedValue(new Error("Unavailable"));
  render(<DeploymentProvider><Features /></DeploymentProvider>);
  expect(await screen.findByText("Presenters disabled · Invitation required")).toBeTruthy();
});

it("keeps restricted defaults when a proxy returns HTML instead of policy flags", async () => {
  getDeployment.mockResolvedValue({ ok: true, data: "<html>Unavailable</html>" });
  render(<DeploymentProvider><Features /></DeploymentProvider>);
  expect(await screen.findByText("Presenters disabled · Invitation required")).toBeTruthy();
});
