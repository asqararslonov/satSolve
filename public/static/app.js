// SAT Solver Frontend Application
let selectedFiles = [];
let activeJob = null;

document.addEventListener("DOMContentLoaded", () => {
  initUI();
  loadConfig();
  loadPrompts();
});

function initUI() {
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const startBtn = document.getElementById("startPipelineBtn");
  const clearBtn = document.getElementById("clearFilesBtn");
  const openSettingsBtn = document.getElementById("openSettingsBtn");
  const closeSettingsBtn = document.getElementById("closeSettingsBtn");
  const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
  const saveSettingsBtn = document.getElementById("saveSettingsBtn");
  const settingsModal = document.getElementById("settingsModal");
  const downloadQuestionsBtn = document.getElementById("downloadQuestionsBtn");
  const downloadSolutionsBtn = document.getElementById("downloadSolutionsBtn");

  // Drag & Drop
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("border-indigo-500", "bg-slate-900/50");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("border-indigo-500", "bg-slate-900/50");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("border-indigo-500", "bg-slate-900/50");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  });

  clearBtn.addEventListener("click", () => {
    selectedFiles = [];
    fileInput.value = "";
    renderPreviewTray();
  });

  startBtn.addEventListener("click", startClientPipeline);

  // Settings modal
  openSettingsBtn.addEventListener("click", () => {
    settingsModal.classList.remove("hidden");
  });

  const closeSettings = () => settingsModal.classList.add("hidden");
  closeSettingsBtn.addEventListener("click", closeSettings);
  cancelSettingsBtn.addEventListener("click", closeSettings);

  saveSettingsBtn.addEventListener("click", async () => {
    await saveConfig();
    closeSettings();
  });

  downloadQuestionsBtn.addEventListener("click", () => {
    if (!activeJob) return;
    let md = `# Exam Questions\n\nTotal Questions Transcribed: ${activeJob.total_images}\n\n---\n\n`;
    activeJob.items.forEach((it) => {
      md += `${it.markdown_question || `### Question ${it.index}\n(Transcription pending)`}\n\n---\n\n`;
    });
    downloadFile(md, "questions.md");
  });

  downloadSolutionsBtn.addEventListener("click", () => {
    if (!activeJob) return;

    // Build Simple Answer Key: 1.A, 2.B, 3.C, ...
    const keyParts = [];
    activeJob.items.forEach((it) => {
      let ans = "?";
      if (it.solution) {
        const match = it.solution.match(/Final Answer:?\s*\(?([A-D0-9.\-\/]+)\)?/i);
        if (match) ans = match[1].toUpperCase();
      }
      keyParts.push(`${it.index}.${ans}`);
    });
    const simpleKey = keyParts.join(", ");

    let md = `# SAT Practice Test Module - Answers & Explanations\n\n`;
    md += `## Simple Answer Key\n${simpleKey}\n\n---\n\n`;
    md += `## Detailed Explanations\n\n`;
    activeJob.items.forEach((it) => {
      md += `### Question ${it.index}\n\n`;
      md += `#### Problem Stem & Visuals\n${it.markdown_question || "(Pending)"}\n\n`;
      md += `#### Explanation & Analysis\n${it.solution || "(Pending)"}\n\n---\n\n`;
    });
    downloadFile(md, "answers.md");
  });
}

function downloadFile(content, filename) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function handleFiles(files) {
  const imageFiles = files.filter((f) =>
    ["image/png", "image/jpeg", "image/webp"].includes(f.type)
  );

  if (imageFiles.length === 0) {
    alert("Please upload valid image files (.png, .jpg, .webp)");
    return;
  }

  const existingNames = new Set(selectedFiles.map((f) => f.name));
  for (const f of imageFiles) {
    if (!existingNames.has(f.name)) {
      selectedFiles.push(f);
    }
  }

  selectedFiles.sort((a, b) =>
    a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" })
  );

  renderPreviewTray();
}

