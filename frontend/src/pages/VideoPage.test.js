import React from "react";
import { act, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Video } from "./VideoPage";
import { getVideo } from "../api/apiService";

jest.mock("../api/apiService", () => ({ getVideo: jest.fn() }));
jest.mock("../components/VideoConfigModal", () => ({ VideoConfigModal: () => null }));
jest.mock("../components/RenderModal", () => ({ RenderModal: () => null }));
jest.mock("../components/ResumeModal", () => ({ ResumeModal: () => null }));
jest.mock("../components/CreateSceneModal", () => ({ SceneCreationModal: () => null }));
jest.mock("../components/CreateTwitchSceneModal", () => ({ TwitchSceneCreationModal: () => null }));
jest.mock("../components/Scene", () => ({ Scene: ({ scene }) => <p>{scene.text}</p> }));
const row = { id: 12, title: "My video", status: "GENERATION", scenes: [], scene_jobs: [{ id: 1, status: "PROCESSING" }] };
const mount = async () => {
  let result;
  await act(async () => { result = render(<MemoryRouter initialEntries={["/videos/12"]}><Routes><Route path="/videos/:videoId" element={<Video />} /></Routes></MemoryRouter>); });
  return result;
};
beforeEach(() => { jest.useFakeTimers(); jest.clearAllMocks(); });
afterEach(() => { jest.useRealTimers(); });

test("resumes progress on reload and refreshes scenes when the worker completes", async () => {
  getVideo.mockResolvedValue({ data: row });
  await mount();
  expect(screen.getByText("Creating your scene…")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Render video" })).toBeDisabled();
  getVideo.mockResolvedValue({ data: { ...row, status: "READY", scenes: [{ id: 4, text: "Finished scene" }], scene_jobs: [{ id: 1, status: "COMPLETED" }] } });
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(screen.getAllByText("Finished scene").length).toBeGreaterThan(0);
  expect(screen.queryByText("Creating your scene…")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Render video" })).toBeEnabled();
  const calls = getVideo.mock.calls.length;
  await act(async () => { jest.advanceTimersByTime(9000); });
  expect(getVideo).toHaveBeenCalledTimes(calls);
});

test("poll failures retry and worker errors are shown", async () => {
  getVideo.mockResolvedValue({ data: row });
  await mount();
  getVideo.mockResolvedValue({ data: null });
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(screen.getByText(/Retrying automatically/)).toBeInTheDocument();
  getVideo.mockResolvedValue({ data: { ...row, status: "READY", scene_jobs: [{ id: 1, status: "FAILED", error: "Scene creation failed" }] } });
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(screen.getByRole("alert")).toHaveTextContent("Scene creation failed");
  expect(screen.getByRole("button", { name: "Add scene" })).toBeEnabled();
});
