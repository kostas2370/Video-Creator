import { HiOutlineScissors, HiOutlineBookOpen, HiOutlineSparkles, HiOutlineFilm, HiOutlineMicrophone, HiOutlineChatBubbleBottomCenterText } from "react-icons/hi2";

export const creationModes = [
  {
    to: "/clips/", label: "Long video → Shorts", eyebrow: "Find your best moments", icon: HiOutlineScissors,
    description: "Turn a podcast, interview, or talk into short clips with portrait framing and captions.",
    requirement: "A video with speech + connected AI providers", action: "Find short clips",
    color: "text-rose-600 dark:text-rose-300", background: "bg-rose-50 dark:bg-rose-950/40", preview: "clips",
  },
  {
    to: "/series/", label: "Create a series", eyebrow: "Keep the story going", icon: HiOutlineBookOpen,
    description: "Make an ongoing series with recurring characters, a shared style, and connected episodes.",
    requirement: "A series idea + connected AI providers", action: "Build your series",
    color: "text-indigo-600 dark:text-indigo-300", background: "bg-indigo-50 dark:bg-indigo-900/20", preview: "series",
  },
  {
    to: "/ai/", label: "Create with AI", eyebrow: "Start with an idea", icon: HiOutlineSparkles,
    description: "Describe your idea. Shape it into a script, narration, and editable scenes with AI.",
    requirement: "An idea + connected AI providers", action: "Build with AI",
    color: "text-blue-600 dark:text-blue-300", background: "bg-blue-50 dark:bg-blue-950/40", preview: "ai",
  },
  {
    to: "/story/", label: "Story over gameplay", eyebrow: "Made for short stories", icon: HiOutlineMicrophone,
    description: "Tell a narrated story over looping gameplay, with word highlights for vertical video.",
    requirement: "A gameplay clip + a connected voice provider", action: "Tell a story",
    color: "text-violet-600 dark:text-violet-300", background: "bg-violet-50 dark:bg-violet-950/40", preview: "story",
  },
  {
    to: "/manual/", label: "Edit your own media", eyebrow: "Start from scratch", icon: HiOutlineFilm,
    description: "Turn your photos and clips into a finished video. Arrange scenes, add audio, and make it yours.",
    requirement: "Your own media · No API keys needed", action: "Open a blank project",
    color: "text-emerald-600 dark:text-emerald-300", background: "bg-emerald-50 dark:bg-emerald-950/40", preview: "manual",
  },
  {
    to: "/captions/", label: "Add captions", eyebrow: "Already have a video?", icon: HiOutlineChatBubbleBottomCenterText,
    description: "Add styled captions to an existing video. Edit the words and timing before exporting.",
    requirement: "A video with speech + an OpenAI API key", action: "Caption a video",
    color: "text-amber-700 dark:text-amber-300", background: "bg-amber-50 dark:bg-amber-900/20", preview: "captions",
  },
];

export const isCreationPath = pathname => {
  const path = pathname.replace(/\/+$/, "") || "/";
  return path === "/" || creationModes.some(mode => mode.to.replace(/\/$/, "") === path) || path.startsWith("/clips/") || path.startsWith("/captions/") || path.startsWith("/series/");
};
