// SAT Solver Frontend Application with Screenshot Grouping Agent
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
    let md = `# SAT Exam Questions\n\nTotal Questions: ${activeJob.items.length}\n\n---\n\n`;
    activeJob.items.forEach((it) => {
      md += `${it.markdown_question || `### Question ${it.question_number}\n(Transcription pending)`}\n\n---\n\n`;
    });
    downloadFile(md, "questions.md");
  });

  downloadSolutionsBtn.addEventListener("click", () => {
    if (!activeJob) return;

    // Simple Answer Key: 1.A, 2.B, 3.C, ...
    const keyParts = [];
    activeJob.items.forEach((it) => {
      let ans = "?";
      if (it.solution) {
        const match = it.solution.match(/Final Answer:?\s*\(?([A-D0-9.\-\/]+)\)?/i);
        if (match) ans = match[1].toUpperCase();
      }
      keyParts.push(`${it.question_number}.${ans}`);
    });
    const simpleKey = keyParts.join(", ");

    let md = `# SAT Practice Test Module - Answers & Explanations\n\n`;
    md += `## Simple Answer Key\n${simpleKey}\n\n---\n\n`;
    md += `## Detailed Explanations\n\n`;
    activeJob.items.forEach((it) => {
      md += `### Question ${it.question_number}\n\n`;
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
    if (document.getElementById("settingGroupingPrompt")) {
      document.getElementById("settingGroupingPrompt").value = data.grouping_system_prompt || "";
    }
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

// Downscale images client-side for Agent 0 grouping to keep payload well under Vercel's 4.5MB limit
function createDownscaledThumbnail(file, maxDim = 800, quality = 0.75) {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        let w = img.width;
        let h = img.height;
        if (w > maxDim || h > maxDim) {
          if (w > h) {
            h = Math.round((h * maxDim) / w);
            w = maxDim;
          } else {
            w = Math.round((w * maxDim) / h);
            h = maxDim;
          }
        }
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, w, h);
        const thumbUrl = canvas.toDataURL("image/jpeg", quality);
        URL.revokeObjectURL(url);
        resolve(thumbUrl.split(",")[1]);
      } catch (e) {
        console.warn("Canvas thumbnail failed, falling back to full b64:", e);
        URL.revokeObjectURL(url);
        fileToBase64(file).then(resolve);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      fileToBase64(file).then(resolve);
    };
    img.src = url;
  });
}

