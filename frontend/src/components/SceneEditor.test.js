import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Scene } from "./Scene";
import { updateScene, generateScene, updateSceneImage, generateSceneImage } from "../api/apiService";
jest.mock("../api/apiService", () => ({
  updateScene: jest.fn(),
  generateScene: jest.fn(),
  updateSceneImage: jest.fn(),
  generateSceneImage: jest.fn(),
  deleteImageScene: jest.fn(),
  deleteScene: jest.fn()
}));
jest.mock("react-toastify", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn()
  }
}));
jest.mock("./DeleteModal", () => ({
  DeleteModal: () => null
}));
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});
const scene = {
  id: 5,
  text: "Original narration",
  file: "/audio.mp3",
  scene_image: {
    id: 8,
    file: "/photo.png",
    prompt: "A sunny park",
    with_audio: false
  }
};
beforeEach(() => {
  jest.resetAllMocks();
  updateScene.mockResolvedValue(result({}));
  updateSceneImage.mockResolvedValue(result({}));
  generateSceneImage.mockResolvedValue(result({}));
});
test("rewrite is reviewed before saving and reopening uses the latest dialogue", async () => {
  generateScene.mockResolvedValue(result({
    text: "A shorter narration"
  }));
  const refresh = jest.fn();
  const {
    rerender
  } = render(<Scene scene={scene} setUpdated={refresh} video_type="AI" />);
  fireEvent.click(screen.getByRole("button", {
    name: "Edit scene text"
  }));
  fireEvent.change(screen.getByLabelText("Rewrite with AI"), {
    target: {
      value: "Shorten it"
    }
  });
  fireEvent.click(screen.getByRole("button", {
    name: "Generate rewrite"
  }));
  await waitFor(() => expect(screen.getByLabelText("Dialogue")).toHaveValue("A shorter narration"));
  expect(updateScene).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", {
    name: "Save dialogue"
  }));
  await waitFor(() => expect(refresh).toHaveBeenCalled());
  expect(updateScene).toHaveBeenCalledWith(5, {
    text: "A shorter narration"
  });
  rerender(<Scene scene={{
    ...scene,
    text: "A shorter narration"
  }} setUpdated={refresh} video_type="AI" />);
  fireEvent.click(screen.getByRole("button", {
    name: "Edit scene text"
  }));
  expect(screen.getByLabelText("Dialogue")).toHaveValue("A shorter narration");
});
test("existing audio settings can be changed without uploading", async () => {
  render(<Scene scene={scene} setUpdated={jest.fn()} video_type="AI" />);
  fireEvent.click(screen.getByRole("button", {
    name: "Edit visual"
  }));
  fireEvent.click(screen.getByLabelText("Keep uploaded video audio"));
  fireEvent.click(screen.getByRole("button", {
    name: "Save visual"
  }));
  await waitFor(() => expect(updateSceneImage).toHaveBeenCalled());
  const [id, imageId, data] = updateSceneImage.mock.calls[0];
  expect([id, imageId]).toEqual([5, 8]);
  expect(data.get("with_audio")).toBe("1");
  expect(data.has("image")).toBe(false);
});
test("missing image can open the editor and generate a visual", async () => {
  render(<Scene scene={{
    ...scene,
    scene_image: null
  }} setUpdated={jest.fn()} video_type="AI" />);
  fireEvent.click(screen.getByRole("button", {
    name: "Add visual"
  }));
  expect(screen.getByRole("button", {
    name: "Save visual"
  })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", {
    name: "Generate with AI"
  }));
  fireEvent.change(screen.getByLabelText("Image description"), {
    target: {
      value: "A mountain sunrise"
    }
  });
  fireEvent.click(screen.getByRole("button", {
    name: "Generate image"
  }));
  await waitFor(() => expect(generateSceneImage).toHaveBeenCalled());
  expect(generateSceneImage.mock.calls[0][1].get("image_description")).toBe("A mountain sunrise");
});
function result(data) {
  return {
    ok: data !== undefined,
    data: data ?? null
  };
}
