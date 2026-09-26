# V5 interface and production guide

## Workspace layout

AI Media Studio V5 uses three resizable areas:

1. **Production settings** — canvas, provider choices, voice model, media, and independent audio levels.
2. **Script and scene editor** — write tagged script lines, build scenes, then change scene text, type, duration,
   or media before rendering.
3. **Production monitor** — displays incoming scene frames during a render and previews the finished MP4 visually.

The interface style menu changes the application itself without changing the exported video's render theme.
Available styles are Obsidian Neon, Violet Cinema, Ember Studio, and Arctic Light.

## Editing workflow

1. Choose YouTube 16:9 or Reel 9:16.
2. Write one scene per line using `Hook:`, `Intro:`, `Point:`, `Section:`, or `Outro:`.
3. Select **Build editable scenes**.
4. Select a scene to change its narration, type, duration, or media file.
5. Set voice and music volume independently.
6. Generate the video while watching the production monitor advance through the selected media.
7. Use **Preview** for embedded visual playback or **Open with sound** for synchronized playback.
8. Return to the scene editor, revise, and render a new version.

## Audio behavior

- **Voice volume** controls scene narration before final mixing. `100%` preserves the synthesized level.
- **Music volume** controls the backing track before the final mix. `24%` is the new practical default.
- The final soundtrack is normalized toward broadcast-friendly social-video loudness.
- Piper is the recommended private/offline neural voice. Edge TTS is the network neural option. Flite is retained
  only as a lightweight compatibility fallback.

## Preview boundary

The embedded monitor decodes the actual finished MP4 and displays its video frames. It intentionally does not create
a second audio-output stack inside Tk. **Open with sound** launches the same MP4 in the operating system's player.
This keeps installation small and playback dependable while the future multitrack timeline is developed.

## Output

Every run produces an H.264/AAC MP4, `project.json`, and `provider-catalog.json`. YouTube Audio Library projects also
produce `video-description.txt` containing the saved attribution text.
