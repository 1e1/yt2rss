// background.js
// Works both on Firefox (MV2, `browser.*`) and Chrome/Edge (MV3, `chrome.*`).
const browser = globalThis.browser || globalThis.chrome;
const action = browser.action || browser.browserAction;

// Helper: normalize base URL (no trailing slash)
function normalizeBaseUrl(url) {
  if (!url) return "";
  url = url.trim();
  if (url.endsWith("/")) url = url.slice(0, -1);
  return url;
}

// ---- Known-servers storage (supports several yt2rss instances on the LAN) ----
// Schema: { servers: string[], activeServer: string }. Legacy single `baseUrl`
// is migrated on first read.
async function getConfig() {
  const data = await browser.storage.sync.get(["servers", "activeServer", "baseUrl"]);
  let servers = Array.isArray(data.servers) ? data.servers : [];
  let active = data.activeServer || "";

  if (!servers.length && data.baseUrl) {
    const legacy = normalizeBaseUrl(data.baseUrl);
    servers = [legacy];
    active = legacy;
    await browser.storage.sync.set({ servers, activeServer: active });
    await browser.storage.sync.remove("baseUrl");
  }
  if (!active && servers.length) active = servers[0];
  return { servers, active: normalizeBaseUrl(active) };
}

async function addServer(url) {
  const base = normalizeBaseUrl(url);
  if (!base) return;
  const { servers } = await getConfig();
  const next = servers.includes(base) ? servers : [...servers, base];
  await browser.storage.sync.set({ servers: next, activeServer: base });
}

// Turn a YouTube author URL into the matching yt2rss RSS path.
function authorUrlToRssPath(authorUrl) {
  try {
    const u = new URL(authorUrl);
    const path = u.pathname.replace(/^\/+|\/+$/g, ""); // trim leading/trailing slashes
    const matchAt = path.match(/^@([^\/]+)/);
    if (matchAt) return `_user/${matchAt[1]}.rss`;
    if (path.startsWith("c/") || path.startsWith("channel/") || path.startsWith("user/")) {
      return `${path.split("/").slice(0, 2).join("/")}.rss`;
    }
    return `c/${path.split("/")[0]}.rss`;
  } catch (err) {
    return `_user/${encodeURIComponent(authorUrl)}.rss`;
  }
}

function notify(message) {
  return browser.notifications.create({
    type: "basic",
    iconUrl: browser.runtime.getURL("icons/icon48.png"),
    title: "subcRiSS",
    message,
  });
}

// Inject the content script on demand (MV3: scripting, MV2: tabs.executeScript).
async function injectContentScript(tabId) {
  if (browser.scripting && browser.scripting.executeScript) {
    await browser.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  } else if (browser.tabs && browser.tabs.executeScript) {
    await browser.tabs.executeScript(tabId, { file: "content.js" });
  }
}

// Handshake: read the yt2rss homepage marker in the active tab (activeTab grant
// after the user click; no broad host permission needed). Returns the origin or null.
async function detectYt2rssOrigin(tabId) {
  const probe = 'document.querySelector(\'meta[name="yt2rss-server"]\') ? location.origin : null';
  try {
    if (browser.scripting && browser.scripting.executeScript) {
      const res = await browser.scripting.executeScript({
        target: { tabId },
        func: () => (document.querySelector('meta[name="yt2rss-server"]') ? location.origin : null),
      });
      return res && res[0] ? res[0].result : null;
    }
    if (browser.tabs && browser.tabs.executeScript) {
      const res = await browser.tabs.executeScript(tabId, { code: probe });
      return Array.isArray(res) ? res[0] : null;
    }
  } catch (err) {
    return null; // not accessible / not a yt2rss page
  }
  return null;
}

async function handleClick(tab) {
  if (!tab || !tab.id) return;

  // 1) On a yt2rss homepage -> register this server and stop.
  const origin = await detectYt2rssOrigin(tab.id);
  if (origin) {
    await addServer(origin);
    await notify(`Serveur yt2rss enregistré : ${origin}`);
    return;
  }

  // 2) Otherwise treat the tab as a YouTube page -> transform + copy.
  const { active } = await getConfig();
  if (!active) {
    await notify(
      "Aucun serveur yt2rss configuré. Ouvrez la page d'accueil yt2rss et cliquez l'extension pour l'enregistrer.",
    );
    await browser.runtime.openOptionsPage();
    return;
  }

  let authorUrl;
  try {
    authorUrl = await browser.tabs.sendMessage(tab.id, { action: "getAuthorUrl" });
  } catch (err) {
    // Content script not loaded yet: inject and retry once.
    console.error("subcRiSS: content script unreachable, injecting…", err);
    await injectContentScript(tab.id);
    authorUrl = await browser.tabs.sendMessage(tab.id, { action: "getAuthorUrl" });
  }

  if (!authorUrl) {
    await notify("Ouvrez une page YouTube (vidéo ou chaîne) pour générer le flux RSS.");
    return;
  }

  const rssUrl = `${active}/${authorUrlToRssPath(authorUrl)}`;
  await browser.tabs.sendMessage(tab.id, { action: "copyAndToast", rssUrl });
}

action.onClicked.addListener((tab) => {
  handleClick(tab).catch(async (err) => {
    console.error("subcRiSS onClicked error:", err);
    await notify("Erreur lors de la génération du lien RSS.");
  });
});
