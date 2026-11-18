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
  show({ use_service_api_keys: false, openai_key: "sk-••••••••key1", openai_warning: { code: "credentials", message: "OpenAI rejected the API key. It may be revoked." } });
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("It may be revoked"));
  expect(screen.getByText("Needs attention")).toBeTruthy();
  expect(screen.getByLabelText("OpenAI").parentElement.parentElement.parentElement.textContent).toContain("OpenAI rejected");
});

it("identifies service key warnings without blaming the saved personal key", async () => {
  show({ use_service_api_keys: true, openai_key: "sk-••••••••key1", openai_warning: { code: "quota", message: "OpenAI quota or billing limit reached." } });
  await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("OpenAI service key needs attention"));
  expect(screen.getByRole("alert").textContent).toContain("Contact the administrator");
  expect(screen.queryByText("Needs attention")).toBeNull();
});

it("shows no warning when the active key has no recorded failure", async () => {
  show({ use_service_api_keys: false, openai_key: "sk-••••••••key1", openai_warning: null });
  await screen.findByLabelText("OpenAI");
  expect(screen.queryByRole("alert")).toBeNull();
});

it("clears the warning after saving a replacement key", async () => {
  show({ use_service_api_keys: false, openai_key: "sk-••••••••key1", openai_warning: { code: "credentials", message: "OpenAI rejected the API key." } });
  const input = await screen.findByLabelText("OpenAI");
  updateApiKeys.mockResolvedValue({ ok: true, data: { use_service_api_keys: false, openai_key: "sk-••••••••key2", openai_warning: null } });
  fireEvent.change(input, { target: { value: "sk-replacement" } });
  fireEvent.click(screen.getByRole("button", { name: "Save 1 change" }));
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(updateApiKeys).toHaveBeenCalledWith({ openai_key: "sk-replacement" });
});
