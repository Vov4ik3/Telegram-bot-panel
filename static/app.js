const STATUS_GLYPH = {
  online: "\u25CF",       // ●
  offline: "\u25CB",      // ○
  crashed: "\u2715",      // ✕
  launch_failed: "\u26A0", // ⚠
};

const STATUS_LABEL = {
  online: "Running",
  offline: "Stopped",
  crashed: "Crashed",
  launch_failed: "Launch failed",
};

const botList = document.getElementById("bot-list");
const rowTemplate = document.getElementById("bot-row-template");

const addToggle = document.getElementById("add-toggle");
const addForm = document.getElementById("add-form");
const addCancel = document.getElementById("add-cancel");
const addSubmit = document.getElementById("add-submit");
const folderInput = document.getElementById("folder-path");
const displayNameField = document.getElementById("display-name-field");
const displayNameInput = document.getElementById("display-name");
const addError = document.getElementById("add-error");

const openDetails = new Set(); // bot ids whose detail panel is expanded
const openLogs = new Set();    // bot ids whose log is additionally expanded
const rows = new Map();        // bot id -> refs into its persistent DOM node

addToggle.addEventListener("click", () => {
  addForm.classList.toggle("hidden");
  addError.classList.add("hidden");
});

addCancel.addEventListener("click", () => {
  addForm.classList.add("hidden");
  folderInput.value = "";
  displayNameInput.value = "";
  displayNameField.classList.add("hidden");
  addError.classList.add("hidden");
});

addSubmit.addEventListener("click", async () => {
  const folder_path = folderInput.value.trim();
  const display_name = displayNameInput.value.trim();
  if (!folder_path) {
    showAddError("Folder path is required.");
    return;
  }

  const res = await fetch("/api/bots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path, display_name }),
  });
  const data = await res.json();

  if (!res.ok) {
    showAddError(data.error || "Failed to add bot.");
    if (data.needs_display_name) displayNameField.classList.remove("hidden");
    return;
  }

  addCancel.click();
  await refresh();
});

function showAddError(msg) {
  addError.textContent = msg;
  addError.classList.remove("hidden");
}

async function refresh() {
  const res = await fetch("/api/bots");
  const bots = await res.json();
  render(bots);
}