function renderPreviewTray() {
  const tray = document.getElementById("previewTray");
  const grid = document.getElementById("fileGrid");
  const countBadge = document.getElementById("fileCountBadge");
  const startBtn = document.getElementById("startPipelineBtn");
  const clearBtn = document.getElementById("clearFilesBtn");

  if (selectedFiles.length === 0) {
    tray.classList.add("hidden");
    clearBtn.classList.add("hidden");
    startBtn.disabled = true;
    return;
  }

  tray.classList.remove("hidden");
  clearBtn.classList.remove("hidden");
  startBtn.disabled = false;
  countBadge.textContent = `${selectedFiles.length} screenshots queued`;

  grid.innerHTML = "";
  selectedFiles.forEach((file, idx) => {
    const card = document.createElement("div");
    card.className =
      "relative group bg-slate-950 border border-slate-800 rounded-lg p-1.5 flex flex-col items-center";

    const objectUrl = URL.createObjectURL(file);
    card.innerHTML = `
      <div class="w-full h-16 bg-slate-900 rounded overflow-hidden flex items-center justify-center">
        <img src="${objectUrl}" class="w-full h-full object-cover" />
      </div>
      <div class="w-full mt-1 flex items-center justify-between">
        <span class="text-[10px] text-slate-300 truncate w-20" title="${file.name}">${idx + 1}. ${file.name}</span>
        <button class="text-slate-500 hover:text-rose-400 text-xs px-1" onclick="removeFile(${idx})">&times;</button>
      </div>
    `;
    grid.appendChild(card);
  });
}

window.removeFile = function (index) {
  selectedFiles.splice(index, 1);
  renderPreviewTray();
};

async function loadConfig() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();

    document.getElementById("settingProvider").value = data.ai_provider || "omniroute";
    if (data.omni_route_url) {
      document.getElementById("settingOmniRouteUrl").value = data.omni_route_url;
    }
    document.getElementById("settingVisionModel").value = data.vision_model || "antigravity/claude-sonnet-4-6";
    document.getElementById("settingSolverModel").value = data.solver_model || "antigravity/claude-opus-4-6-thinking-high";
    document.getElementById("settingConcurrency").value = data.max_concurrency || 4;

    const providerText = document.getElementById("providerText");
    let provName = "Omni Route (Active)";
    if (data.ai_provider === "anthropic") provName = "Anthropic Direct";
    else if (data.ai_provider === "openrouter") provName = "OpenRouter";
    providerText.textContent = `Provider: ${provName}`;
  } catch (err) {
    console.error("Failed to load config:", err);
  }
}

async function loadPrompts() {
  try {
    const res = await fetch("/api/prompts");
    const data = await res.json();
    document.getElementById("settingVisionPrompt").value = data.vision_system_prompt || "";
    document.getElementById("settingSolverPrompt").value = data.solver_system_prompt || "";
  } catch (err) {
    console.error("Failed to load prompts:", err);
  }
}

async function saveConfig() {
  const payload = {
    ai_provider: document.getElementById("settingProvider").value,
    omni_route_url: document.getElementById("settingOmniRouteUrl").value.trim(),
    vision_model: document.getElementById("settingVisionModel").value.trim(),
    solver_model: document.getElementById("settingSolverModel").value.trim(),
    max_concurrency: parseInt(document.getElementById("settingConcurrency").value, 10),
  };

  const omniKey = document.getElementById("settingOmniRouteKey").value.trim();
  if (omniKey) payload.omni_route_api_key = omniKey;

  const orKey = document.getElementById("settingOpenrouterKey").value.trim();
  if (orKey) payload.openrouter_api_key = orKey;

  const antKey = document.getElementById("settingAnthropicKey").value.trim();
  if (antKey) payload.anthropic_api_key = antKey;

  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      await loadConfig();
    }
  } catch (err) {
    alert("Error saving settings: " + err.message);
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      const base64 = result.split(",")[1];
      resolve(base64);
    };
    reader.onerror = (error) => reject(error);
    reader.readAsDataURL(file);
  });
}

