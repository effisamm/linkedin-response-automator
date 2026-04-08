/**
 * Fallback selectors for LinkedIn compose box.
 * LinkedIn uses different selectors depending on the page context.
 * If the primary selector fails, try each fallback in order.
 */
const COMPOSE_BOX_SELECTORS = [
    '.msg-form__content-editable',           // Primary: LinkedIn messaging
    '[data-placeholder="Write a message..."]', // Fallback 1: Alternative messaging
    '[contenteditable="true"][role="textbox"]', // Fallback 2: Any contenteditable textbox
    '.ql-editor'                            // Fallback 3: Quill editor (used in some contexts)
];

/**
 * Gets the LinkedIn compose box element using fallback selectors.
 * Tries each selector in order and returns the first match.
 * @returns {Element|null} The compose box element or null if not found.
 */
function getComposeBox() {
    for (const selector of COMPOSE_BOX_SELECTORS) {
        const element = document.querySelector(selector);
        if (element) {
            console.log('[LinkedIn Reply Automator] Found compose box with selector:', selector);
            return element;
        }
    }
    console.warn('[LinkedIn Reply Automator] Compose box not found with any selector');
    return null;
}

/**

* Scrapes the current LinkedIn message thread for all messages.

* @returns {Array<{sender: string, text: string}>} An array of message objects.

*/

function scrapeThread() {

    const messages = [];

    const messageElements = document.querySelectorAll('.msg-s-message-list__event');

 

    messageElements.forEach(el => {

        const senderEl = el.querySelector('.msg-s-message-group__name');

        // LinkedIn uses a visually hidden element for the sender of self-sent messages

        const selfSenderEl = el.querySelector('.msg-s-message-group__profile-link > .visually-hidden');

       

        const textEl = el.querySelector('.msg-s-event-listitem__body');

 

        if (textEl) {

            let sender = "Unknown";

            if (senderEl) {

                sender = senderEl.textContent.trim();

            } else if (selfSenderEl && selfSenderEl.textContent.includes('You')) {

                sender = "You";

            }

           

            messages.push({

                sender: sender,

                text: textEl.textContent.trim()

            });

        }

    });

    return messages;

}

 

/**

* Injects the "Draft Reply" button into the message form.

* It removes any existing button to prevent duplicates.

*/

function injectGenerateButton() {

    const form = document.querySelector('.msg-form__content-editable');

    if (!form) return;

 

    const container = form.parentElement;

    if (!container) return;

 

    // Remove existing button to avoid duplicates on re-injection

    const existingButton = document.getElementById('draft-reply-btn');

    if (existingButton) {

        existingButton.remove();

    }

    const existingError = document.getElementById('draft-reply-error');

    if(existingError) {

        existingError.remove();

    }

 

    const button = document.createElement('button');

    button.id = 'draft-reply-btn';

    button.textContent = '✦ Draft Reply';

    // Simple inline styles for now

    button.style.cssText = `

        position: absolute;

        bottom: 10px;

        right: 10px;

        z-index: 100;

        background-color: #0a66c2;

        color: white;

        border: none;

        border-radius: 18px;

        padding: 8px 16px;

        font-size: 14px;

        font-weight: bold;

        cursor: pointer;

        box-shadow: 0 2px 4px rgba(0,0,0,0.1);

    `;

 

    button.addEventListener('click', async (e) => {

        e.preventDefault();

        const messages = scrapeThread();

        if (messages.length > 0) {

            await generateReply(messages);

        } else {

            console.log("No messages found to generate a reply.");

        }

    });

 

    container.style.position = 'relative'; // Needed for absolute positioning of the button

    container.appendChild(button);

}

 

/**
 * Injects text into the LinkedIn message box using execCommand so React's
 * synthetic events fire and the Send button becomes active.
 * @param {string} text
 * @returns {boolean} true if the box was found, false otherwise.
 */