function buildRow(bot) {
  const node = rowTemplate.content.cloneNode(true);
  const article = node.querySelector(".bot-row");

  const refs = {
    article,
    glyph: node.querySelector(".glyph"),
    name: node.querySelector(".name"),
    detail: node.querySelector(".bot-detail"),
    state: node.querySelector(".state"),
    description: node.querySelector(".description"),
    staticName: node.querySelector(".static-name"),
    folder: node.querySelector(".folder"),
    entrypoint: node.querySelector(".entrypoint"),
    logToggle: node.querySelector(".log-toggle"),
    log: node.querySelector(".log"),
  };

  node.querySelector(".bot-summary").addEventListener("click", (e) => {
    if (e.target.closest(".actions")) return;
    toggleDetail(bot.id, refs);
  });

  refs.logToggle.addEventListener("click", () => toggleLog(bot.id, refs));

  node.querySelector(".open-log-tab").addEventListener("click", () => {
    window.open(`/api/bots/${bot.id}/log/raw`, "_blank");
  });

  node.querySelector(".clear-log").addEventListener("click", async () => {
    if (!confirm(`Clear the log for "${refs.name.textContent}"? This can't be undone.`)) return;
    const res = await fetch(`/api/bots/${bot.id}/log/clear`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json();
      alert(data.error || "Failed to clear log.");
      return;
    }
    if (openLogs.has(bot.id)) {
      loadLog(bot.id, refs.log);
    }
  });

  node.querySelector(".start").addEventListener("click", async () => {
    await fetch(`/api/bots/${bot.id}/start`, { method: "POST" });
    refresh();
  });

  node.querySelector(".stop").addEventListener("click", async () => {
    await fetch(`/api/bots/${bot.id}/stop`, { method: "POST" });
    refresh();
  });

  node.querySelector(".rename").addEventListener("click", async () => {
    const current = refs.name.textContent;
    const newName = prompt("New display name:", current);
    if (!newName || newName.trim() === current) return;
    const res = await fetch(`/api/bots/${bot.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ display_name: newName.trim() }),
    });
    if (!res.ok) {
      const data = await res.json();
      alert(data.error || "Rename failed.");
    }
    refresh();
  });

  node.querySelector(".delete").addEventListener("click", async () => {
    if (!confirm(`Delete "${refs.name.textContent}"? This only removes it from the panel, not its files.`)) return;
    await fetch(`/api/bots/${bot.id}`, { method: "DELETE" });
    refresh();
  });

  botList.appendChild(node);
  return refs;
}

function toggleDetail(botId, refs) {
  if (openDetails.has(botId)) {
    openDetails.delete(botId);
    refs.detail.classList.add("hidden");
  } else {
    openDetails.add(botId);
    refs.detail.classList.remove("hidden");
  }
}

function toggleLog(botId, refs) {
  if (openLogs.has(botId)) {
    openLogs.delete(botId);
    refs.log.classList.add("hidden");
    refs.logToggle.textContent = "Show log";
  } else {
    openLogs.add(botId);
    refs.log.classList.remove("hidden");
    refs.logToggle.textContent = "Hide log";
    loadLog(botId, refs.log);
  }
}

function updateRow(bot, refs) {
  refs.glyph.textContent = STATUS_GLYPH[bot.status] || "?";
  refs.glyph.className = "glyph " + bot.status;
  refs.glyph.title = STATUS_LABEL[bot.status] || bot.status;

  refs.name.textContent = bot.display_name;
  refs.state.textContent = STATUS_LABEL[bot.status] || bot.status;
  refs.state.className = "state " + bot.status;
  refs.description.textContent = bot.description || "(none)";
  refs.staticName.textContent = bot.static_name;
  refs.folder.textContent = bot.folder_path;
  refs.entrypoint.textContent = bot.entrypoint;

  refs.detail.classList.toggle("hidden", !openDetails.has(bot.id));

  if (openLogs.has(bot.id)) {
    loadLog(bot.id, refs.log); // node persists across polls, so this just updates text - no flash
  }
}

function render(bots) {
  const seenIds = new Set();

  const existingEmpty = botList.querySelector(".empty");

  if (bots.length === 0) {
    if (!existingEmpty) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No bots registered yet. Add one to get started.";
      botList.appendChild(empty);
    }
  } else if (existingEmpty) {
    existingEmpty.remove();
  }

  bots.forEach((bot, index) => {
    seenIds.add(bot.id);
    let refs = rows.get(bot.id);
    if (!refs) {
      refs = buildRow(bot);
      rows.set(bot.id, refs);
    }
    updateRow(bot, refs);
    // Only touch the DOM position if it's actually out of order - moving a
    // node (even to the same spot) clears any active text selection inside
    // it, which was silently undoing the log-selection protection above.
    if (botList.children[index] !== refs.article) {
      botList.insertBefore(refs.article, botList.children[index] || null);
    }
  });

  // remove rows for bots that no longer exist (e.g. deleted from another tab)
  for (const [id, refs] of rows) {
    if (!seenIds.has(id)) {
      refs.article.remove();
      rows.delete(id);
      openDetails.delete(id);
      openLogs.delete(id);
    }
  }
}

async function loadLog(botId, logEl) {
  // Don't disrupt an active text selection inside this log - let the user
  // finish copying before the next poll overwrites it.
  const selection = document.getSelection();
  if (selection && !selection.isCollapsed && logEl.contains(selection.anchorNode)) {
    return;
  }

  const res = await fetch(`/api/bots/${botId}/log`);
  const data = await res.json();
  const text = data.log || "(no output yet)";
  if (logEl.textContent === text) return;

  // Replacing textContent resets scrollTop to 0 as a side effect - capture
  // state first so we can restore a sensible position after.
  const wasAtBottom = logEl.scrollHeight - logEl.scrollTop <= logEl.clientHeight + 20;
  const prevScrollHeight = logEl.scrollHeight;
  const prevScrollTop = logEl.scrollTop;

  logEl.textContent = text;

  if (wasAtBottom) {
    logEl.scrollTop = logEl.scrollHeight; // keep following live output
  } else {
    // preserve relative position instead of snapping back to the top
    const delta = logEl.scrollHeight - prevScrollHeight;
    logEl.scrollTop = prevScrollTop + delta;
  }
}

refresh();
setInterval(refresh, 2000);
