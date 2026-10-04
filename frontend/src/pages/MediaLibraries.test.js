import React from "react";
import { MemoryRouter } from "react-router-dom";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { Avatar } from "./AvatarPage";
import { AssetPage } from "./AssetPage";
import { getAvatars, getVoices, createAvatar, getIntro, getOutro, createOutro } from "../api/apiService";
jest.mock("../api/apiService", () => ({
  getAvatars: jest.fn(),
  getVoices: jest.fn(),
  createAvatar: jest.fn(),
  deleteAvatar: jest.fn(),
  getIntro: jest.fn(),
  getOutro: jest.fn(),
  createIntro: jest.fn(),
  createOutro: jest.fn(),
  deleteIntro: jest.fn(),
  deleteOutro: jest.fn()
}));
jest.mock("../hooks/useDebounce", () => ({
  useDebounce: value => value
}));
jest.mock("react-toastify", () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn()
  }
}));
jest.mock("../components/DeleteModal", () => ({
  DeleteModal: () => null
}));
beforeAll(() => {
  global.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  URL.createObjectURL = jest.fn(() => "blob:preview");
  URL.revokeObjectURL = jest.fn();
});
beforeEach(() => {
  jest.clearAllMocks();
  URL.createObjectURL.mockReturnValue("blob:preview");
  getAvatars.mockResolvedValue(result([]));
  getVoices.mockResolvedValue(result([{
    id: 2,
    name: "onyx",
    provider: "OPENAI"
  }]));
  getIntro.mockResolvedValue(result([{
    id: 1,
    name: "Studio opening",
    file: "/intro.mp4"
  }]));
  getOutro.mockResolvedValue(result([{
    id: 2,
    name: "Closing credits",
    file: "/outro.mp4"
  }]));
});
test("avatar creation previews the uploaded portrait and sends the selected voice", async () => {
  createAvatar.mockResolvedValue(result({
    id: 3,
    name: "Presenter",
    file: "/portrait.png",
    sample: ""
  }));
  render(<MemoryRouter><Avatar /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", {
    name: "Create avatar"
  }));
  await screen.findByRole("option", {
    name: "onyx · OPENAI"
  });
  const portrait = new File(["portrait"], "portrait.png", {
    type: "image/png"
  });
  fireEvent.change(screen.getByLabelText("Portrait image"), {
    target: {
      files: [portrait]
    }
  });
  expect(await screen.findByRole("img", {
    name: "New avatar preview"
  })).toHaveAttribute("src", "blob:preview");
  fireEvent.change(screen.getByLabelText("Avatar name"), {
    target: {
      value: "Presenter"
    }
  });
  fireEvent.change(screen.getByLabelText("Gender"), {
    target: {
      value: "oth"
    }
  });
  fireEvent.change(screen.getByLabelText("Voice"), {
    target: {
      value: "2"
    }
  });
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", {
    name: "Create avatar"
  }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  const data = createAvatar.mock.calls[0][0];
  expect(data.get("voice")).toBe("2");
  expect(data.get("name")).toBe("Presenter");
  expect(data.get("file")).toBe(portrait);
});
test("an avatar with no available voices points to provider settings", async () => {
  getVoices.mockResolvedValue(result([]));
  render(<MemoryRouter><Avatar /></MemoryRouter>);
  fireEvent.click(screen.getByRole("button", {
    name: "Create avatar"
  }));
  expect(await screen.findByRole("link", {
    name: "Check your provider settings"
  })).toHaveAttribute("href", "/api-keys/");
  expect(within(screen.getByRole("dialog")).getByRole("button", {
    name: "Create avatar"
  })).toBeDisabled();
});
test("asset tabs preserve search and uploads go to the selected asset API", async () => {
  createOutro.mockResolvedValue(result({
    id: 4,
    name: "End card",
    file: "/end.mp4"
  }));
  render(<MemoryRouter><AssetPage /></MemoryRouter>);
  await screen.findByRole("link", {
    name: "Preview Studio opening"
  });
  fireEvent.change(screen.getByRole("searchbox", {
    name: "Search intros"
  }), {
    target: {
      value: "Studio"
    }
  });
  fireEvent.click(screen.getByRole("tab", {
    name: "Outros"
  }));
  expect(await screen.findByRole("link", {
    name: "Preview Closing credits"
  })).toHaveAttribute("href", "/outro.mp4");
  fireEvent.click(screen.getByRole("button", {
    name: "Add outro"
  }));
  fireEvent.change(screen.getByLabelText("Clip name"), {
    target: {
      value: "End card"
    }
  });
  const clip = new File(["video"], "end.mp4", {
    type: "video/mp4"
  });
  fireEvent.change(screen.getByLabelText("Video file"), {
    target: {
      files: [clip]
    }
  });
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", {
    name: "Add outro"
  }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(createOutro.mock.calls[0][0].get("file")).toBe(clip);
  fireEvent.click(screen.getByRole("tab", {
    name: "Intros"
  }));
  expect(screen.getByRole("searchbox", {
    name: "Search intros"
  })).toHaveValue("Studio");
});
function result(data) {
  return {
    ok: data !== undefined,
    data: data ?? null
  };
}
