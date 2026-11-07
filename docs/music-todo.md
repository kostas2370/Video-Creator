# To do: music discovery and generation

Goal: help users choose a soundtrack without first building a large local library.
Reuse the existing music preview, library, and project attachment workflow.

## Music search

- [ ] Evaluate an external music catalog, starting with Jamendo. Confirm API access
      and licensing for use in videos created through this app before integration.
- [ ] Search by text, mood, genre, and instrumental/vocal preference.
- [ ] Preview search results and show the source, artist, and license requirements.
- [ ] Import the selected track and retain its provider ID and license metadata.
- [ ] Suggest editable search terms from the storyboard.

## AI-generated music

- [ ] Evaluate an official music generation API, starting with ElevenLabs.
- [ ] Add a Generate music option with an editable prompt, duration, and
      instrumental preference. Offer a prompt suggested from the storyboard.
- [ ] Show the estimated cost before starting a paid request.
- [ ] Generate in the background with progress, failure handling, and protection
      against duplicate requests.
- [ ] Preview the result before applying it; keep the current soundtrack until
      the user chooses its replacement.
- [ ] Save generated tracks to the user's library for reuse, including the prompt,
      provider, model, duration, and applicable usage information.

Suggested build order: AI generation and preview first, external catalog search
after confirming a suitable provider agreement.
