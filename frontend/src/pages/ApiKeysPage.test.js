import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiKeys } from "./ApiKeysPage";
import { getApiKeys, getCustomTtsProviders } from "../api/apiService";

jest.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: jest.fn() }));
jest.mock("react-toastify", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock("../api/apiService", () => ({
  getApiKeys: jest.fn(), updateApiKeys: jest.fn(), deleteApiKeys: jest.fn(),
  getCustomTtsProviders: jest.fn(), createCustomTtsProvider: jest.fn(),
  updateCustomTtsProvider: jest.fn(), deleteCustomTtsProvider: jest.fn(),
  refreshCustomTtsProviderVoices: jest.fn(),
}));

beforeEach(() => {
  jest.resetAllMocks();
  getApiKeys.mockResolvedValue({ ok: true, data: { use_service_api_keys: false } });
  getCustomTtsProviders.mockResolvedValue({ ok: true, data: [] });
});

test("custom providers have a separate tab and preserve both sections' drafts", async () => {
  render(<ApiKeys />);
  const keysTab = await screen.findByRole("tab", { name: "Built-in API keys" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Add provider", hidden: true })).toBeEnabled());
  const customTab = screen.getByRole("tab", { name: "Custom voice providers" });
  expect(keysTab).toHaveAttribute("aria-selected", "true");
  fireEvent.change(screen.getByLabelText("OpenAI"), { target: { value: "draft-key" } });
  fireEvent.click(customTab);
  expect(screen.getByRole("tabpanel", { name: "Custom voice providers" })).toBeVisible();
  expect(screen.queryByRole("tabpanel", { name: "Built-in API keys" })).not.toBeInTheDocument();
  await screen.findByText("No custom providers yet");
  fireEvent.click(screen.getByRole("button", { name: "Add provider" }));
  fireEvent.change(screen.getByLabelText("Provider name"), { target: { value: "Unsaved service" } });
  fireEvent.click(keysTab);
  expect(screen.getByLabelText("OpenAI")).toHaveValue("draft-key");
  expect(keysTab).toHaveTextContent("unsaved");
  fireEvent.click(customTab);
  expect(screen.getByLabelText("Provider name")).toHaveValue("Unsaved service");
});

test("tabs support keyboard navigation and keep focus on the selected tab", async () => {
  render(<ApiKeys />);
  const keysTab = await screen.findByRole("tab", { name: "Built-in API keys" });
  await waitFor(() => expect(screen.getByRole("button", { name: "Add provider", hidden: true })).toBeEnabled());
  const customTab = screen.getByRole("tab", { name: "Custom voice providers" });
  fireEvent.keyDown(keysTab, { key: "ArrowRight" });
  expect(customTab).toHaveFocus();
  expect(customTab).toHaveAttribute("aria-selected", "true");
  fireEvent.keyDown(customTab, { key: "Home" });
  expect(keysTab).toHaveFocus();
  expect(keysTab).toHaveAttribute("aria-selected", "true");
});