// Client-Driven Automated Pipeline (Vercel-proof & Serverless-safe)
async function startClientPipeline() {
  if (selectedFiles.length === 0) return;

  const startBtn = document.getElementById("startPipelineBtn");
  startBtn.disabled = true;

  const visionPrompt = document.getElementById("settingVisionPrompt").value;
  const solverPrompt = document.getElementById("settingSolverPrompt").value;
  const concurrency = parseInt(document.getElementById("settingConcurrency").value, 10) || 3;

  const progressSec = document.getElementById("progressSection");
  const resultsSec = document.getElementById("resultsSection");
  progressSec.classList.remove("hidden");
  resultsSec.classList.remove("hidden");

  activeJob = {
    total_images: selectedFiles.length,
    vision_completed: 0,
    solver_completed: 0,
    current_message: "Starting processing...",
    items: selectedFiles.map((file, idx) => ({
      index: idx + 1,
      filename: file.name,
      file: file,
      image_url: URL.createObjectURL(file),
      status: "pending",
      markdown_question: "",
      solution: "",
      error: null,
    })),
  };

  updateProgressUI();
  renderResults();

  // Async task pool
  let queue = [...activeJob.items];

  async function worker() {
    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) break;

      try {
        // Stage 1: Vision Transcription
        item.status = "transcribing";
        activeJob.current_message = `Transcribing Question ${item.index} with Vision...`;
        updateProgressUI();
        renderResults();

        const b64 = await fileToBase64(item.file);
        const mimeType = item.file.type || "image/png";

        const tRes = await fetch("/api/transcribe-direct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_base64: b64,
            image_mime_type: mimeType,
            question_num: item.index,
            vision_prompt: visionPrompt,
          }),
        });

        if (!tRes.ok) {
          const errData = await tRes.json().catch(() => ({}));
          throw new Error(errData.detail || `Transcription failed (${tRes.status})`);
        }

        const tData = await tRes.json();
        item.markdown_question = tData.markdown_question;
        item.status = "transcribed";
        activeJob.vision_completed += 1;
        updateProgressUI();
        renderResults();

        // Stage 2: Frontier Cloud Solver
        item.status = "solving";
        activeJob.current_message = `Solving Question ${item.index} with Claude Opus Thinking High...`;
        updateProgressUI();
        renderResults();

        const sRes = await fetch("/api/solve-direct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            markdown_question: item.markdown_question,
            question_num: item.index,
            solver_prompt: solverPrompt,
          }),
        });

        if (!sRes.ok) {
          const sErrData = await sRes.json().catch(() => ({}));
          throw new Error(sErrData.detail || `Solving failed (${sRes.status})`);
        }

        const sData = await sRes.json();
        item.solution = sData.solution;
        item.status = "completed";
        activeJob.solver_completed += 1;
        updateProgressUI();
        renderResults();

      } catch (err) {
        console.error(`Error on item ${item.index}:`, err);
        item.status = "error";
        item.error = err.message;
        updateProgressUI();
        renderResults();
      }
    }
  }

  // Launch parallel workers
  const workerCount = Math.min(concurrency, selectedFiles.length);
  const workers = Array.from({ length: workerCount }, () => worker());
  await Promise.all(workers);

  document.getElementById("progressTitle").textContent = "Pipeline Completed!";
  document.getElementById("progressMessage").textContent =
    `Successfully processed all ${activeJob.total_images} questions.`;
  startBtn.disabled = false;
}

function updateProgressUI() {
  if (!activeJob) return;
  const total = activeJob.total_images || 1;
  const vDone = activeJob.vision_completed || 0;
  const sDone = activeJob.solver_completed || 0;

  const overallPercent = Math.round(((vDone + sDone) / (total * 2)) * 100);

  document.getElementById("progressPercent").textContent = `${overallPercent}%`;
  document.getElementById("progressMessage").textContent = activeJob.current_message;

  const vPercent = Math.round((vDone / total) * 100);
  document.getElementById("visionProgressBar").style.width = `${vPercent}%`;
  document.getElementById("visionProgressCount").textContent = `${vDone} / ${total}`;

  const sPercent = Math.round((sDone / total) * 100);
  document.getElementById("solverProgressBar").style.width = `${sPercent}%`;
  document.getElementById("solverProgressCount").textContent = `${sDone} / ${total}`;
}

