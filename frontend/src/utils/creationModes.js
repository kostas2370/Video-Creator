import { HiOutlineBookOpen, HiOutlineSparkles, HiOutlineFilm, HiOutlineMicrophone, HiOutlineChatBubbleBottomCenterText } from "react-icons/hi2";

export const creationModes = [
  {
    to: "/series/", label: "Create a series", eyebrow: "Keep the story going", icon: HiOutlineBookOpen,
    description: "Build a recurring cast and signature style. Draft each new episode with memory of the stories before it.",
    requirement: "A series idea + connected AI providers", action: "Build your series",
    color: "text-indigo-600 dark:text-indigo-300", background: "bg-indigo-50 dark:bg-indigo-950/40", preview: "series",
  },
  {
    to: "/ai/", label: "Create with AI", eyebrow: "Start with an idea", icon: HiOutlineSparkles,
    description: "Turn a prompt into a script, narration, and scenes. Review the storyboard before generating your media.",
    requirement: "An idea + connected AI providers", action: "Build with AI",
    color: "text-blue-600 dark:text-blue-300", background: "bg-blue-50 dark:bg-blue-950/40", preview: "ai",
  },
  {
    to: "/story/", label: "Story over gameplay", eyebrow: "Made for short stories", icon: HiOutlineMicrophone,
    description: "Pair a narrated story with looping gameplay and word highlights. Ready for a vertical social video.",
    requirement: "A gameplay clip + a connected voice provider", action: "Tell a story",
    color: "text-violet-600 dark:text-violet-300", background: "bg-violet-50 dark:bg-violet-950/40", preview: "story",
  },
  {
    to: "/manual/", label: "Edit your own media", eyebrow: "Start from scratch", icon: HiOutlineFilm,
    description: "Bring your photos and clips. Arrange scenes, record a voiceover, and add music at your own pace.",
    requirement: "Your own media · No API keys needed", action: "Open a blank project",
    color: "text-emerald-600 dark:text-emerald-300", background: "bg-emerald-50 dark:bg-emerald-950/40", preview: "manual",
  },
  {
    to: "/captions/", label: "Add captions", eyebrow: "Already have a video?", icon: HiOutlineChatBubbleBottomCenterText,
    description: "Turn speech into editable captions. Choose a style, fine-tune the words, and export your captioned video.",
    requirement: "A video with speech + an OpenAI API key", action: "Caption a video",
    color: "text-amber-700 dark:text-amber-300", background: "bg-amber-50 dark:bg-amber-950/40", preview: "captions",
  },
];

export const isCreationPath = pathname => {
  const path = pathname.replace(/\/+$/, "") || "/";
  return path === "/" || creationModes.some(mode => mode.to.replace(/\/$/, "") === path) || path.startsWith("/captions/") || path.startsWith("/series/");
};
