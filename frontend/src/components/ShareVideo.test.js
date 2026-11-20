// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ShareVideo } from "./ShareVideo";
import { createVideoShare, getVideoShare, revokeVideoShare } from "../api/apiService";

vi.mock("../api/apiService", () => ({ createVideoShare: vi.fn(), getVideoShare: vi.fn(), revokeVideoShare: vi.fn() }));

beforeEach(() => {
  vi.clearAllMocks();
  getVideoShare.mockResolvedValue({ ok: true, data: { active: false } });
});
afterEach(cleanup);

const exportedVideo = { id: "video-1", title: "Ocean stories", output: "/media/output.mp4" };

it("creates sharing only after an explicit action, copies the link and revokes it", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
  createVideoShare.mockResolvedValue({ ok: true, data: { active: true, path: "/share/secret/", expires_at: null } });
  revokeVideoShare.mockResolvedValue({ ok: true });
  render(<ShareVideo video={exportedVideo} />);
  expect(getVideoShare).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Share link" }));
  await screen.findByRole("button", { name: "Create share link" });
  expect(createVideoShare).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Link expires"), { target: { value: "7" } });
  fireEvent.click(screen.getByRole("button", { name: "Create share link" }));
  const input = await screen.findByLabelText("Public viewing link");
  expect(createVideoShare).toHaveBeenCalledWith("video-1", { expires_in_days: 7 });
  expect(input.value).toBe(`${window.location.origin}/share/secret/`);
  fireEvent.click(screen.getByRole("button", { name: "Copy link" }));
  await screen.findByRole("button", { name: "Copied!" });
  expect(writeText).toHaveBeenCalledWith(input.value);
  fireEvent.click(screen.getByRole("button", { name: "Stop sharing" }));
  await screen.findByRole("button", { name: "Create share link" });
  expect(revokeVideoShare).toHaveBeenCalledWith("video-1");
  expect(screen.queryByLabelText("Public viewing link")).toBeNull();
});

it("requires an export and keeps sharing disabled when loading fails", async () => {
  render(<ShareVideo video={{ id: "draft" }} />);
  fireEvent.click(screen.getByRole("button", { name: "Share link" }));
  const button = await screen.findByRole("button", { name: "Create share link" });
  expect(button.disabled).toBe(true);
  expect(screen.getByText("Export your video to create a viewing link.")).toBeTruthy();
  cleanup();
  getVideoShare.mockResolvedValue({ ok: false, message: "Unable to load" });
  render(<ShareVideo video={exportedVideo} />);
  fireEvent.click(screen.getByRole("button", { name: "Share link" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Unable to load");
  expect(screen.queryByRole("button", { name: "Create share link" })).toBeNull();
});

it("keeps a link visible if revocation fails", async () => {
  getVideoShare.mockResolvedValue({ ok: true, data: { active: true, path: "/share/secret/" } });
  revokeVideoShare.mockResolvedValue({ ok: false, message: "Try again" });
  render(<ShareVideo video={exportedVideo} />);
  fireEvent.click(screen.getByRole("button", { name: "Share link" }));
  fireEvent.click(await screen.findByRole("button", { name: "Stop sharing" }));
  await waitFor(() => expect(screen.getByRole("alert").textContent).toBe("Try again"));
  expect(screen.getByLabelText("Public viewing link")).toBeTruthy();
});