function renderResults() {
  if (!activeJob) return;
  const container = document.getElementById("questionsContainer");
  const countBadge = document.getElementById("resultsCountBadge");
  countBadge.textContent = `${activeJob.items.length} Questions`;

  container.innerHTML = "";

  activeJob.items.forEach((item) => {
    const card = document.createElement("div");
    card.className =
      "bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4";

    const statusColors = {
      pending: "bg-slate-800 text-slate-400 border-slate-700",
      transcribing: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30 animate-pulse",
      transcribed: "bg-blue-500/20 text-blue-300 border-blue-500/30",
      solving: "bg-amber-500/20 text-amber-300 border-amber-500/30 animate-pulse",
      completed: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
      error: "bg-rose-500/20 text-rose-300 border-rose-500/30",
    };

    const statusBadge = `<span class="text-xs px-2.5 py-0.5 rounded-full border ${statusColors[item.status] || statusColors.pending}">${item.status.toUpperCase()}</span>`;

    const questionHtml = item.markdown_question
      ? marked.parse(item.markdown_question)
      : item.status === "transcribing"
      ? '<p class="text-indigo-400 italic">Transcribing screenshot with Vision model...</p>'
      : '<p class="text-slate-500 italic">Waiting for transcription...</p>';

    const solutionHtml = item.solution
      ? marked.parse(item.solution)
      : item.status === "solving"
      ? '<p class="text-amber-400 italic">Claude Opus Thinking High is deriving step-by-step solution...</p>'
      : '<p class="text-slate-500 italic">Solution will appear after transcription.</p>';

    card.innerHTML = `
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div class="flex items-center gap-3">
          <span class="font-bold text-base text-white">#${item.index}</span>
          <span class="text-xs text-slate-400 font-mono">${item.filename}</span>
        </div>
        <div>${statusBadge}</div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <!-- Col 1: Screenshot -->
        <div class="lg:col-span-4 bg-slate-950/80 rounded-xl border border-slate-800/80 p-3 flex flex-col">
          <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Original Screenshot</span>
          <div class="flex-1 rounded-lg overflow-hidden bg-slate-900 border border-slate-800 flex items-center justify-center min-h-[220px]">
            <img src="${item.image_url}" class="max-h-72 w-auto object-contain cursor-zoom-in" onclick="window.open('${item.image_url}', '_blank')" />
          </div>
        </div>

        <!-- Col 2: Markdown Question -->
        <div class="lg:col-span-4 bg-slate-950/80 rounded-xl border border-slate-800/80 p-4 flex flex-col">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Transcribed Question (MD)</span>
            <button class="text-[11px] text-slate-400 hover:text-slate-200" onclick="copyText(${item.index}, 'q')">Copy</button>
          </div>
          <div id="q-content-${item.index}" class="markdown-body flex-1 overflow-y-auto max-h-96 pr-2">
            ${questionHtml}
          </div>
        </div>

        <!-- Col 3: Frontier Solution -->
        <div class="lg:col-span-4 bg-slate-950/80 rounded-xl border border-slate-800/80 p-4 flex flex-col">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Frontier AI Solution</span>
            <button class="text-[11px] text-slate-400 hover:text-slate-200" onclick="copyText(${item.index}, 's')">Copy</button>
          </div>
          <div id="s-content-${item.index}" class="markdown-body flex-1 overflow-y-auto max-h-96 pr-2">
            ${solutionHtml}
          </div>
        </div>
      </div>
    `;

    container.appendChild(card);
  });

  if (window.renderMathInElement) {
    renderMathInElement(container, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
      ],
      throwOnError: false,
    });
  }
}

window.copyText = function (index, type) {
  const el = document.getElementById(`${type}-content-${index}`);
  if (el) {
    navigator.clipboard.writeText(el.innerText);
    alert("Copied to clipboard!");
  }
};
