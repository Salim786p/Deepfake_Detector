const backendUrlInput = document.getElementById("backendUrl");
const saveBackendButton = document.getElementById("saveBackendButton");
const saveStatus = document.getElementById("saveStatus");
const statusBadge = document.getElementById("statusBadge");
const emptyState = document.getElementById("emptyState");
const resultContent = document.getElementById("resultContent");
const imagePreview = document.getElementById("imagePreview");
const verdictText = document.getElementById("verdictText");
const confidenceText = document.getElementById("confidenceText");
const genaiText = document.getElementById("genaiText");
const deepfakeText = document.getElementById("deepfakeText");
const summaryText = document.getElementById("summaryText");
const explanationText = document.getElementById("explanationText");
const signalsList = document.getElementById("signalsList");
const authenticityList = document.getElementById("authenticityList");
const actionText = document.getElementById("actionText");
const reanalyzeButton = document.getElementById("reanalyzeButton");

document.addEventListener("DOMContentLoaded", initialize);
saveBackendButton.addEventListener("click", saveBackendUrl);
reanalyzeButton.addEventListener("click", reanalyzeLastImage);
chrome.storage.onChanged.addListener(handleStorageChange);

async function initialize() {
  const state = await sendRuntimeMessage({ type: "get-state" });
  backendUrlInput.value = state.backendUrl || "http://127.0.0.1:8000";
  renderLatestAnalysis(state.latestAnalysis);
}

async function saveBackendUrl() {
  const backendUrl = backendUrlInput.value.trim();
  const response = await sendRuntimeMessage({
    type: "save-backend-url",
    backendUrl
  });

  saveStatus.textContent = response?.ok
    ? `Saved backend URL: ${response.backendUrl}`
    : "Unable to save backend URL.";
}

async function reanalyzeLastImage() {
  reanalyzeButton.disabled = true;
  reanalyzeButton.textContent = "Re-analyzing...";

  const response = await sendRuntimeMessage({ type: "reanalyze-last-image" });
  if (!response?.ok) {
    saveStatus.textContent = response?.error || "Re-analysis failed.";
  }

  reanalyzeButton.disabled = false;
  reanalyzeButton.textContent = "Re-analyze last image";
}

function handleStorageChange(changes, areaName) {
  if (areaName !== "local" || !changes.latestAnalysis) {
    return;
  }

  renderLatestAnalysis(changes.latestAnalysis.newValue);
}

function renderLatestAnalysis(latestAnalysis) {
  const status = latestAnalysis?.status || "idle";
  setStatusBadge(status);

  if (!latestAnalysis) {
    emptyState.classList.remove("hidden");
    emptyState.textContent = "No image analyzed yet. Right-click any image and choose the analysis option.";
    resultContent.classList.add("hidden");
    return;
  }

  if (status === "processing") {
    emptyState.classList.remove("hidden");
    emptyState.textContent = "Analysis is running. This may take a few seconds.";
    resultContent.classList.add("hidden");
    return;
  }

  if (status === "error") {
    emptyState.classList.remove("hidden");
    emptyState.textContent = `Analysis failed: ${latestAnalysis.error || "Unknown error."}`;
    resultContent.classList.add("hidden");
    return;
  }

  const result = latestAnalysis.result;
  if (!result) {
    emptyState.classList.remove("hidden");
    resultContent.classList.add("hidden");
    return;
  }

  emptyState.classList.add("hidden");
  resultContent.classList.remove("hidden");

  imagePreview.src = result.source_image_url || latestAnalysis.imageUrl || "";
  imagePreview.classList.toggle("hidden", !imagePreview.src);

  verdictText.textContent = humanizeVerdict(result.verdict);
  confidenceText.textContent = `${result.confidence}%`;
  genaiText.textContent = `${Math.round((result.sightengine?.ai_generated_score || 0) * 100)}%`;
  deepfakeText.textContent = `${Math.round((result.sightengine?.deepfake_score || 0) * 100)}%`;
  summaryText.textContent = result.summary || "-";
  explanationText.textContent = result.explanation || "-";
  actionText.textContent = result.recommended_action || "-";

  renderList(
    signalsList,
    result.vision?.manipulation_signals || ["No strong visual manipulation signals were listed."]
  );
  renderList(
    authenticityList,
    result.vision?.authenticity_cues || ["No notable authenticity cues were listed."]
  );
}

function setStatusBadge(status) {
  statusBadge.textContent = status;
  statusBadge.className = `status-badge ${status}`;
}

function renderList(element, items) {
  element.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function humanizeVerdict(verdict) {
  switch (verdict) {
    case "LIKELY_DEEPFAKE":
      return "Likely Deepfake";
    case "LIKELY_AI_GENERATED":
      return "Likely AI-Generated";
    case "SUSPICIOUS":
      return "Suspicious";
    case "LIKELY_AUTHENTIC":
      return "Likely Authentic";
    default:
      return "Unknown";
  }
}

function sendRuntimeMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      resolve(response);
    });
  });
}
