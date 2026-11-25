import { useState } from "react";
import { Link } from "react-router-dom";
import {
  HiCheck,
  HiOutlineAdjustmentsHorizontal,
  HiOutlineFilm,
  HiOutlineScissors,
  HiOutlineShieldCheck,
  HiOutlineSparkles,
  HiPlay,
} from "react-icons/hi2";
import { PublicHeader } from "../components/PublicHeader";
import { VideoShowcase } from "../components/VideoShowcase";
import { useDeployment } from "../store/DeploymentContext";
import "./LandingPage.css";

const workflows = [
  {
    id: "plan",
    label: "Plan your story",
    icon: HiOutlineSparkles,
    eyebrow: "From a spark to a storyboard",
    title: "Give your idea a little direction.",
    description:
      "Start with an idea, a script, or a recording. Choose the look and sound, then review your storyboard before creating the media.",
    points: [
      "Review the script before generating",
      "Choose your visuals and narration",
      "Keep every scene editable",
    ],
    image: "/showcase/storyboard.png",
    alt: "Viddie storyboard review with an idea, scene count, and look and sound settings",
  },
  {
    id: "edit",
    label: "Make it yours",
    icon: HiOutlineAdjustmentsHorizontal,
    eyebrow: "The details make the difference",
    title: "Your first draft is just the beginning.",
    description:
      "Open the editor and get hands-on. Rewrite a line, change a visual, refine the timing, and bring the whole story together.",
    points: [
      "Arrange and refine individual scenes",
      "Shape captions, music, and motion",
      "Preview before the final render",
    ],
    image: "/showcase/editor.png",
    alt: "Viddie scene editor with an emu video preview, editable narration, and a scene timeline",
  },
  {
    id: "clips",
    label: "Find the highlights",
    icon: HiOutlineScissors,
    eyebrow: "There’s more in your footage",
    title: "Big recordings. Little moments that matter.",
    description:
      "Turn interviews, podcasts, and talks into shorter clips. Find moments in the transcript, adjust the framing, and refine the captions.",
    points: [
      "Start with a long-form recording",
      "Review and trim selected moments",
      "Frame your clips for a smaller screen",
    ],
    image: "/showcase/clips.png",
    alt: "Viddie clip workspace with a video transcript and controls for selecting highlights",
  },
];

