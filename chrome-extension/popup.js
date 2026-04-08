document.addEventListener('DOMContentLoaded', () => {
    // Tab navigation
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`${tab}-tab`).classList.add('active');
        });
    });

    // Settings form elements
    const form = document.getElementById('config-form');
    const backendUrlInput = document.getElementById('backendUrl');
    const apiKeyInput = document.getElementById('apiKey');
    const saveBtn = document.getElementById('saveBtn');
    const testBtn = document.getElementById('testBtn');
    const toggleKeyBtn = document.getElementById('toggleKey');
    const statusDiv = document.getElementById('status');
    const urlError = document.getElementById('url-error');
    const keyError = document.getElementById('key-error');
    
    // Generate reply elements
    const generateBtn = document.getElementById('generateBtn');
    const replyContainer = document.getElementById('reply-container');
    const generatedReplyDiv = document.getElementById('generatedReply');

    let statusTimeout;
    let currentReply = null;

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
            console.log('[loadConfig] Storage contents:', { backendUrl: result.backendUrl, hasApiKey: !!result.apiKey });
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
                apiKey: apiKeyInput.value,
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

    /**
     * Generates a reply using the backend API.
     */
    async function generateReply() {
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';
        showStatus('Scraping conversation and generating reply...', 'info');
        console.log('Generate Reply button clicked');

        try {
            // Get configuration
            chrome.storage.sync.get(['backendUrl', 'apiKey'], async (result) => {
                console.log('Config loaded:', { backendUrl: result.backendUrl, hasApiKey: !!result.apiKey });
                
                if (!result.backendUrl || !result.apiKey) {
                    showStatus('Please configure settings first!', 'error');
                    generateBtn.disabled = false;
                    generateBtn.textContent = 'Generate AI Reply';
                    return;
                }

                // Send message to content script to scrape conversation
                chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                    console.log('Active tab:', tabs[0]?.url);
                    
                    if (!tabs[0]) {
                        showStatus('No active tab found', 'error');
                        generateBtn.disabled = false;
                        generateBtn.textContent = 'Generate AI Reply';
                        return;
                    }

                    chrome.tabs.sendMessage(tabs[0].id, { type: 'SCRAPE_CONVERSATION' }, async (response) => {
                        console.log('Scrape response:', response);
                        
                        if (chrome.runtime.lastError) {
                            const errorMsg = chrome.runtime.lastError.message || 'Unknown error';
                            console.error('Chrome error:', errorMsg);
                            console.error('Full error object:', chrome.runtime.lastError);
                            showStatus(`Failed to access LinkedIn. Error: ${errorMsg}. Make sure you're on linkedin.com/messaging`, 'error');
                            generateBtn.disabled = false;
                            generateBtn.textContent = 'Generate AI Reply';
                            return;
                        }

                        if (response === undefined) {
                            console.error('No response from content script - it may not be loaded yet');
                            showStatus('Content script not ready. Refresh the page and try again.', 'error');
                            generateBtn.disabled = false;
                            generateBtn.textContent = 'Generate AI Reply';
                            return;
                        }

                        if (!response || !response.messages) {
                            const errorInfo = response && response.error ? ` Error: ${response.error}` : '';
                            showStatus('Failed to scrape conversation. Make sure you\'re on a LinkedIn messaging page.' + errorInfo, 'error');
                            generateBtn.disabled = false;
                            generateBtn.textContent = 'Generate AI Reply';
                            return;
                        }

                        try {
                            // Call backend API
                            const backendUrl = result.backendUrl.endsWith('/') ? result.backendUrl.slice(0, -1) : result.backendUrl;
                            console.log('Calling backend:', `${backendUrl}/generate-reply`);
                            
                            const apiResponse = await fetch(`${backendUrl}/generate-reply`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-API-Key': result.apiKey
                                },
                                body: JSON.stringify({
                                    messages: response.messages,
                                    stage: 'initial_reply'
                                })
                            });

                            console.log('API response status:', apiResponse.status);

                            if (!apiResponse.ok) {
                                throw new Error(`API error: ${apiResponse.statusText}`);
                            }

                            const data = await apiResponse.json();
                            currentReply = data.reply;
                            generatedReplyDiv.textContent = currentReply;
                            replyContainer.style.display = 'block';
                            
                            // Auto-insert the reply into the LinkedIn draft box
                            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                                if (tabs[0]) {
                                    chrome.tabs.sendMessage(tabs[0].id, { 
                                        type: 'INSERT_REPLY',
                                        reply: currentReply
                                    }, (insertResponse) => {
                                        if (chrome.runtime.lastError) {
                                            console.warn('Could not auto-insert reply:', chrome.runtime.lastError);
                                            showStatus('Reply generated but could not insert. Manual draft mode available.', 'success');
                                        } else if (insertResponse && insertResponse.success) {
                                            showStatus('Reply generated and inserted!', 'success');
                                        } else {
                                            showStatus('Reply generated but could not auto-insert.', 'success');
                                        }
                                    });
                                } else {
                                    showStatus('Reply generated successfully!', 'success');
                                }
                            });
                        } catch (error) {
                            console.error('Error:', error);
                            showStatus(`Error: ${error.message}`, 'error');
                        } finally {
                            generateBtn.disabled = false;
                            generateBtn.textContent = 'Generate AI Reply';
                        }
                    });
                });
            });
        } catch (error) {
            console.error('Outer error:', error);
            showStatus(`Error: ${error.message}`, 'error');
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate AI Reply';
        }
    }

    // --- Event Listeners ---
    form.addEventListener('submit', saveConfig);
    testBtn.addEventListener('click', testConnection);
    toggleKeyBtn.addEventListener('click', toggleKeyVisibility);
    generateBtn.addEventListener('click', generateReply);

    // --- Initial Load ---
    loadConfig();
});
