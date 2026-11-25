export const publicPages = {
  "/": {
    title: "Viddie — AI Video Creator & Editor",
    description:
      "Create videos from ideas, scripts, and your own footage with Viddie. Edit scenes, add captions, turn long videos into Shorts, and share your finished video.",
  },
  "/guide/": {
    title: "Viddie Guide — Create, Edit & Share Videos",
    description:
      "Learn how to create your first video, connect AI providers, edit scenes, add captions, export, and share with Viddie.",
  },
  "/whats-new/": {
    title: "What’s New in Viddie",
    description:
      "Explore the latest Viddie video creation, editing, captioning, and sharing improvements.",
  },
  "/privacy/": {
    title: "Privacy Policy — Viddie",
    description:
      "How Viddie handles account information, provider credentials, and video project data.",
  },
  "/terms/": {
    title: "Terms of Service — Viddie",
    description:
      "Read the terms for using Viddie and its video creation tools.",
  },
  "/contact/": {
    title: "Contact Viddie",
    description:
      "Contact Viddie for support, feedback, or an early access request.",
  },
};

export function siteOrigin(value) {
  const url = new URL(value);
  if (
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash ||
    !(
      url.protocol === "https:" ||
      (url.protocol === "http:" &&
        ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname))
    )
  ) {
    throw new Error(
      "VITE_PUBLIC_SITE_URL must be an HTTPS origin, or an HTTP localhost origin for development.",
    );
  }
  return url.origin;
}
