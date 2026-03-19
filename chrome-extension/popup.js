document.addEventListener('DOMContentLoaded', () => {

    const form = document.getElementById('config-form');

    const backendUrlInput = document.getElementById('backendUrl');

    const apiKeyInput = document.getElementById('apiKey');

    const saveBtn = document.getElementById('saveBtn');

    const testBtn = document.getElementById('testBtn');

    const toggleKeyBtn = document.getElementById('toggleKey');

    const statusDiv = document.getElementById('status');

    const urlError = document.getElementById('url-error');

    const keyError = document.getElementById('key-error');

 

    let statusTimeout;

 

    /**

     * Displays a status message that auto-clears.

     * @param {string} message The message to display.

     * @param {'success' | 'error' | 'info'} type The type of message.

     */

    function showStatus(message, type = 'info') {

        clearTimeout(statusTimeout);

        statusDiv.textContent = message;

        statusDiv.className = `status status--${type}`;

        statusDiv.style.display = 'block';

 

        statusTimeout = setTimeout(() => {

            statusDiv.style.display = 'none';

            statusDiv.textContent = '';

            statusDiv.className = 'status';

        }, 3000);

    }

 

    /**

     * Loads configuration from storage and populates the form.

     */

    function loadConfig() {

        chrome.storage.sync.get(['backendUrl', 'apiKey'], (result) => {

            if (result.backendUrl) {

                backendUrlInput.value = result.backendUrl;

            }

            if (result.apiKey) {

                apiKeyInput.value = result.apiKey;

            }

        });

    }

 

    /**

     * Validates inputs and saves the configuration to storage.

     */

    function saveConfig(e) {

        e.preventDefault();

        let isValid = true;

        urlError.textContent = '';

        keyError.textContent = '';

 

        // Validate URL

        let url;

        try {

            url = new URL(backendUrlInput.value);

            if (!['http:', 'https:',].includes(url.protocol)) {

                throw new Error("URL must start with http:// or https://");

            }

        } catch (error) {

            urlError.textContent = 'Please enter a valid URL.';

            isValid = false;

        }

 

        // Validate API Key

        if (apiKeyInput.value.trim() === '') {

            keyError.textContent = 'API Key cannot be empty.';

            isValid = false;

        }

 

        if (isValid) {

            chrome.storage.sync.set({

                backendUrl: backendUrlInput.value,

                apiKey: apiKeyInput.value

            }, () => {

                showStatus('Settings saved successfully!', 'success');

            });

        }

    }

 

    /**

     * Sends a message to the background script to test the backend connection.

     */

    function testConnection() {

        showStatus('Testing connection...', 'info');

        chrome.runtime.sendMessage({ type: "CHECK_HEALTH" }, (response) => {

            if (response.ok) {

                showStatus('Connection successful!', 'success');

            } else {

                showStatus(`Connection failed: ${response.error}`, 'error');

            }

        });

    }

 

    /**

     * Toggles the visibility of the API key input field.

     */

    function toggleKeyVisibility() {

        if (apiKeyInput.type === 'password') {

            apiKeyInput.type = 'text';

            toggleKeyBtn.textContent = 'Hide';

        } else {

            apiKeyInput.type = 'password';

            toggleKeyBtn.textContent = 'Show';

        }

    }

 

    // --- Event Listeners ---

    form.addEventListener('submit', saveConfig);

    testBtn.addEventListener('click', testConnection);

    toggleKeyBtn.addEventListener('click', toggleKeyVisibility);

 

    // --- Initial Load ---

    loadConfig();

});