function injectTextIntoBox(text) {
    const contentEditable = getComposeBox();
    if (!contentEditable) {
        console.warn('[LinkedIn Reply Automator] Could not find compose box to inject text');
        return false;
    }
    
    try {
        // Focus the compose box
        contentEditable.focus();
        
        // Select all existing content
        document.execCommand('selectAll', false, null);
        
        // Delete existing content
        document.execCommand('delete', false, null);
        
        // Insert the new text
        document.execCommand('insertText', false, text);
        
        // Dispatch InputEvent for React to pick up the change
        const inputEvent = new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        contentEditable.dispatchEvent(inputEvent);
        
        // Dispatch change event as well
        const changeEvent = new Event('change', {
            bubbles: true,
            cancelable: true
        });
        contentEditable.dispatchEvent(changeEvent);
        
        console.log('[LinkedIn Reply Automator] Text injected successfully');
        return true;
    } catch (error) {
        console.error('[LinkedIn Reply Automator] Error injecting text:', error);
        return false;
    }
}

/**

* Fetches config, calls the backend to generate a reply, and injects it into the compose box.

* Shows loading state, confirmation message on success, and error message on failure.

* @param {Array<{sender: string, text: string}>} messages The conversation history.

*/

async function generateReply(messages) {

    const button = document.getElementById('draft-reply-btn');

    if (!button) {
        console.error('[LinkedIn Reply Automator] Draft Reply button not found');
        return;
    }

    // Create or get error display element
    let errorDisplay = document.getElementById('draft-reply-error');
    if (!errorDisplay) {
        errorDisplay = document.createElement('div');
        errorDisplay.id = 'draft-reply-error';
        errorDisplay.style.cssText = `
            position: absolute;
            bottom: 45px;
            right: 10px;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            max-width: 250px;
            z-index: 99;
        `;
        button.parentElement.appendChild(errorDisplay);
    }

    // Create or get success display element
    let successDisplay = document.getElementById('draft-reply-success');
    if (!successDisplay) {
        successDisplay = document.createElement('div');
        successDisplay.id = 'draft-reply-success';
        successDisplay.style.cssText = `
            position: absolute;
            bottom: 45px;
            right: 10px;
            padding: 8px 12px;
            border-radius: 4px;
            background-color: #0a66c2;
            color: white;
            font-size: 12px;
            max-width: 250px;
            z-index: 99;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        button.parentElement.appendChild(successDisplay);
    }

    try {
        // Set loading state
        button.textContent = '⏳ Drafting...';
        button.disabled = true;
        errorDisplay.textContent = '';
        errorDisplay.style.display = 'none';
        successDisplay.textContent = '';
        successDisplay.style.display = 'none';

        console.log('[LinkedIn Reply Automator] Starting reply generation...');

        // 1. Get config from the background service worker
        const config = await new Promise((resolve, reject) => {
            chrome.runtime.sendMessage({ type: "GET_CONFIG" }, response => {
                if (chrome.runtime.lastError) {
                    return reject(new Error(chrome.runtime.lastError.message));
                }
                if (!response || !response.backendUrl || !response.apiKey) {
                    return reject(new Error("Invalid config received from background script. Please configure settings."));
                }
                response.clientId = response.clientId || 'default';
                resolve(response);
            });
        });

        // 2. POST to the backend
        console.log('[LinkedIn Reply Automator] Calling backend:', `${config.backendUrl}/generate-reply`);
        const response = await fetch(`${config.backendUrl}/generate-reply`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${config.apiKey}`,
            },
            body: JSON.stringify({ messages: messages, client_id: config.clientId }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        const reply = data.reply;

        // 3. Inject reply into the compose box
        console.log('[LinkedIn Reply Automator] Injecting reply...');
        const injected = injectTextIntoBox(reply);

        if (injected) {
            // Show success message
            successDisplay.textContent = '✓ Reply inserted into compose box';
            successDisplay.style.display = 'block';
            successDisplay.style.opacity = '1';

            // Auto-dismiss success message after 3 seconds
            setTimeout(() => {
                successDisplay.style.opacity = '0';
                setTimeout(() => {
                    successDisplay.style.display = 'none';
                }, 300);
            }, 3000);
            
            console.log('[LinkedIn Reply Automator] Reply successfully generated and inserted');
        } else {
            throw new Error('Failed to inject text into compose box');
        }

    } catch (error) {
        // Show error message
        console.error('[LinkedIn Reply Automator] Error generating reply:', error);
        errorDisplay.textContent = `Error: ${error.message}`;
        errorDisplay.style.color = 'white';
        errorDisplay.style.backgroundColor = '#d32f2f';
        errorDisplay.style.display = 'block';
    } finally {
        // Restore button state
        button.textContent = '✦ Draft Reply';
        button.disabled = false;
    }

}

