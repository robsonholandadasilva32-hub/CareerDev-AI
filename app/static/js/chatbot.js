document.addEventListener("DOMContentLoaded", () => {
    // State
    let isVoiceEnabled = false;
    let isInterviewMode = false;
    let isEmbedded = false;
    let currentLang = 'en'; // Default

    // UI Elements
    const widget = document.getElementById('chatbot-widget');
    const toggleBtn = document.getElementById('chatbot-toggle');
    const closeBtn = document.getElementById('btn-close-chat');
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('btn-send');
    const micBtn = document.getElementById('btn-mic');
    const voiceToggleBtn = document.getElementById('voice-toggle');
    const interviewBtn = document.getElementById('interview-toggle');
    const dashboardInterviewBtn = document.getElementById('dashboard-interview-toggle');
    const langSelect = document.getElementById('chat-lang-selector');
    const messagesContainer = document.getElementById('chatbot-messages');
    const statusDiv = document.getElementById('chatbot-status');
    const statusText = document.getElementById('status-text');

    // Translations
    const translations = {
        'en': {
            placeholder: "Ask something...",
            listening: "Listening...",
            exploring: "Exploring...",
            error_mic: "Microphone access required.",
            error_ai: "Connection Error: AI Unavailable",
            interview_start: "🎙️ Interview Mode Activated. I am your Senior Tech Lead. Say 'Start' when ready.",
            interview_end: "Interview mode ended.",
            voice_enabled: "Voice mode enabled.",
            welcome: "Hello! I am your career assistant. Ask about Rust, Go, or how to connect your GitHub."
        }
    };

    // --- Initialization ---
    function init() {
        // Check for Embedded Mode (Career OS Dashboard)
        const embeddedTarget = document.getElementById('embedded-chatbot-target');
        if (embeddedTarget && (window.CAREER_OS_EMBEDDED_CHAT || document.body.classList.contains('career-os-mode'))) {
            isEmbedded = true;

            // Move Components
            const messages = document.getElementById('chatbot-messages');
            const status = document.getElementById('chatbot-status');
            const inputArea = document.querySelector('.chatbot-input');
            const controls = document.querySelector('.header-controls');

            if (messages && inputArea) {
                embeddedTarget.innerHTML = ''; // Clear placeholder

                // Move Controls to Dashboard Header
                const dashboardHeader = document.querySelector('.chat-terminal-header');
                if (dashboardHeader && controls) {
                    // Hide Close Button
                    const closeBtn = document.getElementById('btn-close-chat');
                    if (closeBtn) closeBtn.style.display = 'none';
                    dashboardHeader.appendChild(controls);
                }

                // Move Main Components
                embeddedTarget.appendChild(messages);
                if (status) embeddedTarget.appendChild(status);
                embeddedTarget.appendChild(inputArea);

                // Styling Overrides for Embedded View
                messages.style.flex = '1';
                messages.style.height = 'auto';
                messages.style.maxHeight = 'none';
                inputArea.style.borderRadius = '0';

                // Hide Original Floating Widget
                if (widget) widget.style.display = 'none';
                if (toggleBtn) toggleBtn.style.display = 'none';
            }
        }

        // Enforce English Only
        currentLang = 'en';

        // Check Browser Support (UX Improvement)
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
             if (micBtn) micBtn.style.display = 'none';
        }

        updateUIText();
        attachEventListeners();
    }

    function updateUIText() {
        const t = translations[currentLang] || translations['en'];
        if (input) input.placeholder = t.placeholder;

        // Update welcome message
        const welcomeMsg = document.getElementById('chatbot-welcome-msg');
        if (welcomeMsg) {
             // Context-Aware Greeting: Use server-provided message if available
             const serverGreeting = welcomeMsg.getAttribute('data-server-greeting');
             if (serverGreeting && serverGreeting.trim() !== '') {
                 welcomeMsg.innerText = serverGreeting;
             } else {
                 welcomeMsg.innerText = t.welcome;
             }
        }
    }

    function attachEventListeners() {
        if (toggleBtn) toggleBtn.addEventListener('click', toggleChat);
        if (closeBtn) closeBtn.addEventListener('click', toggleChat);
        if (voiceToggleBtn) voiceToggleBtn.addEventListener('click', toggleVoice);
        if (interviewBtn) interviewBtn.addEventListener('click', toggleInterview);
        if (dashboardInterviewBtn) dashboardInterviewBtn.addEventListener('click', toggleInterview);
        if (micBtn) micBtn.addEventListener('click', startVoiceInput);
        if (sendBtn) sendBtn.addEventListener('click', sendMessage);
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        }
    }

    // --- Core Logic ---

    function toggleChat() {
        if (isEmbedded) return; // Disable toggle in embedded mode

        if (widget.style.display === 'none' || widget.style.display === '') {
            widget.style.display = 'flex';
            toggleBtn.style.display = 'none';
            input.focus();
        } else {
            widget.style.display = 'none';
            toggleBtn.style.display = 'flex';
        }
    }

    function toggleVoice() {
        isVoiceEnabled = !isVoiceEnabled;
        const t = translations[currentLang] || translations['en'];

        if (isVoiceEnabled) {
            voiceToggleBtn.innerHTML = '🔊';
            voiceToggleBtn.setAttribute('aria-label', "Disable voice");
            voiceToggleBtn.title = "Disable voice";
            speakText(t.voice_enabled);
        } else {
            voiceToggleBtn.innerHTML = '🔇';
            voiceToggleBtn.setAttribute('aria-label', "Enable voice");
            voiceToggleBtn.title = "Enable voice";
            window.speechSynthesis.cancel();
        }
    }

    function toggleInterview() {
        isInterviewMode = !isInterviewMode;
        const header = document.querySelector('.chatbot-header') || document.querySelector('.chat-terminal-header');
        const t = translations[currentLang] || translations['en'];

        if (isInterviewMode) {
            interviewBtn.style.color = 'var(--secondary-color)';
            interviewBtn.title = "Exit Interview";

            if (dashboardInterviewBtn) {
                dashboardInterviewBtn.innerText = "END_SIMULATION";
                dashboardInterviewBtn.style.borderColor = "var(--neon-green)";
                dashboardInterviewBtn.style.color = "var(--neon-green)";
            }

            if (header) header.style.background = 'linear-gradient(90deg, rgba(76, 29, 149, 0.95), rgba(17, 24, 39, 0.95))';
            addMessage(t.interview_start, 'bot');
            if (isVoiceEnabled) speakText(t.interview_start);
        } else {
            interviewBtn.style.color = 'var(--text-muted)';
            interviewBtn.title = "Interview Mode";

            if (dashboardInterviewBtn) {
                dashboardInterviewBtn.innerText = "START_SIMULATION";
                dashboardInterviewBtn.style.borderColor = "var(--neon-cyan)";
                dashboardInterviewBtn.style.color = "var(--neon-cyan)";
            }

            if (header) header.style.background = 'rgba(10, 15, 28, 0.9)';
            addMessage(t.interview_end, 'bot');
        }
    }

    function startVoiceInput() {
        console.log("STT: Initializing...");

        // Polyfill Strategy
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Your browser does not support Speech Recognition. Please use Chrome or Edge.");
            return;
        }

        const recognition = new SpeechRecognition();
        const t = translations[currentLang] || translations['en'];

        // Strict English Policy
        recognition.lang = 'en-US';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        // Visual Feedback State
        if (micBtn) {
            micBtn.classList.add('listening');
            micBtn.setAttribute('aria-label', "Stop listening");
        }
        showToast(t.listening);

        console.log("STT: Started. Waiting for audio...");
        recognition.start();

        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            console.log("STT: Result received: ", speechResult);
            input.value = speechResult;

            resetMicButton();

            // Auto-send
            sendMessage();
        };

        recognition.onspeechend = () => {
            console.log("STT: Speech ended.");
            recognition.stop();
            resetMicButton();
        };

        recognition.onerror = function(event) {
            console.log("STT: Error: ", event.error);
            resetMicButton(); // Reset UI immediately

            if (event.error === 'not-allowed') {
                alert("⚠️ MICROPHONE BLOCKED!\n\nYour browser blocked access. Please:\n1. Click the 'Lock' icon in the URL bar.\n2. Allow Microphone.\n3. Reload the page.");
            } else if (event.error === 'service-not-allowed') {
                alert("⚠️ SPEECH SERVICE BLOCKED!\n\nThis feature requires a secure HTTPS connection or localhost.");
            } else {
                showToast("Error: " + event.error);
            }
        };
    }

    function resetMicButton() {
        if (micBtn) {
            micBtn.classList.remove('listening');
            micBtn.style.color = 'var(--primary-color)';
            micBtn.style.borderColor = 'var(--primary-color)';
            micBtn.setAttribute('aria-label', "Speak message");
        }
        hideToast();
    }

    function hideToast() {
        const toast = document.getElementById('chatbot-toast');
        if (toast) {
            toast.classList.remove('show');
        }
    }

    async function sendMessage() {
        let text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';

        const t = translations[currentLang] || translations['en'];

        // Status
        statusText.innerText = t.exploring;
        statusDiv.style.display = 'flex';

        // Audio Accessibility
        if (isVoiceEnabled) {
            speakText(t.exploring);
        }

        try {
            // Force HTTPS if not localhost
            const apiUrl = (window.location.hostname === 'localhost') ? '/chatbot/message' : 'https://' + window.location.host + '/chatbot/message';

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    mode: isInterviewMode ? 'interview' : 'standard',
                    lang: currentLang // Send selected language
                })
            });

            if (!response.ok) {
                throw new Error(`Server Error: ${response.status}`);
            }

            const data = await response.json();

            statusDiv.style.display = 'none';
            addMessage(data.response, 'bot');

            // Visual Alerts
            if (localStorage.getItem('visual-alerts') === 'true') {
                triggerVisualAlert();
            }

            // TTS with correct language
            if (isVoiceEnabled) {
                speakText(data.response);
            }

        } catch (error) {
            statusDiv.style.display = 'none';
            console.error("Chatbot Error:", error);
            showToast(t.error_ai);
            addMessage(t.error_ai, 'bot');
            if (isVoiceEnabled) speakText(t.error_ai);
        }
    }

    function speakText(text) {
        if (!isVoiceEnabled || !('speechSynthesis' in window)) return;

        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US'; // Use selected language
        utterance.rate = 0.9;     // Slower speech rate for better comprehension
        utterance.pitch = 1.0;    // Natural pitch

        window.speechSynthesis.speak(utterance);
    }

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `message ${sender}`;
        div.innerText = text;
        messagesContainer.appendChild(div);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function showToast(message) {
        let toast = document.getElementById('chatbot-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'chatbot-toast';
            toast.className = 'chatbot-toast';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    function triggerVisualAlert() {
        const flash = document.createElement('div');
        flash.className = 'visual-flash-overlay';
        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 500);
    }

    // Run Init
    init();
});
