document.addEventListener("DOMContentLoaded", function () {
  // Setup Ace editor
  const editor = ace.edit("editor");
  editor.setTheme("ace/theme/textmate");
  editor.session.setMode("ace/mode/text");
  // enable vim keybindings
  try {
    editor.setKeyboardHandler("ace/keyboard/vim");
  } catch (e) {
    console.warn("Vim keybinding not loaded", e);
  }

  // initial content
  editor.setValue(INITIAL_OVERLAY || "", -1);
  const titleInput = document.getElementById("title-input");
  titleInput.value = INITIAL_TITLE || "";

  const thumbOverlay = document.getElementById("thumb-overlay");
  const thumbImg = document.getElementById("thumb-img");

  // update overlay live
  editor.session.on('change', function () {
    const txt = editor.getValue();
    thumbOverlay.textContent = txt;
  });

  // Save button
  document.getElementById("save-btn").addEventListener("click", async () => {
    const overlay = editor.getValue();
    const title = titleInput.value;
    try {
      const resp = await fetch(`/api/video/${VIDEO_ID}/save_overlay`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ overlay_text: overlay, title })
      });
      const data = await resp.json();
      if (data.ok) {
        alert("Saved.");
      } else {
        alert("Save failed");
      }
    } catch (e) {
      console.error(e);
      alert("Error saving overlay");
    }
  });

  // Delete video from detail page
  document.getElementById("delete-btn").addEventListener("click", async () => {
    if (!confirm("Delete this video?")) return;
    try {
      const resp = await fetch(`/api/video/${VIDEO_ID}/delete`, { method: "POST" });
      const data = await resp.json();
      if (data.ok) {
        window.location.href = "/";
      } else {
        alert("Delete failed");
      }
    } catch (e) {
      console.error(e);
      alert("Error deleting");
    }
  });
});
