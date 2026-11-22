# In-app guide

Open **Resources → Guide**, or visit `/guide/`. The guide is also available before
sign-in; its tool links use the app's existing authentication flow.

Choose a starting point or a topic to read one walkthrough at a time. Each guide
lists prerequisites, an expected outcome, numbered steps, and the next relevant
action. Desktop navigation groups topics by task. On mobile, use **Choose a guide**.

**Search the guide** searches walkthrough instructions and troubleshooting answers,
not just topic titles. Select a result to open its full steps; clear search to
return to the selected topic. Topic URLs such as `/guide/#edit` can be bookmarked
or shared, and browser Back/Forward navigates between topics. Existing guide anchors
remain valid.

The first walkthrough uses the manual editor and needs no API keys. Other topics
cover provider setup, AI creation, narration, series, gameplay stories, short clips,
captioning, scene editing, video exports, sharing, publishing, project ZIPs, and
troubleshooting. The editor map is a simplified orientation diagram, not an
interactive editor or a screenshot.

Walkthrough copy lives in `frontend/src/content/guide.js`; the guide interface is in
`frontend/src/pages/GuidePage.js`. Keep action labels, routes, prerequisites, and
failure advice aligned with the actual tools when changing a workflow. Do not add
credentials, private project screenshots, or real user content to guide examples.
