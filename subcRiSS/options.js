// options.js
const browser = globalThis.browser || globalThis.chrome;

function normalizeBaseUrl(url) {
  if (!url) return "";
  url = url.trim();
  if (url.endsWith("/")) url = url.slice(0, -1);
  return url;
}

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

async function saveConfig(servers, active) {
  await browser.storage.sync.set({ servers, activeServer: active });
}

function flash(message) {
  const status = document.getElementById("status");
  status.textContent = message;
  setTimeout(() => {
    status.textContent = "";
  }, 2000);
}

async function render() {
  const { servers, active } = await getConfig();
  const list = document.getElementById("servers");
  list.textContent = "";

  if (!servers.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "Aucun serveur enregistré pour l'instant.";
    list.appendChild(li);
    return;
  }

  for (const url of servers) {
    const li = document.createElement("li");

    const radio = document.createElement("input");
    radio.type = "radio";
    radio.name = "active";
    radio.checked = url === active;
    radio.addEventListener("change", async () => {
      await saveConfig(servers, url);
      flash("Serveur actif mis à jour.");
    });

    const code = document.createElement("code");
    code.textContent = url;

    const del = document.createElement("button");
    del.textContent = "Supprimer";
    del.addEventListener("click", async () => {
      const next = servers.filter((s) => s !== url);
      const nextActive = active === url ? next[0] || "" : active;
      await saveConfig(next, nextActive);
      await render();
      flash("Serveur supprimé.");
    });

    li.append(radio, code, del);
    list.appendChild(li);
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  await render();

  document.getElementById("addBtn").addEventListener("click", async () => {
    const input = document.getElementById("newServer");
    const url = normalizeBaseUrl(input.value);
    if (!url) return;
    const { servers } = await getConfig();
    const next = servers.includes(url) ? servers : [...servers, url];
    await saveConfig(next, url); // newly added becomes active
    input.value = "";
    await render();
    flash("Serveur ajouté.");
  });
});
