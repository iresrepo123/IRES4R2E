(() => {
  const TASKS = window.ANNOTATION_TASKS;
  const BATCH_SIZE = 25;
  const $ = (id) => document.getElementById(id);
  const state = { participantId: "", batch: 0, tasks: [], index: 0, startedAt: 0, taskStartedAt: 0 };

  if (!Array.isArray(TASKS) || TASKS.length !== 500) {
    $("welcome-error").textContent = "Task data did not load correctly. Keep annotation_tasks.js beside index.html.";
    $("start-button").disabled = true;
    return;
  }

  const hash = (value) => {
    let h = 2166136261;
    for (let i = 0; i < value.length; i++) h = Math.imul(h ^ value.charCodeAt(i), 16777619);
    return h >>> 0;
  };
  const shuffled = (items, seed) => {
    const result = [...items]; let x = hash(seed);
    for (let i = result.length - 1; i > 0; i--) {
      x = (Math.imul(1664525, x) + 1013904223) >>> 0;
      const j = x % (i + 1); [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  };
  const storageKey = () => `rq1-annotation:${state.participantId}:batch:${state.batch}`;
  const labels = "ABCDEFGHI".split("");
  const elapsedSeconds = () => Math.round((Date.now() - state.taskStartedAt) / 1000);

  function loadProgress() {
    try { return JSON.parse(localStorage.getItem(storageKey())) || {}; } catch { return {}; }
  }
  function saveProgress() {
    const progress = loadProgress();
    const task = state.tasks[state.index];
    progress[task.sample_id] = { order: currentOrder(), seconds: (progress[task.sample_id]?.seconds || 0) + elapsedSeconds() };
    localStorage.setItem(storageKey(), JSON.stringify(progress));
    state.taskStartedAt = Date.now();
    $("save-status").textContent = "Saved locally.";
  }
  function currentOrder() {
    return [...$("ranking-list").children].map((card) => card.dataset.level);
  }
  function render() {
    const task = state.tasks[state.index]; const saved = loadProgress()[task.sample_id];
    $("function-name").textContent = task.function_name || `Method ${task.sample_id}`;
    $("code").textContent = task.code;
    const randomized = shuffled(task.summaries, `${state.participantId}:${task.sample_id}`);
    const byLevel = Object.fromEntries(randomized.map((item, index) => [item.level, { ...item, label: labels[index] }]));
    const order = saved?.order || randomized.map((item) => item.level);
    const list = $("ranking-list"); list.replaceChildren();
    order.forEach((level) => {
      const item = byLevel[level]; const card = document.createElement("li");
      card.className = "ranking-card"; card.draggable = true; card.dataset.level = level; card.dataset.label = item.label;
      card.innerHTML = `<div class="candidate-meta"><span class="rank-number"></span><span class="handle" title="Drag to reorder">⠿</span><span class="candidate-label">${item.label}</span></div><div class="summary"></div>`;
      card.querySelector(".summary").textContent = item.text;
      attachDragHandlers(card); list.append(card);
    });
    $("progress").textContent = `Task ${state.index + 1} of ${state.tasks.length}`;
    $("previous-button").disabled = state.index === 0;
    $("next-button").textContent = state.index === state.tasks.length - 1 ? "Finish batch" : "Next →";
    state.taskStartedAt = Date.now(); $("save-status").textContent = saved ? "Previous local progress restored." : "";
  }
  function attachDragHandlers(card) {
    card.addEventListener("dragstart", () => card.classList.add("dragging"));
    card.addEventListener("dragend", () => { card.classList.remove("dragging"); saveProgress(); });
    card.addEventListener("dragover", (event) => { event.preventDefault(); card.classList.add("drag-over"); });
    card.addEventListener("dragleave", () => card.classList.remove("drag-over"));
    card.addEventListener("drop", (event) => {
      event.preventDefault(); card.classList.remove("drag-over"); const dragging = $("ranking-list").querySelector(".dragging");
      if (dragging && dragging !== card) $("ranking-list").insertBefore(dragging, card);
    });
  }
  function exportCsv() {
    saveProgress(); const progress = loadProgress(); const header = ["participant_id", "batch", "sample_id", "function_name", "rank", "candidate_label", "context_level"];
    const rows = [header];
    state.tasks.forEach((task) => {
      const record = progress[task.sample_id]; if (!record) return;
      const randomized = shuffled(task.summaries, `${state.participantId}:${task.sample_id}`);
      const labelByLevel = Object.fromEntries(randomized.map((item, index) => [item.level, labels[index]]));
      record.order.forEach((level, index) => rows.push([state.participantId, state.batch, task.sample_id, task.function_name, index + 1, labelByLevel[level], level]));
    });
    const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\r\n") + "\r\n";
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" }); const link = document.createElement("a");
    link.href = URL.createObjectURL(blob); link.download = `RQ1_annotation_${state.participantId}_batch${state.batch}.csv`; link.click(); URL.revokeObjectURL(link.href);
  }
  $("start-button").addEventListener("click", () => {
    const id = $("participant-id").value.trim(); const batch = Number($("batch-number").value); const batchCount = Math.ceil(TASKS.length / BATCH_SIZE);
    if (!id || !Number.isInteger(batch) || batch < 1 || batch > batchCount) { $("welcome-error").textContent = `Enter an anonymous ID and a batch from 1 to ${batchCount}.`; return; }
    state.participantId = id; state.batch = batch; state.tasks = TASKS.slice((batch - 1) * BATCH_SIZE, batch * BATCH_SIZE); state.index = 0; state.startedAt = Date.now();
    $("participant-display").textContent = `Participant ${id}`; $("batch-display").textContent = batch; $("welcome").classList.add("hidden"); $("annotation").classList.remove("hidden"); render();
  });
  $("previous-button").addEventListener("click", () => { saveProgress(); if (state.index > 0) { state.index--; render(); } });
  $("next-button").addEventListener("click", () => { saveProgress(); if (state.index < state.tasks.length - 1) { state.index++; render(); } else { $("save-status").textContent = "Batch complete. Download your CSV and send it to the researcher."; exportCsv(); } });
  $("export-button").addEventListener("click", exportCsv);
})();
