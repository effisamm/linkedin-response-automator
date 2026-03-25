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

* Fetches config, calls the backend to generate a reply, and injects it.

* @param {Array<{sender: string, text: string}>} messages The conversation history.

*/

async function generateReply(messages) {

    const button = document.getElementById('draft-reply-btn');

    const errorDisplay = document.getElementById('draft-reply-error') || document.createElement('div');

    errorDisplay.id = 'draft-reply-error';

    errorDisplay.style.cssText = 'position: absolute; bottom: 45px; right: 10px; color: red; font-size: 12px;';

    button.parentElement.appendChild(errorDisplay);

 

    try {

        button.textContent = '✦ Drafting...';

        button.disabled = true;

        errorDisplay.textContent = '';

 

        // 1. Get config from the background service worker

        const config = await new Promise((resolve, reject) => {

            chrome.runtime.sendMessage({ type: "GET_CONFIG" }, response => {

                if (chrome.runtime.lastError) {

                    return reject(new Error(chrome.runtime.lastError.message));

                }

                if (!response || !response.backendUrl || !response.apiKey) {

                    return reject(new Error("Invalid config received from background script."));

                }

                resolve(response);

            });

        });

 

        // 2. POST to the backend

        const response = await fetch(`${config.backendUrl}/generate-reply`, {

            method: 'POST',

            headers: {

                'Content-Type': 'application/json',

                'Authorization': `Bearer ${config.apiKey}`,

            },

            body: JSON.stringify({ messages: messages }),

        });

 

        if (!response.ok) {

            const errorData = await response.json();

            throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);

        }

 

        const data = await response.json();

        const reply = data.reply;

 

        // 3. On success, set the text content and dispatch an event

        const messageBox = document.querySelector('.msg-form__content-editable p');

        if (messageBox) {

            messageBox.textContent = reply;

            // Dispatch input event for React to pick up the change

            const inputEvent = new Event('input', { bubbles: true, cancelable: true });

            messageBox.dispatchEvent(inputEvent);

        }

 

    } catch (error) {

        // 4. On error, show an inline error message

        console.error("Error generating reply:", error);

        errorDisplay.textContent = `Error: ${error.message}`;

    } finally {

        button.textContent = '✦ Draft Reply';

        button.disabled = false;

    }

}

 

/**

* Observes the messaging container for changes and re-injects the button.

*/

function observeThread() {

    const targetNode = document.querySelector('.msg-s-message-list-container');

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

// Initial injection

injectGenerateButton();

// Start observing for thread changes

observeThread();

// --- Message Listener for Popup ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'SCRAPE_CONVERSATION') {
        const messages = scrapeThread();
        sendResponse({ messages: messages });
    }
});