import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CustomTtsProviders } from "./CustomTtsProviders";
import { getCustomTtsProviders, createCustomTtsProvider, updateCustomTtsProvider, deleteCustomTtsProvider, refreshCustomTtsProviderVoices } from "../api/apiService";

jest.mock("../api/apiService", () => ({
  getCustomTtsProviders: jest.fn(), createCustomTtsProvider: jest.fn(),
  updateCustomTtsProvider: jest.fn(), deleteCustomTtsProvider: jest.fn(),
  refreshCustomTtsProviderVoices: jest.fn(),
}));
jest.mock("react-toastify", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const provider = {
  id: 1, name: "My service", endpoint_url: "https://example.com/speech",
  auth_type: "bearer", auth_header_name: "", api_key: "abc••••••••1234",
  voices_url: "https://example.com/voices", text_field_name: "text", voice_field_name: "voice_id",
};

beforeEach(() => {
  jest.resetAllMocks();
  getCustomTtsProviders.mockResolvedValue({ ok: true, data: [provider] });
});

async function clickAndResolve(button) {
  fireEvent.click(button);
  await waitFor(() => expect(screen.queryByText(/^(Saving|Queueing|Deleting)\.\.\.$/)).not.toBeInTheDocument());
}

async function editProvider() {
  render(<CustomTtsProviders />);
  fireEvent.click(await screen.findByRole("button", { name: "Edit" }));
}

test("editing preserves a stored credential instead of sending its mask", async () => {
  updateCustomTtsProvider.mockResolvedValue({ ok: true, data: provider });
  await editProvider();
  expect(screen.getByLabelText("API key or token")).toHaveValue("");
  fireEvent.change(screen.getByLabelText("Speech endpoint URL"), { target: { value: "https://example.com/new" } });
  await clickAndResolve(screen.getByRole("button", { name: "Save provider" }));
  await waitFor(() => expect(updateCustomTtsProvider).toHaveBeenCalled());
  const [id, data] = updateCustomTtsProvider.mock.calls[0];
  expect(id).toBe(1);
  expect(data.endpoint_url).toBe("https://example.com/new");
  expect(data).not.toHaveProperty("api_key");
  expect(data).not.toHaveProperty("name");
});

test("explicitly clearing a saved credential sends an empty value", async () => {
  updateCustomTtsProvider.mockResolvedValue({ ok: true, data: { ...provider, api_key: "" } });
  await editProvider();
  fireEvent.click(screen.getByLabelText("Clear saved credential on save"));
  await clickAndResolve(screen.getByRole("button", { name: "Save provider" }));
  await waitFor(() => expect(updateCustomTtsProvider).toHaveBeenCalledWith(1, expect.objectContaining({ api_key: "" })));
});

test("creating a provider submits authentication and request fields", async () => {
  getCustomTtsProviders.mockResolvedValue({ ok: true, data: [] });
  createCustomTtsProvider.mockResolvedValue({ ok: true, data: provider });
  render(<CustomTtsProviders />);
  await screen.findByText(/No custom providers yet/);
  fireEvent.click(screen.getByRole("button", { name: "Add provider" }));
  fireEvent.change(screen.getByLabelText("Provider name"), { target: { value: "My service" } });
  fireEvent.change(screen.getByLabelText("Speech endpoint URL"), { target: { value: provider.endpoint_url } });
  fireEvent.change(screen.getByLabelText("Authentication"), { target: { value: "header" } });
  fireEvent.change(screen.getByLabelText("Authentication header name"), { target: { value: "x-api-key" } });
  fireEvent.change(screen.getByLabelText("API key or token"), { target: { value: "secret" } });
  await clickAndResolve(screen.getAllByRole("button", { name: "Add provider" }).find((button) => !button.disabled));
  await waitFor(() => expect(createCustomTtsProvider).toHaveBeenCalledWith(expect.objectContaining({
    name: "My service", auth_type: "header", auth_header_name: "x-api-key",
    api_key: "secret", text_field_name: "text", voice_field_name: "voice_id",
  })));
});

test("a failed save keeps the editor and its draft available", async () => {
  updateCustomTtsProvider.mockResolvedValue({ ok: false, message: "endpoint_url: Invalid URL", errors: { endpoint_url: ["Invalid URL"] } });
  await editProvider();
  fireEvent.change(screen.getByLabelText("API key or token"), { target: { value: "replacement" } });
  await clickAndResolve(screen.getByRole("button", { name: "Save provider" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid URL");
  expect(screen.getByLabelText("API key or token")).toHaveValue("replacement");
});

test("failed deletion keeps the provider listed and allows retry", async () => {
  deleteCustomTtsProvider.mockResolvedValueOnce({ ok: false, message: "Offline" }).mockResolvedValueOnce({ ok: true });
  render(<CustomTtsProviders />);
  fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
  expect(deleteCustomTtsProvider).not.toHaveBeenCalled();
  await clickAndResolve(screen.getByRole("button", { name: "Delete provider" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Delete provider" })).toBeEnabled());
  expect(screen.getByRole("heading", { name: "My service" })).toBeInTheDocument();
  await clickAndResolve(screen.getByRole("button", { name: "Delete provider" }));
  await waitFor(() => expect(screen.queryByRole("heading", { name: "My service" })).not.toBeInTheDocument());
});

test("refresh requests the provider's voice import", async () => {
  refreshCustomTtsProviderVoices.mockResolvedValue({ ok: true });
  render(<CustomTtsProviders />);
  await clickAndResolve(await screen.findByRole("button", { name: "Refresh voices" }));
  await waitFor(() => expect(refreshCustomTtsProviderVoices).toHaveBeenCalledWith(1));
});

test("cancel preserves unsaved changes until they are explicitly discarded", async () => {
  await editProvider();
  expect(screen.getByRole("button", { name: "Save provider" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Speech endpoint URL"), { target: { value: "https://example.com/changed" } });
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.getByRole("group", { name: "Discard unsaved changes" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  expect(screen.getByLabelText("Speech endpoint URL")).toHaveValue("https://example.com/changed");
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  fireEvent.click(screen.getByRole("button", { name: "Discard changes" }));
  expect(screen.queryByRole("form", { name: "Edit My service" })).not.toBeInTheDocument();
  expect(updateCustomTtsProvider).not.toHaveBeenCalled();
});

test("service key mode explains hidden voices and offers a direct switch", async () => {
  const switchKeys = jest.fn();
  render(<CustomTtsProviders useServiceKeys onUseOwnKeys={switchKeys} />);
  fireEvent.click(await screen.findByRole("button", { name: "Use my own keys" }));
  expect(screen.getByText(/custom voices are hidden/)).toBeInTheDocument();
  expect(switchKeys).toHaveBeenCalledTimes(1);
});

test("voice refresh stays visibly queued without claiming the import completed", async () => {
  refreshCustomTtsProviderVoices.mockResolvedValue({ ok: true });
  render(<CustomTtsProviders />);
  await clickAndResolve(await screen.findByRole("button", { name: "Refresh voices" }));
  expect(screen.getByRole("status")).toHaveTextContent("Voice import queued");
});

test("show credential reveals only the replacement that was typed", async () => {
  await editProvider();
  fireEvent.change(screen.getByLabelText("API key or token"), { target: { value: "new-secret" } });
  fireEvent.click(screen.getByRole("button", { name: "Show credential" }));
  expect(screen.getByLabelText("API key or token")).toHaveAttribute("type", "text");
  expect(screen.getByLabelText("API key or token")).toHaveValue("new-secret");
  fireEvent.click(screen.getByRole("button", { name: "Hide credential" }));
  expect(screen.getByLabelText("API key or token")).toHaveAttribute("type", "password");
});
