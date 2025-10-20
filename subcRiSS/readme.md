# subcRiSS — YouTube → RSS (Firefox Extension)

This Firefox extension lets you quickly 
generate a YouTube-to-RSS feed URL powered 
by your own `yt2rss` server and 
copies it to your clipboard. 

---

## ✅ Features

- Works on **any YouTube page** (video or channel)
- Extracts the **channel URL automatically**
- Converts it into a **yt2rss RSS feed URL**
- Copies to clipboard instantly
- Supports `/_user/<handle>.rss` for `@handle` URLs
- On-premise and **private NAS-friendly use**

---

## 🔧 Requirements

- Firefox
- A running instance of `yt2rss` (like on your NAS or Docker server)

---

## 🚀 Installation (Development Mode)

1. Clone or download this folder.
2. Run the build script:
    ```bash
    ./build.sh
    ```
    This will create subcRiSS.zip.
3. Open Firefox and go to `about:debugging#/runtime/this-firefox`
4. Click "Load Temporary Add-on".
5. Select subcRiSS.zip or manifest.json.
    ✅ The extension icon should now appear in your toolbar.
