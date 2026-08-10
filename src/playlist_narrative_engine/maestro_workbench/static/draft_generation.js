(function () {
  "use strict";

  if (typeof window !== "undefined" && window.PneDraftGenerationPublication) {
    window.PneDraftGenerationPublication.state = "executing";
    if (typeof document !== "undefined") document.documentElement.dataset.draftGenerationPublication = "executing";
  }

  function validateResult(result) {
    if (!result || typeof result.available !== "boolean" || typeof result.message !== "string" || !Array.isArray(result.draft_tracks)) {
      throw new Error("The draft-track provider returned a malformed response.");
    }
    return result;
  }

  async function run(options) {
    const {button, status, loadingText, invoke, acceptDrafts} = options;
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = loadingText;
    status.textContent = `${loadingText}…`;
    try {
      const result = validateResult(await invoke());
      if (result.available) acceptDrafts(result.draft_tracks);
      status.textContent = result.message;
      return result;
    } catch (error) {
      const detail = error?.message || "Unknown provider failure.";
      status.textContent = `Draft generation did not complete. ${detail}`;
      throw error;
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }

  const api = {run, validateResult};
  if (typeof window !== "undefined") {
    window.DraftGenerationFlow = api;
    if (window.PneDraftGenerationPublication) {
      window.PneDraftGenerationPublication.state = "published";
      if (typeof document !== "undefined") document.documentElement.dataset.draftGenerationPublication = "published";
    }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
