// @vitest-environment happy-dom
import React from "react";
import { render, screen, waitFor, cleanup, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiKeys } from "./ApiKeysPage";
import { getApiKeys, updateApiKeys } from "../api/apiService";

vi.mock("../api/apiService", () => ({ getApiKeys: vi.fn(), updateApiKeys: vi.fn(), deleteApiKeys: vi.fn() }));
vi.mock("../hooks/useAxiosPrivate", () => ({ useAxiosPrivate: () => {} }));
vi.mock("../components/CustomTtsProviders", () => ({ CustomTtsProviders: () => null }));
vi.mock("../components/CustomVisualProviders", () => ({ CustomVisualProviders: () => null }));
vi.mock("../components/ClearApiKeysModal", () => ({ ClearApiKeysModal: () => null }));
vi.mock("react-toastify", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

afterEach(cleanup);
beforeEach(() => vi.clearAllMocks());
const show = data => {
  getApiKeys.mockResolvedValue({ ok: true, data });
  return render(<MemoryRouter><ApiKeys /></MemoryRouter>);
};

it("shows a rejected personal key warning next to the OpenAI field after reload", async () => {
  show({ use_service_api_keys: false, openai_key: "sk-••••••••key1", key_warnings: { OPENAI: true } });
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("revoked"));
  expect(screen.getByText("Needs attention")).toBeTruthy();
  expect(screen.getByLabelText("OpenAI").parentElement.parentElement.parentElement.textContent).toContain("OpenAI rejected");
});

it("identifies service key warnings without blaming the saved personal key", async () => {
  show({ use_service_api_keys: true, openai_key: "sk-••••••••key1", key_warnings: { OPENAI: true } });
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("OpenAI service key needs attention"));
  expect(screen.getByRole("alert").textContent).toContain("Contact the administrator");
  expect(screen.queryByText("Needs attention")).toBeNull();
});

it("shows no warning when the active key has no recorded failure", async () => {
  show({ use_service_api_keys: false, openai_key: "sk-••••••••key1", key_warnings: {} });
  await screen.findByLabelText("OpenAI");
  expect(screen.queryByRole("alert")).toBeNull();
});

it("clears the warning after saving a replacement key", async () => {
  show({ use_service_api_keys: false, openai_key: "sk-••••••••key1", key_warnings: { OPENAI: true } });
  const input = await screen.findByLabelText("OpenAI");
  updateApiKeys.mockResolvedValue({ ok: true, data: { use_service_api_keys: false, openai_key: "sk-••••••••key2", key_warnings: {} } });
  fireEvent.change(input, { target: { value: "sk-replacement" } });
  fireEvent.click(screen.getByRole("button", { name: "Save 1 change" }));
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(updateApiKeys).toHaveBeenCalledWith({ openai_key: "sk-replacement" });
});

it("shows independent warnings for other built-in keys", async () => {
  show({ use_service_api_keys: false, key_warnings: { ANTHROPIC: true, GEMINI: true } });
  await screen.findByLabelText("OpenAI");
  expect(screen.getAllByRole("alert")).toHaveLength(2);
  expect(screen.getAllByRole("alert").map(element => element.textContent).join(" ")).toContain("Anthropic rejected");
  expect(screen.getAllByRole("alert").map(element => element.textContent).join(" ")).toContain("Google Gemini rejected");
});
