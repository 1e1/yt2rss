// options.js
document.addEventListener("DOMContentLoaded", async () => {
  const input = document.getElementById("baseUrl");
  const status = document.getElementById("status");
  const data = await browser.storage.sync.get("baseUrl");
  if (data.baseUrl) input.value = data.baseUrl;

  document.getElementById("saveBtn").addEventListener("click", async () => {
    const val = input.value.trim();
    await browser.storage.sync.set({ baseUrl: val });
    status.textContent = "Enregistré.";
    setTimeout(() => status.textContent = "", 2000);
  });
});
