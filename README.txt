LUCKNOW LAND VIDEO - build on GitHub (iPad friendly)

WHAT YOU GET: lucknow_land_video.mp4 (1080p, Hindi voice, blue/amber vector scenes,
slow pans, ambient music), captions.srt (Hindi captions for YouTube), thumbnail.png.

STEPS (all in Safari + Files on iPad)
1. Files app: tap the zip to unzip it.
2. github.com > New repository (Private is fine) > create it.
3. Add file > Upload files. Select these from the unzipped folder:
   build_video.py, scenes.json, requirements.txt, README.txt  -> Commit.
4. The workflow file is a hidden ".github" folder that iPad cannot see, so:
   Add file > Create new file. In the name box type exactly:
       .github/workflows/build.yml
   (typing the slashes creates the folders). Open "github-workflow-build.yml.txt"
   from the unzipped folder, copy everything, paste it in, Commit.
5. Actions tab > "Build Lucknow land video" > Run workflow.
   Wait ~15-30 min.
6. Releases (right side of repo page) > open latest > download lucknow_land_video.mp4
   -> it saves to Files. Upload to YouTube Studio; add captions.srt as Hindi subtitles.

IMPORTANT - LENGTH
The narration in scenes.json is the script you gave me, word for word. Spoken calmly it is
only ~4-5 minutes, not 10. To reach 10 min, add more sentences to the "narration" fields
(examples, checklists, cost sums, mistakes) and edit "lines" (on-screen text). The build
prints the final length.

OPTIONS
- Female voice: in build_video.py change hi-IN-MadhurNeural to hi-IN-SwaraNeural
  (or ask me to).
- Your own voice: record each scene on iPad (Voice Memos), name files scene_01.m4a ...
  scene_12.m4a and upload them to the repo root. They replace the AI voice.
- Your own music (sitar/flute, royalty-free): upload as music.mp3 to the repo root.
  Without it, a soft ambient drone is used as a placeholder.
- Map scene is schematic (not to scale); the last scene says "यह निवेश सलाह नहीं है।".
  The 5-year growth claims in the script are predictions - check them before publishing.
