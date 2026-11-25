import { Link } from "react-router-dom";
import {
  HiOutlineArrowRight,
  HiOutlineBookOpen,
  HiOutlineCheck,
  HiOutlineFilm,
  HiOutlineScissors,
  HiOutlineSparkles,
} from "react-icons/hi2";
import { useDeployment } from "../store/DeploymentContext";

const primary =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2";
const secondary =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-gray-300 px-5 py-3 text-sm font-semibold transition hover:border-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-gray-600";

export default function LandingPage() {
  const { invite_only: inviteOnly } = useDeployment();
  return (
    <main className="mx-auto max-w-6xl px-4 pb-10 sm:px-6">
      <nav
        aria-label="Viddie public navigation"
        className="flex flex-wrap items-center justify-between gap-4 py-6"
      >
        <Link
          to="/"
          aria-label="Viddie home"
          className="flex items-center gap-3 rounded-lg text-lg font-bold focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <img src="/viddie-icon.svg" alt="" className="h-9 w-9 rounded-xl" />
          Viddie
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            to="/guide/"
            className="px-2 py-2 text-sm font-medium hover:text-blue-500"
          >
            Guide
          </Link>
          <Link to="/login/" className={secondary}>
            Sign in
          </Link>
        </div>
      </nav>
      <section
        aria-labelledby="landing-title"
        className="grid items-center gap-10 py-10 sm:py-16 lg:grid-cols-[1.1fr_1fr]"
      >
        <div>
          <p className="mb-4 text-xs font-bold uppercase tracking-widest text-blue-600 dark:text-blue-300">
            Your ideas. Your footage. Your creative space.
          </p>
          <h1
            id="landing-title"
            className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl lg:text-6xl"
          >
            Make something
            <br />
            <span className="text-blue-600 dark:text-blue-400">
              worth watching.
            </span>
          </h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-gray-600 dark:text-gray-300">
            Viddie is a video creator and editor for turning ideas, scripts, and
            your own media into videos. Build scenes with AI, find highlights in
            long recordings, add captions, and shape the final edit yourself.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link to="/register/" className={primary}>
              Get started
              <HiOutlineArrowRight aria-hidden="true" className="h-4 w-4" />
            </Link>
            <Link to="/guide/" className={secondary}>
              <HiOutlineBookOpen aria-hidden="true" className="h-4 w-4" />
              See how it works
            </Link>
          </div>
          <p className="mt-4 text-xs leading-6 text-gray-500 dark:text-gray-400">
            {inviteOnly ? (
              <>
                Hosted access is currently invite-only.{" "}
                <Link
                  to="/contact/"
                  className="font-semibold text-blue-600 underline dark:text-blue-300"
                >
                  Request an invitation
                </Link>
                .
              </>
            ) : (
              "Start with your own media, or connect your providers to create with AI."
            )}
          </p>
        </div>
        <figure className="overflow-hidden rounded-3xl border border-gray-200 bg-white p-4 shadow-xl shadow-blue-900/5 dark:border-gray-700 dark:bg-gray-800 sm:p-6">
          <figcaption className="mb-4 flex items-center justify-between gap-3 text-xs font-semibold">
            <span className="flex items-center gap-2">
              <HiOutlineFilm
                aria-hidden="true"
                className="h-4 w-4 text-blue-500"
              />
              A little idea, brought to life
            </span>
            <span className="text-gray-400">Editor illustration</span>
          </figcaption>
          <div className="relative flex aspect-video items-end overflow-hidden rounded-2xl bg-gradient-to-br from-blue-700 via-indigo-700 to-violet-500 p-6">
            <div
              aria-hidden="true"
              className="absolute -right-5 -top-12 h-48 w-48 rounded-full border-[24px] border-white/10"
            />
            <div>
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-blue-100">
                Your next story
              </p>
              <p className="text-3xl font-bold tracking-tight text-white">
                One idea.
                <br />A world of possibilities.
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {["01 · The idea", "02 · The story", "03 · Your edit"].map(
              (label) => (
                <div
                  key={label}
                  className="rounded-xl bg-gray-50 px-3 py-4 text-xs font-semibold dark:bg-gray-900/60"
                >
                  {label}
                </div>
              ),
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-gray-500 dark:text-gray-400">
            {["Scenes", "Narration", "Captions"].map((label) => (
              <span key={label} className="flex items-center gap-1.5">
                <HiOutlineCheck
                  aria-hidden="true"
                  className="h-4 w-4 text-blue-500"
                />
                {label}
              </span>
            ))}
          </div>
        </figure>
      </section>
      <section aria-labelledby="landing-tools" className="py-8">
        <p className="text-xs font-bold uppercase tracking-widest text-blue-600 dark:text-blue-300">
          More than one way to create
        </p>
        <h2
          id="landing-tools"
          className="mt-3 text-2xl font-bold tracking-tight sm:text-3xl"
        >
          Start with what you have.
        </h2>
        <div className="mt-7 grid gap-4 sm:grid-cols-3">
          {[
            {
              icon: HiOutlineSparkles,
              title: "Turn an idea into a video",
              text: "Draft a script and storyboard, generate narration and visuals, then review and edit each scene.",
            },
            {
              icon: HiOutlineFilm,
              title: "Edit your own photos and clips",
              text: "Arrange your media, control timing and sound, and make a finished video without needing AI keys.",
            },
            {
              icon: HiOutlineScissors,
              title: "Turn long videos into Shorts",
              text: "Find highlights in interviews, podcasts, and talks. Refine their framing, trim, and captions before exporting.",
            },
          ].map(({ icon: Icon, title, text }) => (
            <article
              key={title}
              className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
            >
              <Icon
                aria-hidden="true"
                className="mb-5 h-6 w-6 text-blue-600 dark:text-blue-300"
              />
              <h3 className="font-bold">{title}</h3>
              <p className="mt-3 text-sm leading-7 text-gray-500 dark:text-gray-400">
                {text}
              </p>
            </article>
          ))}
        </div>
      </section>
      <section
        aria-labelledby="landing-control"
        className="my-8 rounded-3xl bg-blue-50 p-6 sm:p-9 dark:bg-blue-500/10"
      >
        <h2 id="landing-control" className="text-2xl font-bold tracking-tight">
          Keep the creative control.
        </h2>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-gray-600 dark:text-gray-300">
          Review your scenes, correct captions, and preview before rendering.
          Build connected episodes with recurring characters, share finished
          videos through viewing links, or export an editable project ZIP to
          keep a portable copy.
        </p>
        <p className="mt-3 max-w-3xl text-xs leading-6 text-gray-500 dark:text-gray-400">
          AI tools use your connected providers. Provider usage may be billed
          separately; you can also work with your own media without AI. Your
          project is private unless you choose to share or publish it.
        </p>
        <Link
          to="/guide/"
          className="mt-5 inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-blue-700 hover:underline dark:text-blue-300"
        >
          Explore the guide
          <HiOutlineArrowRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      </section>
    </main>
  );
}
