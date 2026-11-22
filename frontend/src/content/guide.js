export const guideTopics = [
  {
    id: "start",
    group: "Start here",
    title: "Make your first video",
    description: "A simple walkthrough using photos or clips you already have.",
    needs: "One or two photos or short clips. No API keys needed.",
    result: "A saved project and a finished video you can watch and share.",
    steps: [
      [
        "Open a blank project",
        "Choose Edit your own media from Create. Give the project a name and choose its format: portrait for a vertical video, or landscape for a wider frame.",
      ],
      [
        "Add your first scene",
        "Choose Add scene and upload a photo or clip. Start with just one or two scenes so you can learn the editor before building a longer video.",
      ],
      [
        "Set the pace",
        "Select a scene and open Timing. Set how long a still image stays on screen. Use the storyboard below the scene to select or reorder your scenes.",
      ],
      [
        "Add sound if you want it",
        "Open Audio to upload a recorded voiceover. For background music, open Project extras. You can also leave your first video silent.",
      ],
      [
        "Preview, then export",
        "Wait for saving to finish. Choose Preview video to check your edit, then Export → Video to render it. When the export is ready, choose Watch export.",
      ],
    ],
    tip: "Keep the first project small. You can come back, add more scenes, and export again.",
    action: ["/manual/", "Start with my own media"],
    related: ["edit", "preview-export", "sharing"],
  },
  {
    id: "providers",
    group: "Start here",
    title: "Connect your AI providers",
    description: "Set up the services your chosen creation tool needs.",
    needs:
      "Your own provider account, an API key, model access, and available provider credit.",
    result: "The required providers are connected before you start generating.",
    steps: [
      [
        "Open provider settings",
        "Open the account menu and choose API keys and providers. Add the keys needed for the text, voice, and visual providers you want to use.",
      ],
      [
        "Choose the matching services",
        "In the creation form, select providers and models covered by your keys. An active key does not automatically give you access to every model.",
      ],
      [
        "Try a small project",
        "Start with a short script and a few scenes. Review the result before generating more media. Provider requests and repeated retries may incur charges on your provider account.",
      ],
    ],
    tip: "Never put a key in a prompt, script, screenshot, or support message. You can use the manual editor without an AI provider. Presenter availability depends on your workspace.",
    action: ["/api-keys/", "Open provider settings"],
    related: ["ai", "start", "troubleshooting"],
  },
  {
    id: "ai",
    group: "Create a video",
    title: "Turn an idea into a video",
    description: "Use AI to draft a storyboard and prepare editable scenes.",
    needs:
      "An idea and connected providers for the text, voice, and visuals you select.",
    result:
      "An editable video project with scenes you can review before exporting.",
    steps: [
      [
        "Describe a small, clear idea",
        "Choose Create with AI. Say who the video is for, what it should explain or show, and the tone you want. Use a few scenes for your first attempt.",
      ],
      [
        "Choose the look and sound",
        "Select the format, voice, and visual provider. Add a reference image if it helps describe the subject or style. Check provider access before continuing.",
      ],
      [
        "Review before generating",
        "Review the creation choices and draft the storyboard. Check narration and visual descriptions together; correct mistakes before approving media generation.",
      ],
      [
        "Refine the prepared scenes",
        "Wait for preparation to finish, then select scenes in the editor. Regenerate only the parts you want to change, save, and preview before exporting.",
      ],
    ],
    tip: "A queued job is still processing. Return through My videos to check its status; avoid submitting the same idea repeatedly while it is working.",
    action: ["/ai/", "Create with AI"],
    related: ["providers", "edit", "preview-export"],
  },
  {
    id: "text",
    group: "Create a video",
    title: "Start from a script or narration",
    description: "Build visuals around words you have already prepared.",
    needs:
      "A script or spoken MP3/WAV, plus the providers required by your selected options.",
    result: "Scenes based on your narration, ready for editing.",
    steps: [
      [
        "Choose Narration to video",
        "Paste your script or upload spoken audio. Keep the language and purpose clear; check the text before asking AI to plan scenes.",
      ],
      [
        "Review the scene plan",
        "Choose the look, sound, and format. Read the proposed narration and visual descriptions before continuing with media generation.",
      ],
      [
        "Check words against the visuals",
        "In the editor, preview the narration, adjust scene pacing, and review captions. If a word is wrong, save the correction and wait for any audio update to finish.",
      ],
    ],
    tip: "Transcription requirements depend on the workspace’s configured provider. Check the error shown if an uploaded recording cannot be transcribed.",
    action: ["/text/", "Open Narration to video"],
    related: ["providers", "edit", "preview-export"],
  },
  {
    id: "series",
    group: "Create a video",
    title: "Build a recurring series",
    description: "Keep characters, style, and episode history together.",
    needs:
      "A series idea, connected AI providers, and references for any recurring characters you add.",
    result: "A series workspace containing connected episode projects.",
    steps: [
      [
        "Set up the series",
        "Choose Create a series. Describe the cast, world, and shared style. Add character details and references where they help keep the appearance consistent.",
      ],
      [
        "Review the characters",
        "Approve character images before drafting an episode where required. A reference guides generation; check each shot rather than assuming every detail will match.",
      ],
      [
        "Draft an episode",
        "Describe what should happen next. Review its storyboard, prepare the scenes, and edit the video through the normal scene editor.",
      ],
      [
        "Review episode memory",
        "Check the saved episode summary before using it as history for the next episode. Update it when the story changes so later drafts have the right context.",
      ],
    ],
    tip: "Later series changes do not silently replace the cast or media already saved in an existing episode.",
    action: ["/series/", "Open My series"],
    related: ["ai", "edit", "troubleshooting"],
  },
  {
    id: "story",
    group: "Create a video",
    title: "Tell a story over gameplay",
    description: "Combine narration, a looping background, and captions.",
    needs:
      "A gameplay clip you can use and a connected voice provider for generated narration.",
    result: "A narrated story video with a reusable background.",
    steps: [
      [
        "Choose your background",
        "Open Story over gameplay. Upload or select the gameplay clip you want behind the story.",
      ],
      [
        "Prepare the story and voice",
        "Enter the story, choose a voice, and review the available caption and format choices before creating the project.",
      ],
      [
        "Check the whole video",
        "Preview the narration and captions against the background. Adjust sound levels and export when the pacing is right.",
      ],
    ],
    tip: "Use footage and music you have permission to use. Review the finished export before publishing it.",
    action: ["/story/", "Open Story over gameplay"],
    related: ["providers", "preview-export", "publish"],
  },
  {
    id: "clips",
    group: "Create a video",
    title: "Turn a long video into Shorts",
    description: "Find and polish highlights from speech-based video.",
    needs:
      "A video upload or public YouTube link, and the providers required for transcription and AI suggestions.",
    result: "Short clips with reviewed boundaries, framing, and captions.",
    steps: [
      [
        "Create a clip project",
        "Open Long video → Shorts and choose New project. Upload the video or paste its YouTube link. Set preferred clip lengths and, optionally, a processing range or description of the moments you want.",
      ],
      [
        "Wait for the transcript and suggestions",
        "The app checks for suitable YouTube captions before transcribing audio where needed. You can leave and return to the saved project while processing finishes.",
      ],
      [
        "Choose a complete moment",
        "Open Transcript & AI search to find another moment. Use Add clip, Add selected, or Add and edit clip to keep a result. Add clip manually lets you choose your own times.",
      ],
      [
        "Refine before exporting",
        "Check that the clip makes sense without the surrounding video. Adjust its trim and portrait framing, correct the captions, and export. Keep decimal seconds when entering precise boundaries.",
      ],
    ],
    tip: "Changing the trim rebuilds captions from the source transcript. Review your words and timing after a trim change.",
    action: ["/clips/", "Open My clips"],
    related: ["providers", "captions", "troubleshooting"],
  },
  {
    id: "captions",
    group: "Create a video",
    title: "Caption an existing video",
    description: "Add styled captions without rebuilding the video as scenes.",
    needs:
      "A video with speech and access to the configured transcription provider.",
    result: "A captioned export with reviewed words and timing.",
    steps: [
      [
        "Upload your video",
        "Choose Add captions from Create and upload a video with clear speech. Wait for transcription to finish.",
      ],
      [
        "Read and correct the words",
        "Review the transcript while listening. Correct spelling and timing rather than relying on the first transcription.",
      ],
      [
        "Choose a readable style",
        "Pick the caption appearance and placement, check it against the video, and export the finished version.",
      ],
    ],
    tip: "For captions inside a scene-based project, use the editor’s Captions tab instead of creating a separate caption project.",
    action: ["/captions/", "Open Add captions"],
    related: ["edit", "providers", "clips"],
  },
  {
    id: "edit",
    group: "Edit & finish",
    title: "Find your way around the editor",
    description:
      "Select a scene, change one thing, save, and preview the result.",
    needs: "A saved video project from My videos.",
    result: "Your scene changes are saved and ready to preview.",
    steps: [
      [
        "Select a scene",
        "Use the storyboard below the scene to move between shots. Reorder scenes with the drag handle or the available keyboard controls.",
      ],
      [
        "Edit Script and Visual",
        "Script changes the scene text. Choose Save text, or press Ctrl/⌘ + Enter, to commit it; generated narration may update. Visual lets you choose, upload, or regenerate the scene’s image or clip.",
      ],
      [
        "Review Audio and Captions",
        "Audio controls the scene’s sound and voiceover. Captions controls the displayed words and their appearance. Listen while reviewing so the words and timing agree.",
      ],
      [
        "Set Timing and finishing touches",
        "Timing controls scene duration and pauses. Use the available transition and motion tools for how scenes move and connect. Open Project extras for background music and Settings for overall format and appearance.",
      ],
      [
        "Wait for saving, then preview",
        "A text draft is not a saved edit. Wait until changes finish saving before Preview video or Export. Editing scenes does not automatically update a completed export.",
      ],
    ],
    tip: "You can find reusable files in My assets. Your project stays private unless you create a share link or publish its video.",
    action: ["/videos/", "Open My videos"],
    related: ["preview-export", "sharing", "troubleshooting"],
  },
  {
    id: "preview-export",
    group: "Edit & finish",
    title: "Preview and export a video",
    description:
      "Understand the difference between the current edit and a finished render.",
    needs:
      "Saved scenes, completed processing, and any narration you want included.",
    result: "A finished video export you have watched and checked.",
    steps: [
      [
        "Check Preview video",
        "Preview video shows the saved edit. Check scene order, framing, narration, captions, and transitions before spending time rendering.",
      ],
      [
        "Choose Export → Video",
        "Select quality and frame rate. Review any missing-narration warning; retry the audio in the affected scene or continue with the available audio if that is what you want.",
      ],
      [
        "Wait for rendering to finish",
        "You can return to the project through My videos. When the render is ready, choose Watch export to check the completed video.",
      ],
      [
        "Export again after editing",
        "Watch export plays the latest completed render. Later scene changes are only included after another export.",
      ],
    ],
    tip: "Choose Project ZIP when you want an editable backup. It is a different output from a finished video.",
    action: ["/videos/", "Choose a project to export"],
    related: ["sharing", "publish", "backup"],
  },
  {
    id: "sharing",
    group: "Edit & finish",
    title: "Share a finished export",
    description: "Let someone watch the video without an account.",
    needs: "A completed export that you have reviewed.",
    result: "A viewing link with an optional expiry that you can revoke.",
    steps: [
      [
        "Open Share link",
        "Use the share icon in the editor. Choose an expiry if you want the link to stop working after a set time.",
      ],
      [
        "Create and check the link",
        "Choose Create share link, then Copy link. Open the shared page and check the video and its title, description, and tags before sending it.",
      ],
      [
        "Control future access",
        "Anyone with the link can watch without signing in. Choose Stop sharing to revoke it. Revoking a link cannot remove copies someone has already saved.",
      ],
    ],
    tip: "Send the share URL, not the address of your editor. Sharing does not give viewers access to your project editing tools or provider keys.",
    action: ["/videos/", "Open a video to share"],
    related: ["preview-export", "publish", "backup"],
  },
  {
    id: "publish",
    group: "Edit & finish",
    title: "Publish to a connected account",
    description:
      "Review the post details before sending a finished video to a platform.",
    needs:
      "A finished export and a supported social account connected in this workspace.",
    result: "A reviewed publishing request with a status you can follow.",
    steps: [
      [
        "Connect your account",
        "Open Connections from the account menu. Connect a supported platform; the available options depend on workspace configuration.",
      ],
      [
        "Review the post",
        "Return to the exported video and open the publishing action from More actions. Choose the account and review the video, title, description, and other platform options.",
      ],
      [
        "Follow the publishing status",
        "Confirm only when the details are right. If a connection has expired, reconnect it. If the app asks you to check the platform, look there before retrying to avoid duplicate posts.",
      ],
    ],
    tip: "A publishing request is not proof that the post is live. Check the final status and platform result.",
    action: ["/connections/", "Open Connections"],
    related: ["preview-export", "sharing", "troubleshooting"],
  },
  {
    id: "backup",
    group: "Edit & finish",
    title: "Export or import an editable project",
    description: "Keep a portable copy with the project’s media and settings.",
    needs:
      "A saved project to export, or a Viddie Project ZIP smaller than 1 GB to import.",
    result: "An editable backup, or a new private copy in your library.",
    steps: [
      [
        "Download the project ZIP",
        "In the editor, choose Export → Project ZIP. Include the finished video if you want that saved render in the archive, then download the ZIP.",
      ],
      [
        "Keep the archive intact",
        "The ZIP contains project.json and the media it references. Keep them together; changing file contents or removing files can make verification fail during import.",
      ],
      [
        "Import into My videos",
        "Open My videos → Import project. Choose the ZIP and wait while it is uploaded, verified, and restored. Both the archive and its unpacked contents must fit within 1 GB.",
      ],
      [
        "Review the new project",
        "Import creates a new private project without replacing the original. Preview its scenes, and choose an available voice in Settings before regenerating narration.",
      ],
    ],
    tip: "Project ZIPs exclude provider credentials and public share links. A downloaded MP4 alone does not contain the editable scene project.",
    action: ["/videos/", "Open My videos"],
    related: ["preview-export", "providers", "troubleshooting"],
  },
  {
    id: "troubleshooting",
    group: "Get unstuck",
    title: "Fix a problem without starting over",
    description: "Check the saved project and the error before retrying work.",
    needs: "The affected project and the message shown by the app.",
    result: "A next step that protects the work already saved.",
    steps: [
      [
        "Read the message and project status",
        "A failed export does not necessarily mean the scenes are damaged. Open the saved project and review its available actions before creating another copy.",
      ],
      [
        "Fix the affected part",
        "Check provider access for provider errors, narration for missing audio, or the saved scene edits for an older export. Retry only the part that failed when the app offers that option.",
      ],
      [
        "Ask for help with a reference",
        "If the problem continues, contact support with the project ID, the visible error or request reference, and what you were doing. Leave out API keys and private provider responses.",
      ],
    ],
    tip: "Repeated generation retries can incur provider charges. Keep the existing project so completed media can be reused where supported.",
    action: ["/contact/", "Contact support"],
    related: ["providers", "edit", "preview-export"],
  },
];

export const guideProblems = [
  [
    "Export is disabled",
    "Wait for saving and processing to finish. Video rendering needs ready scenes; Project ZIP can back up an editable draft. Review any failure message before retrying.",
  ],
  [
    "Narration is missing",
    "Retry narration in the affected scene after checking the selected voice provider. If you choose to render without it, review which scenes will have no narration.",
  ],
  [
    "The export shows an older edit",
    "Save your scene changes and export again. Watch export opens the latest completed render, not a live preview of unsaved edits.",
  ],
  [
    "A provider rejects the request",
    "Check the selected provider, model access, key validity, and account balance in API keys and providers before retrying.",
  ],
  [
    "A share link will not open",
    "Ask the owner to check that the export is complete and the link is active. Expired or revoked links no longer grant access. Copy the viewing link again from Share link.",
  ],
  [
    "Project import failed",
    "Use an unchanged Viddie Project ZIP. Check the 1 GB archive and unpacked limits, and read the error for missing media, an unsupported format, or failed verification. Existing projects are left untouched.",
  ],
];
