// Move the existing comparison into a modal so its slider state and handlers survive.
// Native fullscreen removes browser chrome; the modal also works without that API.
function addFullscreenControl(comparison) {
  const button = comparison.querySelector(".fullscreen-button");
  const openLabel = button.getAttribute("aria-label");
  const dialog = document.createElement("dialog");
  dialog.className = "comparison-dialog";
  dialog.setAttribute(
    "aria-label",
    comparison.querySelector("figcaption strong").textContent + " comparison",
  );
  document.body.append(dialog);

  let placeholder;
  let previousOverflow;
  let previousScroll;
  let enteredFullscreen = false;

  function handleFullscreenChange() {
    if (document.fullscreenElement === document.documentElement) {
      enteredFullscreen = true;
    } else if (enteredFullscreen && dialog.open) {
      dialog.close();
    }
  }

  async function openComparison() {
    previousScroll = { left: window.scrollX, top: window.scrollY };
    previousOverflow = document.body.style.overflow;
    placeholder = document.createElement("div");
    placeholder.style.height = `${comparison.getBoundingClientRect().height}px`;
    placeholder.style.marginTop = getComputedStyle(comparison).marginTop;
    comparison.replaceWith(placeholder);
    dialog.append(comparison);
    document.body.style.overflow = "hidden";
    button.textContent = "Close";
    button.setAttribute("aria-label", "Close fullscreen comparison");
    dialog.showModal();
    button.focus();
    enteredFullscreen = false;
    document.addEventListener("fullscreenchange", handleFullscreenChange);

    if (
      !document.fullscreenElement &&
      document.documentElement.requestFullscreen
    ) {
      try {
        await document.documentElement.requestFullscreen();
        // Closing while the browser processes the request must not leave it fullscreen.
        if (!dialog.open && document.fullscreenElement)
          await document.exitFullscreen();
      } catch {
        // Some embedded/mobile browsers deny fullscreen; keep the viewport-sized modal.
      }
    }
  }

  dialog.addEventListener("close", () => {
    document.removeEventListener("fullscreenchange", handleFullscreenChange);
    placeholder.replaceWith(comparison);
    document.body.style.overflow = previousOverflow;
    button.textContent = "Fullscreen";
    button.setAttribute("aria-label", openLabel);
    button.focus({ preventScroll: true });
    window.scrollTo({ ...previousScroll, behavior: "instant" });
    if (enteredFullscreen && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    enteredFullscreen = false;
  });

  button.hidden = false;
  button.addEventListener("click", () => {
    if (dialog.open) dialog.close();
    else openComparison();
  });
}

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
  addFullscreenControl(comparison);
}
