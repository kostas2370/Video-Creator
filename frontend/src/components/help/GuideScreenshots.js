import { useState } from "react";
import { HiOutlineArrowsPointingOut, HiOutlinePhoto } from "react-icons/hi2";
import { EditorDialog } from "../ui/EditorDialog";

const screenshots = {
  start: [
    {
      src: "/guide-images/manual-project.webp",
      width: 1512,
      height: 763,
      alt: "The blank project form with project name and landscape, portrait, and square formats",
      caption:
        "Start with a name and a format. You’ll add your media in the scene editor.",
    },
  ],
  providers: [
    {
      src: "/guide-images/api-keys.webp",
      width: 1512,
      height: 763,
      alt: "API keys and providers settings with masked saved credentials",
      caption: "Add provider credentials in settings. Saved keys stay masked.",
    },
  ],
  ai: [
    {
      src: "/showcase/storyboard.png",
      width: 1280,
      height: 1516,
      alt: "Review your video screen with scene count, narration, and visual settings",
      caption:
        "Review the plan, look, and sound before drafting your storyboard.",
    },
  ],
  series: [
    {
      src: "/guide-images/series-workspace.webp",
      width: 1280,
      height: 1519,
      alt: "Series workspace with recurring characters and episode memory",
      caption:
        "Keep your cast and story context together as you plan the next episode.",
    },
  ],
  story: [
    {
      src: "/guide-images/story-gameplay.webp",
      width: 1512,
      height: 763,
      alt: "Story over gameplay creation form with a story prompt and portrait preview",
      caption: "Bring your story and gameplay together in a vertical format.",
    },
  ],
  clips: [
    {
      src: "/guide-images/clip-editor.webp",
      width: 1512,
      height: 763,
      alt: "Clip editor with portrait preview, framing, captions, and trim settings",
      caption: "Refine the crop, captions, and timing of your selected moment.",
    },
  ],
  captions: [
    {
      src: "/guide-images/caption-editor.webp",
      width: 1512,
      height: 763,
      alt: "Caption editor with a video preview and editable caption styles",
      caption:
        "Preview the words on your video while you adjust their look and timing.",
    },
  ],
  edit: [
    {
      src: "/showcase/editor.png",
      width: 1512,
      height: 1559,
      alt: "Scene editor with preview, narration tabs, and a storyboard timeline",
      caption:
        "Pick a scene from the storyboard, then use its tabs to edit the details.",
    },
  ],
  "preview-export": [
    {
      src: "/guide-images/preview-timeline.webp",
      width: 1512,
      height: 763,
      alt: "Video preview dialog with playback controls and a timeline of scenes",
      caption: "Watch the scene sequence before rendering your final export.",
    },
  ],
  publish: [
    {
      src: "/guide-images/publish-video.webp",
      width: 1512,
      height: 763,
      alt: "Publishing dialog with a finished export and a connected account selector",
      caption: "Review the finished export and destination before publishing.",
    },
  ],
};

export function GuideScreenshots({ topicId, title }) {
  const [selected, setSelected] = useState(null);
  const [failed, setFailed] = useState({});
  const images = screenshots[topicId];
  if (!images) return null;
  return (
    <section className="guide-visuals" aria-label="Screenshots for this guide">
      <div className="guide-visuals-heading">
        <span>
          <HiOutlinePhoto aria-hidden="true" />
          See it in Viddie
        </span>
        <p>Example screens · Click for a closer look</p>
      </div>
      {images.map((image) => (
        <figure key={image.src} className="guide-screenshot">
          {failed[image.src] ? (
            <p className="guide-image-error">
              Screenshot unavailable. Follow the steps below to continue.
            </p>
          ) : (
            <button
              type="button"
              aria-label={`Enlarge screenshot: ${image.alt}`}
              onClick={() => setSelected(image)}
            >
              <img
                src={image.src}
                alt={image.alt}
                width={image.width}
                height={image.height}
                loading="lazy"
                onError={() =>
                  setFailed((current) => ({ ...current, [image.src]: true }))
                }
              />
              <span className="guide-image-zoom">
                <HiOutlineArrowsPointingOut aria-hidden="true" />
                View larger
              </span>
            </button>
          )}
          <figcaption>{image.caption}</figcaption>
        </figure>
      ))}
      <EditorDialog
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={title ? `${title} · Screenshot` : "Guide screenshot"}
        description={selected?.caption}
        closeLabel="Close screenshot"
        maxWidth="max-w-6xl"
        panelClassName="guide-image-dialog"
      >
        {selected && (
          <>
            <img
              className="guide-full-image"
              src={selected.src}
              alt={selected.alt}
            />
            <a
              className="help-link guide-original-image"
              href={selected.src}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open full-size image
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          </>
        )}
      </EditorDialog>
    </section>
  );
}
