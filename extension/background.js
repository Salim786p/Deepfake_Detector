const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";
const MENU_ID = "analyze-image-fake-content";

chrome.runtime.onInstalled.addListener(async () => {
  chrome.contextMenus.create({
    id: MENU_ID,
    title: "Analyze image for fake/manipulated content",
    contexts: ["image"]
  });

  const existing = await chrome.storage.local.get(["backendUrl"]);
  if (!existing.backendUrl) {
    await chrome.storage.local.set({ backendUrl: DEFAULT_BACKEND_URL });
  }
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID || !info.srcUrl) {
    return;
  }

  const sourcePageUrl = tab?.url || null;
  await setAnalysisState({
    status: "processing",
    imageUrl: info.srcUrl,
    pageUrl: sourcePageUrl,
    startedAt: new Date().toISOString(),
    error: null,
    result: null
  });

  try {
    const backendUrl = await getBackendUrl();
    const data = await analyzeImageWithFallback({
      backendUrl,
      imageUrl: info.srcUrl,
      pageUrl: sourcePageUrl
    });

    await setAnalysisState({
      status: "complete",
      imageUrl: info.srcUrl,
      pageUrl: sourcePageUrl,
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      error: null,
      result: data
    });

    await chrome.action.setBadgeText({ text: "OK" });
    await chrome.action.setBadgeBackgroundColor({ color: "#136f3a" });
    notify("Analysis complete", `${data.summary} Open the extension popup to view details.`);
  } catch (error) {
    const message = formatErrorMessage(error);
    await setAnalysisState({
      status: "error",
      imageUrl: info.srcUrl,
      pageUrl: sourcePageUrl,
      completedAt: new Date().toISOString(),
      error: message,
      result: null
    });

    await chrome.action.setBadgeText({ text: "ERR" });
    await chrome.action.setBadgeBackgroundColor({ color: "#b42318" });
    notify("Analysis failed", message);
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  void (async () => {
    if (message?.type === "get-state") {
      const data = await chrome.storage.local.get(["latestAnalysis", "backendUrl"]);
      sendResponse({
        backendUrl: data.backendUrl || DEFAULT_BACKEND_URL,
        latestAnalysis: data.latestAnalysis || null
      });
      return;
    }

    if (message?.type === "save-backend-url") {
      const backendUrl = normalizeBackendUrl(message.backendUrl || DEFAULT_BACKEND_URL);
      await chrome.storage.local.set({ backendUrl });
      sendResponse({ ok: true, backendUrl });
      return;
    }

    if (message?.type === "reanalyze-last-image") {
      const data = await chrome.storage.local.get(["latestAnalysis"]);
      const latest = data.latestAnalysis;
      if (!latest?.imageUrl) {
        sendResponse({ ok: false, error: "No image available to re-analyze." });
        return;
      }

      const backendUrl = await getBackendUrl();
      try {
        await setAnalysisState({
          ...latest,
          status: "processing",
          error: null
        });

        const payload = await analyzeImageWithFallback({
          backendUrl,
          imageUrl: latest.imageUrl,
          pageUrl: latest.pageUrl || null
        });

        await setAnalysisState({
          status: "complete",
          imageUrl: latest.imageUrl,
          pageUrl: latest.pageUrl || null,
          startedAt: new Date().toISOString(),
          completedAt: new Date().toISOString(),
          error: null,
          result: payload
        });

        sendResponse({ ok: true });
      } catch (error) {
        const message = formatErrorMessage(error);
        await setAnalysisState({
          ...latest,
          status: "error",
          completedAt: new Date().toISOString(),
          error: message,
          result: null
        });
        sendResponse({ ok: false, error: message });
      }
    }
  })();

  return true;
});

async function getBackendUrl() {
  const data = await chrome.storage.local.get(["backendUrl"]);
  return normalizeBackendUrl(data.backendUrl || DEFAULT_BACKEND_URL);
}

function normalizeBackendUrl(value) {
  return String(value || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, "");
}

async function setAnalysisState(state) {
  await chrome.storage.local.set({ latestAnalysis: state });
}

function notify(title, message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: chrome.runtime.getURL("icon128.png"),
    title,
    message
  });
}

async function analyzeImageWithFallback({ backendUrl, imageUrl, pageUrl }) {
  const urlResponse = await fetch(`${backendUrl}/api/analyze-url`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      image_url: imageUrl,
      page_url: pageUrl
    })
  });

  const urlPayload = await readJsonSafely(urlResponse);
  if (urlResponse.ok) {
    return urlPayload;
  }

  const detail = String(urlPayload?.detail || "");
  const shouldFallbackToUpload =
    urlResponse.status === 403 ||
    detail.includes("403") ||
    detail.includes("Forbidden");

  if (!shouldFallbackToUpload) {
    throw new Error(extractErrorDetail(urlPayload, "Backend request failed."));
  }

  const imageResponse = await fetch(imageUrl);
  if (!imageResponse.ok) {
    throw new Error(`Image fetch failed with status ${imageResponse.status}.`);
  }

  const blob = await imageResponse.blob();
  const formData = new FormData();
  formData.append("file", blob, guessFilenameFromUrl(imageUrl, blob.type));

  const uploadResponse = await fetch(`${backendUrl}/api/analyze-upload`, {
    method: "POST",
    body: formData
  });

  const uploadPayload = await readJsonSafely(uploadResponse);
  if (!uploadResponse.ok) {
    throw new Error(extractErrorDetail(uploadPayload, "Fallback upload analysis failed."));
  }

  if (!uploadPayload.source_image_url) {
    uploadPayload.source_image_url = imageUrl;
  }
  if (!uploadPayload.source_page_url && pageUrl) {
    uploadPayload.source_page_url = pageUrl;
  }

  return uploadPayload;
}

async function readJsonSafely(response) {
  try {
    return await response.json();
  } catch (_error) {
    return {};
  }
}

function extractErrorDetail(payload, fallbackMessage) {
  if (!payload) {
    return fallbackMessage;
  }
  if (typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  if (payload.detail && typeof payload.detail === "object") {
    return JSON.stringify(payload.detail);
  }
  if (typeof payload.error === "string" && payload.error.trim()) {
    return payload.error;
  }
  if (payload.error && typeof payload.error === "object") {
    return JSON.stringify(payload.error);
  }
  return fallbackMessage;
}

function formatErrorMessage(error) {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  if (typeof error === "string" && error.trim()) {
    return error;
  }
  if (error && typeof error === "object") {
    try {
      return JSON.stringify(error);
    } catch (_jsonError) {
      return "Unknown error";
    }
  }
  return "Unknown error";
}

function guessFilenameFromUrl(imageUrl, mimeType) {
  try {
    const pathname = new URL(imageUrl).pathname;
    const lastSegment = pathname.split("/").filter(Boolean).pop();
    if (lastSegment && lastSegment.includes(".")) {
      return lastSegment;
    }
  } catch (_error) {
  }

  if (mimeType === "image/png") {
    return "image.png";
  }
  if (mimeType === "image/webp") {
    return "image.webp";
  }
  if (mimeType === "image/gif") {
    return "image.gif";
  }
  return "image.jpg";
}
