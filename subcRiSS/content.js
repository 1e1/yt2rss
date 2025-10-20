// Utility: find channel/author link on YouTube video page or channel page
function findAuthorUrl() {
  // Attempt: new YouTube layout selectors
  // 1) Channel link in video page
  const selectors = [
    "#owner-container ytd-channel-name a",         // owner container link
    "ytd-channel-name a",                          // channel name link
    "a.yt-simple-endpoint.yt-formatted-string",   // various links
    "ytd-video-owner-renderer a"                   // fallback
  ];

  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el && el.href) return el.href;
  }

  // channel page with @handle in location
  if (location.pathname && location.pathname.startsWith("/@")) {
    return location.href;
  }

  // other: maybe a channel link in the meta area
  const metaChannel = document.querySelector("a.yt-simple-endpoint[href*='/channel/'], a.yt-simple-endpoint[href*='/user/'], a.yt-simple-endpoint[href*='/@']");
  if (metaChannel && metaChannel.href) return metaChannel.href;

  return null;
}

// Copy text to clipboard with fallback
async function copyToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
    // fallthrough to execCommand
  }
  // fallback
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return !!ok;
  } catch (e) {
    return false;
  }
}

// Show toast (YouTube-like) at top-right
function showToast(message) {
  // avoid duplicates
  const existing = document.getElementById("subcriss-toast");
  if (existing) {
    existing.remove();
  }

  const toast = document.createElement("div");
  toast.id = "subcriss-toast";
  toast.innerHTML = `<div class="subcriss-inner">${message}</div>`;

  const style = document.createElement("style");
  style.id = "subcriss-toast-style";
  style.textContent = `
  #subcriss-toast {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 9999999;
    font-family: Roboto, Arial, sans-serif;
  }
  #subcriss-toast .subcriss-inner {
    background: rgba(30,30,30,0.95);
    color: #fff;
    padding: 10px 14px;
    border-radius: 4px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.35);
    font-size: 13px;
    display: inline-block;
    max-width: 420px;
    word-break: break-all;
  }
  #subcriss-toast .subcriss-inner em {
    color: #8ab4f8;
    font-style: normal;
  }
  `;
  document.head.appendChild(style);
  document.body.appendChild(toast);

  // auto remove after 3.2s
  setTimeout(() => {
    const el = document.getElementById("subcriss-toast");
    if (el) el.remove();
    const st = document.getElementById("subcriss-toast-style");
    if (st) st.remove();
  }, 3200);
}

// Listener for background messages
browser.runtime.onMessage.addListener(async (message, sender) => {
  if (!message || !message.action) return;

  if (message.action === "getAuthorUrl") {
    const author = findAuthorUrl();
    return author || null;
  }

  if (message.action === "copyAndToast") {
    const rssUrl = message.rssUrl;
    const ok = await copyToClipboard(rssUrl);
    if (ok) {
      showToast(`Lien RSS copié : <em>${rssUrl}</em>`);
    } else {
      // fallback to opening a prompt to let user copy manually
      showToast("Impossible de copier automatiquement. Le lien s'affichera dans une fenêtre.");
      window.prompt("Copiez le lien RSS:", rssUrl);
    }
    return;
  }
});