// 3-Stage Pipeline: Agent 0 (Grouping) -> Agent 1 (Multi-Image Vision) -> Agent 2 (Opus High Solver)
async function startClientPipeline() {
  if (selectedFiles.length === 0) return;

  const startBtn = document.getElementById("startPipelineBtn");
  startBtn.disabled = true;

  const groupingPrompt = document.getElementById("settingGroupingPrompt")?.value;
  const visionPrompt = document.getElementById("settingVisionPrompt").value;
  const solverPrompt = document.getElementById("settingSolverPrompt").value;
  const concurrency = parseInt(document.getElementById("settingConcurrency").value, 10) || 3;

  const progressSec = document.getElementById("progressSection");
  const resultsSec = document.getElementById("resultsSection");
  progressSec.classList.remove("hidden");
  resultsSec.classList.remove("hidden");

  // Encode all images (full resolution for vision/solving, lightweight thumbnail for grouping)
  document.getElementById("progressTitle").textContent = "Preparing Screenshots...";
  document.getElementById("progressMessage").textContent = `Encoding ${selectedFiles.length} screenshots for analysis...`;

  const encodedImages = [];
  for (let i = 0; i < selectedFiles.length; i++) {
    const file = selectedFiles[i];
    const b64 = await fileToBase64(file);
    const thumb_b64 = await createDownscaledThumbnail(file, 800, 0.75);
    encodedImages.push({
      index: i + 1,
      filename: file.name,
      b64: b64,
      thumb_b64: thumb_b64,
      mime_type: file.type || "image/png",
      url: URL.createObjectURL(file),
      file: file,
    });
  }

  const imageMap = {};
  encodedImages.forEach((img) => {
    imageMap[img.index] = img;
  });

  // ==========================================
  // STAGE 0: Agent 0 (Question Grouping & Sequencing)
  // ==========================================
  document.getElementById("progressTitle").textContent = "Agent 0: Analyzing & Grouping Screenshots...";
  document.getElementById("progressMessage").textContent =
    "Detecting question numbers and pairing multi-screenshot questions (passages, diagrams, options)...";
  document.getElementById("groupingProgressCount").textContent = "Analyzing...";
  document.getElementById("groupingProgressBar").style.width = "40%";

  let groupingResult = [];
  try {
    const groupRes = await fetch("/api/group-screenshots", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        images: encodedImages.map((im) => ({
          index: im.index,
          filename: im.filename,
          b64: im.thumb_b64,
          mime_type: "image/jpeg",
        })),
        grouping_prompt: groupingPrompt,
      }),
    });

    if (groupRes.ok) {
      const gData = await groupRes.json();
      groupingResult = gData.grouping || [];
      console.log("Agent 0 Grouping Success:", groupingResult);
    } else {
      const errText = await groupRes.text();
      console.error("Agent 0 Grouping API failed with status", groupRes.status, errText);
    }
  } catch (err) {
    console.error("Grouping agent error, falling back to 1-to-1:", err);
  }

  // Fallback if empty
  if (!groupingResult || groupingResult.length === 0) {
    groupingResult = encodedImages.map((im) => ({
      question_number: im.index,
      title: `Question ${im.index}`,
      image_indices: [im.index],
      reasoning: "Single screenshot unit (fallback)",
    }));
  }

  document.getElementById("groupingProgressCount").textContent = `${groupingResult.length} Questions Identified`;
  document.getElementById("groupingProgressBar").style.width = "100%";

  // Create Question Units
  activeJob = {
    total_questions: groupingResult.length,
    vision_completed: 0,
    solver_completed: 0,
    current_message: `Identified ${groupingResult.length} questions from ${selectedFiles.length} screenshots. Starting transcription...`,
    items: groupingResult.map((g, idx) => ({
      index: idx + 1,
      question_number: g.question_number || idx + 1,
      title: g.title || `Question ${g.question_number || idx + 1}`,
      reasoning: g.reasoning || "",
      images: (g.image_indices || [idx + 1])
        .map((imgIdx) => imageMap[imgIdx])
        .filter(Boolean),
      status: "pending",
      markdown_question: "",
      solution: "",
      error: null,
    })),
  };

  updateProgressUI();
  renderResults();

  // ==========================================
  // STAGE 1 & 2: Multi-Image Vision & Frontier Cloud Solver
  // ==========================================
  let queue = [...activeJob.items];

  async function worker() {
    while (queue.length > 0) {
      const item = queue.shift();
      if (!item) break;

      try {
        // Stage 1: Multi-Image Vision Transcription
        item.status = "transcribing";
        activeJob.current_message = `Transcribing Question ${item.question_number} (${item.images.length} screenshot${item.images.length > 1 ? "s" : ""})...`;
        updateProgressUI();
        renderResults();

        const imagesPayload = item.images.map((im) => ({
          b64: im.b64,
          mime_type: im.mime_type,
        }));

        const tRes = await fetch("/api/transcribe-direct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            images: imagesPayload,
            question_num: item.question_number,
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
        activeJob.current_message = `Solving Question ${item.question_number} with Claude Opus Thinking High...`;
        updateProgressUI();
        renderResults();

        const sRes = await fetch("/api/solve-direct", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            markdown_question: item.markdown_question,
            question_num: item.question_number,
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
        console.error(`Error on Question ${item.question_number}:`, err);
        item.status = "error";
        item.error = err.message;
        updateProgressUI();
        renderResults();
      }
    }
  }

  const workerCount = Math.min(concurrency, activeJob.items.length);
  const workers = Array.from({ length: workerCount }, () => worker());
  await Promise.all(workers);

  document.getElementById("progressTitle").textContent = "Pipeline Completed!";
  document.getElementById("progressMessage").textContent =
    `Successfully grouped, transcribed, and solved all ${activeJob.total_questions} questions!`;
  startBtn.disabled = false;
}

function updateProgressUI() {
  if (!activeJob) return;
  const total = activeJob.total_questions || 1;
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
  countBadge.textContent = `${activeJob.items.length} Questions (${selectedFiles.length} Screenshots)`;

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

    // Render screenshots gallery for this question
    let screenshotsHtml = "";
    item.images.forEach((img, i) => {
      screenshotsHtml += `
        <div class="relative group bg-slate-900 border border-slate-800 rounded-lg overflow-hidden flex flex-col items-center">
          <img src="${img.url}" class="h-28 w-full object-contain cursor-zoom-in p-1" onclick="window.open('${img.url}', '_blank')" />
          <div class="w-full bg-slate-950/80 px-2 py-0.5 text-[10px] text-slate-400 truncate text-center border-t border-slate-800">
            Part ${i + 1}: ${img.filename}
          </div>
        </div>
      `;
    });

    const questionHtml = item.markdown_question
      ? marked.parse(item.markdown_question)
      : item.status === "transcribing"
      ? '<p class="text-indigo-400 italic">Agent 1: Synthesizing and transcribing screenshots...</p>'
      : '<p class="text-slate-500 italic">Waiting for transcription...</p>';

    const solutionHtml = item.solution
      ? marked.parse(item.solution)
      : item.status === "solving"
      ? '<p class="text-amber-400 italic">Agent 2: Claude Opus Thinking High is solving...</p>'
      : '<p class="text-slate-500 italic">Solution will appear after transcription.</p>';

    card.innerHTML = `
      <div class="flex items-center justify-between border-b border-slate-800/80 pb-3">
        <div class="flex items-center gap-3">
          <span class="font-bold text-base text-white">Question ${item.question_number}</span>
          <span class="text-xs bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/30">
            ${item.images.length} screenshot${item.images.length > 1 ? "s" : ""} paired
          </span>
          ${item.reasoning ? `<span class="text-xs text-slate-400 italic hidden md:inline">(${item.reasoning})</span>` : ""}
        </div>
        <div>${statusBadge}</div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <!-- Col 1: Grouped Screenshots Gallery -->
        <div class="lg:col-span-4 bg-slate-950/80 rounded-xl border border-slate-800/80 p-3 flex flex-col">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Paired Screenshots (${item.images.length})</span>
            <span class="text-[10px] text-slate-500">Click to zoom</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 overflow-y-auto max-h-96 pr-1">
            ${screenshotsHtml}
          </div>
        </div>

        <!-- Col 2: Markdown Question -->
        <div class="lg:col-span-4 bg-slate-950/80 rounded-xl border border-slate-800/80 p-4 flex flex-col">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Transcribed Question (MD)</span>
            <button class="text-[11px] text-slate-400 hover:text-slate-200" onclick="copyText(${item.question_number}, 'q')">Copy</button>
          </div>
          <div id="q-content-${item.question_number}" class="markdown-body flex-1 overflow-y-auto max-h-96 pr-2">
            ${questionHtml}
          </div>
        </div>

        <!-- Col 3: Frontier Solution -->
        <div class="lg:col-span-4 bg-slate-950/80 rounded-xl border border-slate-800/80 p-4 flex flex-col">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Frontier AI Solution</span>
            <button class="text-[11px] text-slate-400 hover:text-slate-200" onclick="copyText(${item.question_number}, 's')">Copy</button>
          </div>
          <div id="s-content-${item.question_number}" class="markdown-body flex-1 overflow-y-auto max-h-96 pr-2">
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
