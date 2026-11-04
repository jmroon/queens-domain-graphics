# Comparison website

The GitHub Pages site lives in `site/`. It is plain HTML, CSS and JavaScript with no
build dependencies. `.github/workflows/pages.yml` publishes only this directory
when its files change on `main`, or on a manual workflow run. Repository Settings
→ Pages must use GitHub Actions as its publishing source.

Preview from the repository root with `python -m http.server 8765 --directory site`,
then open `http://localhost:8765`. Check both comparison sliders by dragging the
image and using the range control's arrow keys, Home and End. Also check a narrow
mobile viewport, navigation anchors, expandable notes, images and download links.
For each fullscreen button, check dragging and keyboard controls, then both Close
and Escape. The slider value and keyboard focus should survive returning to the
page. Browsers that deny native fullscreen should still show the full-window
dialog; test this with an iframe whose `allow` attribute is `fullscreen 'none'`.

The JPEGs in `site/images/` are the maintainer's unretouched gameplay screenshots,
copied byte-for-byte from the Nexus release media. Do not regenerate or retouch
comparison images. Before = Original with Retro Resolution OFF; after = Modern.
Captures are sequential rather than identical frames, so small camera/animation
differences are expected. Both image layers must keep matching dimensions.

For a mod release, update the visible version, both download URLs and sizes, and
checksum link in `site/index.html`. Keep compatibility claims aligned with the
README and validation record. The generic latest-release link remains available
if the website's pinned downloads have not yet been updated.

No experimental DLSS, SSGI or AO settings belong in this public release page.
No trackers, external fonts, game saves or personal configuration are hosted.
