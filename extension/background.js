// Opens the side panel when you click the extension icon.
// Requires Chrome 114+ for the sidePanel API.

chrome.runtime.onInstalled.addListener(() => {
  // Make sure the side panel is enabled for the extension
  // (default_path in manifest already sets it, this is just extra safety).
  if (chrome.sidePanel?.setOptions) {
    chrome.sidePanel.setOptions({ path: "popup.html", enabled: true }).catch(() => {});
  }
});

chrome.action.onClicked.addListener(async (tab) => {
  try {
    if (!tab?.id) return;
    await chrome.sidePanel.open({ tabId: tab.id });
  } catch (e) {
    console.error("Failed to open side panel:", e);
  }
});
