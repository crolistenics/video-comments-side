document.addEventListener("DOMContentLoaded", function () {
  const selectAllBtn = document.getElementById("select-all");
  const deselectAllBtn = document.getElementById("deselect-all");
  const deleteSelectedBtn = document.getElementById("delete-selected");

  function getCheckboxes() {
    return Array.from(document.querySelectorAll(".select-checkbox"));
  }

  selectAllBtn.addEventListener("click", () => {
    getCheckboxes().forEach(cb => cb.checked = true);
  });

  deselectAllBtn.addEventListener("click", () => {
    getCheckboxes().forEach(cb => cb.checked = false);
  });

  deleteSelectedBtn.addEventListener("click", async () => {
    const checked = Array.from(document.querySelectorAll(".video-card"))
      .filter(card => card.querySelector(".select-checkbox")?.checked)
      .map(card => parseInt(card.dataset.id));
    if (!checked.length) {
      alert("No videos selected.");
      return;
    }
    if (!confirm(`Delete ${checked.length} videos? This cannot be undone.`)) return;
    try {
      const resp = await fetch("/api/videos/bulk_delete", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ ids: checked })
      });
      const data = await resp.json();
      if (data.ok) {
        // remove deleted cards from DOM
        checked.forEach(id => {
          const el = document.querySelector(`.video-card[data-id='${id}']`);
          if (el) el.remove();
        });
      } else {
        alert("Delete failed");
      }
    } catch (e) {
      console.error(e);
      alert("Error while deleting");
    }
  });

  // per-card delete buttons
  document.querySelectorAll(".btn-delete").forEach(btn => {
    btn.addEventListener("click", async (ev) => {
      const id = btn.dataset.id;
      if (!confirm("Delete this video?")) return;
      try {
        const resp = await fetch(`/api/video/${id}/delete`, { method: "POST" });
        const data = await resp.json();
        if (data.ok) {
          const card = document.querySelector(`.video-card[data-id='${id}']`);
          if (card) card.remove();
        } else {
          alert("Delete failed");
        }
      } catch (e) {
        console.error(e);
        alert("Error while deleting");
      }
    });
  });
});
