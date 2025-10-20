// background.js

// Helper: normalize base URL (no trailing slash)
function normalizeBaseUrl(url) {
  if (!url) return "";
  url = url.trim();
  if (url.endsWith("/")) url = url.slice(0, -1);
  return url;
}

async function getStoredBaseUrl() {
  const data = await browser.storage.sync.get("baseUrl");
  return normalizeBaseUrl(data.baseUrl || "");
}

browser.action.onClicked.addListener(async (tab) => {
  // Ensure we have a tab
  if (!tab || !tab.id) return;

  // Get base URL from options
  const baseUrl = await getStoredBaseUrl();
  if (!baseUrl) {
    // open options to configure
    await browser.notifications.create({
      "type": "basic",
      "iconUrl": browser.runtime.getURL("icons/icon48.png"),
      "title": "subcRiSS",
      "message": "Configurez l'URL de base de votre serveur yt2rss dans les options."
    });
    await browser.runtime.openOptionsPage();
    return;
  }

  // Ask content-script for the author's URL
  try {
    const authorUrl = await browser.tabs.sendMessage(tab.id, { action: "getAuthorUrl" });
    if (!authorUrl) {
      await browser.notifications.create({
        "type": "basic",
        "iconUrl": browser.runtime.getURL("icons/icon48.png"),
        "title": "subcRiSS",
        "message": "Impossible de déterminer l'auteur sur cette page YouTube."
      });
      return;
    }

    // Build RSS URL
    // Cases:
    // - https://www.youtube.com/@handle  -> /_user/handle.rss
    // - https://www.youtube.com/c/Name  -> /c/Name.rss
    // - https://www.youtube.com/channel/ID -> /channel/ID.rss
    // - https://www.youtube.com/user/Name -> /user/Name.rss
    // - else fallback to /c/<path>.rss
    let rssPath = null;
    try {
      const u = new URL(authorUrl);
      const path = u.pathname.replace(/^\/+|\/+$/g, ""); // trim leading/trailing slashes
      // handle /@handle or /@handle/whatever
      const matchAt = path.match(/^@([^\/]+)/);
      if (matchAt) {
        const handle = matchAt[1];
        rssPath = `_user/${handle}.rss`;
      } else if (path.startsWith("c/") || path.startsWith("channel/") || path.startsWith("user/")) {
        rssPath = `${path}.rss`;
      } else {
        // Fallback: if path looks like a plain name, try c/<name>
        rssPath = `c/${path}.rss`;
      }
    } catch (err) {
      // fallback safe behavior
      rssPath = `_user/${encodeURIComponent(authorUrl)}.rss`;
    }

    let rssUrl = `${baseUrl}/${rssPath}`;

    // Ask content script to copy and show the toast (content script will handle clipboard to ensure page toast)
    await browser.tabs.sendMessage(tab.id, { action: "copyAndToast", rssUrl: rssUrl });

    // Optionally, send a small notification as backup
    // await browser.notifications.create({ type: "basic", iconUrl: browser.runtime.getURL("icons/icon48.png"), title: "subcRiSS", message: "Lien RSS copié" });

  } catch (err) {
    // If the tab has no content script (rare), try to inject it then resend
    console.error("background onClicked error:", err);
    try {
      await browser.scripting.executeScript({
        target: { tabId: tab.id },
        files: ["content.js"]
      });
      // try again once
      const authorUrl = await browser.tabs.sendMessage(tab.id, { action: "getAuthorUrl" });
      if (!authorUrl) {
        await browser.notifications.create({
          "type": "basic",
          "iconUrl": browser.runtime.getURL("icons/icon48.png"),
          "title": "subcRiSS",
          "message": "Impossible de déterminer l'auteur sur cette page YouTube."
        });
        return;
      }
      // build and copy as above
      const base = await getStoredBaseUrl();
      const u = new URL(authorUrl);
      const path = u.pathname.replace(/^\/+|\/+$/g, "");
      let rssPath = null;
      const matchAt = path.match(/^@([^\/]+)/);
      if (matchAt) rssPath = `_user/${matchAt[1]}.rss`;
      else if (path.startsWith("c/") || path.startsWith("channel/") || path.startsWith("user/")) rssPath = `${path}.rss`;
      else rssPath = `c/${path}.rss`;
      const rssUrl = `${base}/${rssPath}`;
      await browser.tabs.sendMessage(tab.id, { action: "copyAndToast", rssUrl: rssUrl });
    } catch (e2) {
      console.error("Retry failed:", e2);
      await browser.notifications.create({
        "type": "basic",
        "iconUrl": browser.runtime.getURL("icons/icon48.png"),
        "title": "subcRiSS",
        "message": "Erreur lors de la génération du lien RSS."
      });
    }
  }
});