/**

* Observes the messaging container for changes and re-injects the button.

*/

function observeThread() {

    const targetNode = document.querySelector('.msg-s-message-list-container'); // This selector is for the thread container, not the compose box

    if (!targetNode) {

        console.log("Could not find message container to observe.");

        return;

    }

 

    const config = { childList: true, subtree: true };

 

    const callback = function(mutationsList, observer) {

        // A simple check to see if the message list itself has changed

        for(const mutation of mutationsList) {

            if (mutation.type === 'childList') {

                // Re-inject the button on any significant change.

                // A more robust solution might check for specific node additions/removals.

                injectGenerateButton();

                break;

            }

        }

    };

 

    const observer = new MutationObserver(callback);

    observer.observe(targetNode, config);

    console.log("MutationObserver started on message container.");

}

 

// --- Main Execution ---
console.log('[LinkedIn Reply Automator] Content script loaded');

// Use polling to handle LinkedIn's SPA dynamic loading
let observerStarted = false;
let injectionInterval = setInterval(() => {
    try {
        const form = getComposeBox();
        const btnExists = document.getElementById('draft-reply-btn');
        if (form && !btnExists) {
            injectGenerateButton();
        }
        // Also try to start MutationObserver once container is available (only once)
        if (!observerStarted && document.querySelector('.msg-s-message-list-container')) {
            observeThread();
            observerStarted = true;
            clearInterval(injectionInterval);
            console.log('[LinkedIn Reply Automator] MutationObserver started, polling stopped');
        }
    } catch (error) {
        console.error('[LinkedIn Reply Automator] Error in injection interval:', error);
    }
}, 1000);

// Initial attempts
try {
    const composeBox = getComposeBox();
    if (composeBox) {
        injectGenerateButton();
    } else {
        console.log('[LinkedIn Reply Automator] Compose box not ready on initial attempt, will retry via polling');
    }
} catch (error) {
    console.log('[LinkedIn Reply Automator] Initial button injection failed (may retry):', error.message);
}

try {
    if (!observerStarted) {
        observeThread();
        observerStarted = true;
    }
} catch (error) {
    console.log('[LinkedIn Reply Automator] Initial observer setup failed (will retry):', error.message);
}

// --- Message Listener for Popup ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Content script received message:', request.type);
    try {
        if (request.type === 'SCRAPE_CONVERSATION') {
            console.log('Attempting to scrape thread...');
            const messages = scrapeThread();
            console.log('Scraped messages:', messages.length);
            sendResponse({ messages: messages || [] });
            return true; // Keep channel open for sendResponse
        } else if (request.type === 'INSERT_REPLY') {
            const success = injectTextIntoBox(request.reply);
            sendResponse({ success, error: success ? null : 'Could not find the LinkedIn message box' });
            return true; // Keep channel open for sendResponse
        }
    } catch (error) {
        console.error('Error in message listener:', error);
        sendResponse({ error: error.message, messages: [] });
        return true; // Keep channel open for sendResponse
    }
});