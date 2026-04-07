// --- Defaults & Constants ---

const DEFAULT_BACKEND_URL = "http://localhost:8000";

const ERROR_BADGE_COLOR = "#A32D2D";

 

// --- Badge Management ---

 

/**

* background.js

*

* This service worker handles communication between the content script and the backend API.

*/

async function updateBadge() {

  const { apiKey } = await chrome.storage.sync.get("apiKey");

  if (!apiKey) {

    chrome.action.setBadgeText({ text: "!" });

    chrome.action.setBadgeBackgroundColor({ color: ERROR_BADGE_COLOR });

  } else {

    chrome.action.setBadgeText({ text: "" });

  }

}

 

// --- Event Listeners ---

 

/**

* On extension installation, set default config and open the popup.

*/

chrome.runtime.onInstalled.addListener((details) => {

  if (details.reason === "install") {

    chrome.storage.sync.set({

      backendUrl: DEFAULT_BACKEND_URL,

      apiKey: "",

    });

    // Open the options page for the user to configure the API key

    chrome.runtime.openOptionsPage();

  }

  updateBadge();

});

 

/**

* Listen for changes in storage and update the badge accordingly.

*/

chrome.storage.onChanged.addListener((changes, namespace) => {

  if (namespace === 'sync' && 'apiKey' in changes) {

    updateBadge();

  }

});

 

/**

* Main message handler for requests from other parts of the extension.

*/

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {

  // Return true to indicate you wish to send a response asynchronously

  let isAsync = false;

 

  switch (request.type) {

    case "GET_CONFIG":

      isAsync = true;

      chrome.storage.sync.get(["backendUrl", "apiKey", "clientId"]).then(config => {

        sendResponse(config);

      });

      break;

 

    case "CHECK_HEALTH":

      isAsync = true;

      checkBackendHealth().then(sendResponse);

      break;

     

    case "LOG":

      const level = request.level || 'log';

      const message = request.message || 'No message provided.';

      console[level](`[LRA]`, message);

      break;

  }

 

  return isAsync;

});

 

// --- Helper Functions ---

 

/**

* Checks the health of the backend API with a timeout.

* @returns {Promise<{ok: boolean, error?: string}>}

*/

async function checkBackendHealth() {

  try {

    const { backendUrl } = await chrome.storage.sync.get("backendUrl");

    if (!backendUrl) {

      return { ok: false, error: "Backend URL is not configured." };

    }

 

    const controller = new AbortController();

    const timeoutId = setTimeout(() => controller.abort(), 5000);

 

    const response = await fetch(`${backendUrl}/health`, {

      signal: controller.signal,

    });

 

    clearTimeout(timeoutId);

 

    if (response.ok) {

      return { ok: true };

    } else {

      return { ok: false, error: `Server returned status: ${response.status}` };

    }

  } catch (error) {

    if (error.name === 'AbortError') {

      return { ok: false, error: "Request timed out (5s)." };

    }

    return { ok: false, error: error.message };

  }

}

 

// --- Initial Run ---

// Update badge on startup

updateBadge();