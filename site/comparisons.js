// Each comparison owns its slider and clipping boundary. No libraries or saved state.
for (const comparison of document.querySelectorAll("[data-comparison]")) {
  const stage = comparison.querySelector(".comparison-stage");
  const slider = comparison.querySelector('input[type="range"]');
  const output = comparison.querySelector("output");

  function setSplit(value) {
    const percent = Math.max(0, Math.min(100, Math.round(value)));
    slider.value = String(percent);
    stage.style.setProperty("--split", `${percent}%`);
    slider.setAttribute(
      "aria-valuetext",
      `${percent}% Original, ${100 - percent}% Modern`,
    );
    output.value = `${percent}%`;
  }

  function moveDivider(event) {
    const bounds = stage.getBoundingClientRect();
    if (bounds.width > 0)
      setSplit(((event.clientX - bounds.left) / bounds.width) * 100);
  }

  slider.addEventListener("input", () => setSplit(Number(slider.value)));
  stage.addEventListener("pointerdown", (event) => {
    if (!event.isPrimary || event.button !== 0) return;
    stage.setPointerCapture(event.pointerId);
    moveDivider(event);
  });
  stage.addEventListener("pointermove", (event) => {
    if (stage.hasPointerCapture(event.pointerId)) moveDivider(event);
  });
  stage.addEventListener("pointerup", (event) => {
    if (stage.hasPointerCapture(event.pointerId))
      stage.releasePointerCapture(event.pointerId);
  });
  setSplit(Number(slider.value));
}
