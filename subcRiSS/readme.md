# subcRiSS — YouTube → RSS (browser extension)

This extension lets you quickly generate a YouTube-to-RSS feed URL powered by
your own `yt2rss` server and copies it to your clipboard.

---

## ✅ Features

- Works on **any YouTube page** (video or channel)
- Extracts the **channel URL automatically**
- Converts it into a **yt2rss RSS feed URL** and copies it to the clipboard
- **One-click server registration**: open your yt2rss homepage and click the
  extension icon — the server URL is detected and saved automatically
- **Multiple servers**: keep several yt2rss instances (e.g. different NAS) and
  pick the active one in the options
- On-premise and **private NAS-friendly use**
- Works on **Firefox** (Manifest V2) and **Chrome / Edge** (Manifest V3)
- Minimal permissions: only `activeTab` (the current page is read solely when
  you click the icon) plus access to YouTube pages

---

## 🔧 Requirements

- Firefox, Chrome or Edge
- A running instance of `yt2rss` (like on your NAS or Docker server)
- `jq` and `zip` to build the packages

---

## 📦 Download

Pre-built packages are produced by CI on every push (as workflow artifacts)
and attached to each GitHub Release. A running yt2rss server also serves them
directly at `/extra/extensions/subcRiSS/{firefox,chrome,edge}.zip`.

## 🚀 Build

```bash
./build.sh
```

This produces `dist/firefox.zip` (Manifest V2) and `dist/chrome.zip` /
`dist/edge.zip` (Manifest V3, same Chromium package) from the shared source
manifest.

## Install (development mode)

**Firefox**

1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on".
3. Select `dist/firefox.zip` (or `manifest.json`).

**Chrome / Edge**

1. Unzip `dist/chrome.zip` (or `dist/edge.zip`).
2. Open `chrome://extensions` (or `edge://extensions`), enable "Developer mode".
3. Click "Load unpacked" and select the unzipped folder.

## Usage

1. Open your yt2rss homepage (e.g. `http://192.168.1.50:2777/`) and click the
   extension icon once — the server is registered.
2. Browse to any YouTube video or channel and click the icon — the RSS feed URL
   is built from the active server and copied to your clipboard.
3. Manage servers and choose the active one from the extension options.