export default function LandingPage({ theme, toggleTheme }) {
  const { invite_only: inviteOnly } = useDeployment();
  const [workflow, setWorkflow] = useState("edit");
  const selected = workflows.find((item) => item.id === workflow);
  const signupPath = inviteOnly ? "/request-access/" : "/register/";

  function navigateWorkflow(event, index) {
    let next;
    if (event.key === "ArrowRight") next = (index + 1) % workflows.length;
    else if (event.key === "ArrowLeft")
      next = (index + workflows.length - 1) % workflows.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = workflows.length - 1;
    else return;
    event.preventDefault();
    setWorkflow(workflows[next].id);
    event.currentTarget.parentElement
      .querySelectorAll('[role="tab"]')
      [next].focus();
  }

  return (
    <main className="landing-page">
      <a className="landing-skip" href="#landing-content">
        Skip to content
      </a>
      <PublicHeader theme={theme} toggleTheme={toggleTheme} home />

      <section
        id="landing-content"
        className="landing-hero landing-container"
        aria-labelledby="landing-title"
      >
        <div className="landing-hero-copy">
          <p className="landing-pill">
            <HiOutlineSparkles aria-hidden="true" />A little idea. A whole new
            possibility.
          </p>
          <h1 id="landing-title">
            Make something
            <br />
            <span>worth watching.</span>
          </h1>
          <p className="landing-hero-description">
            The creative studio for the stories in your head.
            <br className="landing-desktop-break" /> Turn ideas, scripts, and
            your own footage into videos that feel like <em>you.</em>
          </p>
          <div className="landing-hero-actions">
            <Link
              to={signupPath}
              className="landing-button landing-button-primary"
            >
              {inviteOnly ? "Request early access" : "Get started"}
              <HiOutlineSparkles aria-hidden="true" />
            </Link>
            <a
              href="#showcase"
              className="landing-button landing-button-secondary"
            >
              <HiPlay aria-hidden="true" />
              Watch the videos
            </a>
          </div>
          <p className="landing-hero-note">
            {inviteOnly ? (
              <>
                A small beta. A personal welcome.{" "}
                <Link to="/request-access/">Request an invitation</Link>.
              </>
            ) : (
              "Start with your own media. Connect your providers when you’re ready."
            )}
          </p>
          <div className="landing-hero-promises">
            <span>
              <HiCheck aria-hidden="true" />
              Your creative control
            </span>
            <span>
              <HiCheck aria-hidden="true" />
              Your choice of AI
            </span>
          </div>
        </div>
        <figure
          className="landing-film-composition"
          aria-label="Illustration of a Viddie video project using the featured Emu War video"
        >
          <div className="landing-film-glow" aria-hidden="true" />
          <div className="landing-film-backdrop" aria-hidden="true">
            <img
              src="/showcase/world-war-ii.jpg"
              alt=""
              width="480"
              height="360"
            />
            <span>Another story waiting to be told.</span>
          </div>
          <div className="landing-film-window">
            <div className="landing-window-bar">
              <span className="landing-window-brand">
                <HiOutlineFilm aria-hidden="true" />
                Your creative space
              </span>
              <span className="landing-window-label">Project illustration</span>
            </div>
            <div className="landing-film-image">
              <img
                src="/showcase/emu-war.jpg"
                alt="Australian soldiers in a field from the featured Great Emu War video"
                width="480"
                height="360"
              />
              <div className="landing-film-overlay">
                <span className="landing-film-tag">
                  A curious little piece of history
                </span>
                <p>
                  Small idea.
                  <br />
                  <em>Big story.</em>
                </p>
                <a href="#showcase" className="landing-film-watch">
                  <HiPlay aria-hidden="true" />
                  <span>Explore the films</span>
                </a>
              </div>
            </div>
            <div className="landing-mini-timeline" aria-hidden="true">
              <div className="landing-timeline-scenes">
                <img src="/showcase/emu-war.jpg" alt="" />
                <img src="/showcase/world-war-ii.jpg" alt="" />
                <div>
                  Your next
                  <br />
                  scene
                </div>
                <span className="landing-timeline-playhead" />
              </div>
              <div className="landing-audio-wave">
                {Array.from({ length: 34 }, (_, index) => (
                  <i
                    key={index}
                    style={{ height: `${6 + ((index * 7) % 17)}px` }}
                  />
                ))}
              </div>
              <div className="landing-caption-track">
                Every story starts with a little curiosity.
              </div>
            </div>
          </div>
          <figcaption className="landing-floating-note">
            <span>
              <HiOutlineSparkles aria-hidden="true" />
            </span>
            <div>
              <strong>From “what if” to “watch this”.</strong>
              <p>Scenes. Sound. A story of your own.</p>
            </div>
          </figcaption>
        </figure>
      </section>

      <div
        className="landing-capabilities landing-container"
        aria-label="Studio capabilities"
      >
        <p>
          One creative space.
          <br />
          <strong>So many ways to begin.</strong>
        </p>
        <div>
          {[
            [HiOutlineSparkles, "Idea to video"],
            [HiOutlineFilm, "Your own media"],
            [HiOutlineScissors, "Long video to Shorts"],
            [HiOutlineAdjustmentsHorizontal, "Captions & editing"],
          ].map(([Icon, label]) => (
            <span key={label}>
              <Icon aria-hidden="true" />
              {label}
            </span>
          ))}
        </div>
      </div>

      <div className="landing-container">
        <VideoShowcase />
      </div>

      <section
        id="workflow"
        className="landing-workflow landing-container"
        aria-labelledby="landing-workflow-title"
      >
        <div className="landing-section-heading">
          <p className="landing-eyebrow">Your idea has a place to grow</p>
          <h2 id="landing-workflow-title">
            A little AI magic.
            <br />
            <span>A lot of you.</span>
          </h2>
          <p>
            Get a helping hand with the first draft. Keep your hands on the
            final cut.
          </p>
        </div>
        <div
          className="landing-workflow-tabs"
          role="tablist"
          aria-label="Explore the Viddie studio"
        >
          {workflows.map((item, index) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`workflow-tab-${item.id}`}
              aria-selected={workflow === item.id}
              aria-controls="workflow-panel"
              tabIndex={workflow === item.id ? 0 : -1}
              onClick={() => setWorkflow(item.id)}
              onKeyDown={(event) => navigateWorkflow(event, index)}
            >
              <item.icon aria-hidden="true" />
              {item.label}
            </button>
          ))}
        </div>
        <div
          id="workflow-panel"
          role="tabpanel"
          aria-labelledby={`workflow-tab-${selected.id}`}
          tabIndex={0}
          className="landing-workflow-panel"
        >
          <div className="landing-workflow-copy">
            <p className="landing-eyebrow">{selected.eyebrow}</p>
            <h3>{selected.title}</h3>
            <p>{selected.description}</p>
            <ul>
              {selected.points.map((point) => (
                <li key={point}>
                  <HiCheck aria-hidden="true" />
                  {point}
                </li>
              ))}
            </ul>
            <Link to="/guide/" className="landing-inline-link">
              Take a look around the studio
            </Link>
          </div>
          <figure
            className={`landing-product-shot landing-product-shot-${selected.id}`}
          >
            <div className="landing-product-caption">
              <HiOutlineFilm aria-hidden="true" />
              <span>Inside Viddie</span>
              <span>Product preview</span>
            </div>
            <img
              key={selected.id}
              src={selected.image}
              alt={selected.alt}
              width={selected.id === "edit" ? 1512 : 1280}
              height={selected.id === "edit" ? 1559 : 1516}
              loading="lazy"
            />
            <figcaption>Actual Viddie interface · Example project</figcaption>
          </figure>
        </div>
      </section>

      <section
        className="landing-control landing-container"
        aria-labelledby="landing-control-title"
      >
        <div className="landing-control-intro">
          <span className="landing-feature-icon">
            <HiOutlineShieldCheck aria-hidden="true" />
          </span>
          <p className="landing-eyebrow">A studio on your terms</p>
          <h2 id="landing-control-title">
            Keep the part
            <br />
            that makes it yours.
          </h2>
          <p>
            Your ideas, your media, your decisions. Viddie gives you room to
            create your way.
          </p>
        </div>
        <div className="landing-control-features">
          {[
            [
              "Pick your creative partners.",
              "Connect your preferred AI providers for writing, voices, and visuals. Or start with your own photos and clips.",
            ],
            [
              "Make the final call.",
              "Review your storyboard before generating media. Rewrite, rearrange, and preview before the final render.",
            ],
            [
              "Share when you’re ready.",
              "Keep your project private, create a viewing link, or export an editable project ZIP for a portable copy.",
            ],
          ].map(([title, text]) => (
            <article key={title}>
              <HiCheck aria-hidden="true" />
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section
        className="landing-faq landing-container"
        aria-labelledby="landing-faq-title"
      >
        <div>
          <p className="landing-eyebrow">A few things to know</p>
          <h2 id="landing-faq-title">
            Curious?
            <br />
            Good place to start.
          </h2>
          <Link to="/contact/" className="landing-inline-link">
            Get in touch
          </Link>
        </div>
        <div className="landing-faq-list">
          {[
            [
              "Do I need AI provider keys?",
              "You can edit your own photos and clips without AI keys. AI writing, narration, and visual generation use your connected providers. Provider usage may be billed separately.",
            ],
            [
              "Can I edit what the AI creates?",
              "Yes. Review the storyboard, rewrite narration, replace visuals, adjust scene timing, and refine your captions before rendering.",
            ],
            [
              "How does early access work?",
              "Send an access request with your email and what you’d like to create. If approved, you’ll receive an invitation to register. You’ll still verify your email before signing in.",
            ],
            [
              "Are my projects public?",
              "Your projects are private unless you choose to share or publish them. Public viewing links let you share a finished video when you’re ready.",
            ],
          ]
            .filter(
              ([question]) =>
                inviteOnly || question !== "How does early access work?",
            )
            .map(([question, answer]) => (
              <details key={question}>
                <summary>
                  {question}
                  <span aria-hidden="true" />
                </summary>
                <p>{answer}</p>
              </details>
            ))}
        </div>
      </section>

      <section
        className="landing-final landing-container"
        aria-labelledby="landing-final-title"
      >
        <div className="landing-final-orbit" aria-hidden="true" />
        <p className="landing-eyebrow">You bring the idea.</p>
        <h2 id="landing-final-title">
          Let’s make it
          <br />
          <span>worth watching.</span>
        </h2>
        <p>
          That story you keep thinking about?
          <br />
          It deserves more than a note on your phone.
        </p>
        <Link to={signupPath} className="landing-button landing-button-primary">
          {inviteOnly ? "Request access" : "Create your account"}
          <HiOutlineSparkles aria-hidden="true" />
        </Link>
        <span className="landing-final-note">
          {inviteOnly
            ? "Thoughtful tools. A small beta. Your next big idea."
            : "Your own footage, or a little help from AI. You decide."}
        </span>
      </section>
      <div className="landing-endnote landing-container">
        <Link to="/" className="landing-brand">
          <img src="/viddie-icon.svg" alt="" width="28" height="28" />
          Viddie
        </Link>
        <p>A creative space for curious minds.</p>
        <Link to="/guide/">Explore the guide</Link>
      </div>
    </main>
  );
}
