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
        },
        'pt-BR': {
            placeholder: "Pergunte algo...",
            listening: "Ouvindo...",
            exploring: "Explorando...",
            error_mic: "Acesso ao microfone necessário.",
            error_ai: "Erro de Conexão: IA Indisponível",
            interview_start: "🎙️ Modo Entrevista Ativado. Sou seu Líder Técnico. Diga 'Começar' quando estiver pronto.",
            interview_end: "Modo entrevista encerrado.",
            voice_enabled: "Modo de voz ativado.",
            welcome: "Olá! Sou seu assistente de carreira. Pergunte sobre Rust, Go ou como conectar seu GitHub."
        },
        'es': {
            placeholder: "Pregunta algo...",
            listening: "Escuchando...",
            exploring: "Explorando...",
            error_mic: "Se requiere acceso al micrófono.",
            error_ai: "Error de conexión: IA no disponible",
            interview_start: "🎙️ Modo Entrevista Activado. Soy tu Líder Técnico. Di 'Comenzar' cuando estés listo.",
            interview_end: "Modo entrevista finalizado.",
            voice_enabled: "Modo de voz activado.",
            welcome: "¡Hola! Soy tu asistente de carrera. Pregunta sobre Rust, Go o cómo conectar tu GitHub."
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

        // Detect Language from Browser
        const browserLang = navigator.language || 'en';
        if (browserLang.startsWith('pt')) currentLang = 'pt-BR';
        else if (browserLang.startsWith('es')) currentLang = 'es';
        else currentLang = 'en';

        // Set Selector
        if (langSelect) {
            // Check if option exists, otherwise default to EN
            const options = Array.from(langSelect.options).map(o => o.value);
            if (!options.includes(currentLang)) currentLang = 'en';

            langSelect.value = currentLang;

            langSelect.addEventListener('change', (e) => {
                currentLang = e.target.value;
                updateUIText();
            });
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
             welcomeMsg.innerText = t.welcome;
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
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            showToast("Browser does not support voice recognition.");
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        const t = translations[currentLang] || translations['en'];

        // Set recognition language
        recognition.lang = currentLang;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        // Visual indicator
        micBtn.style.color = 'var(--error-color)';
        micBtn.style.borderColor = 'var(--error-color)';
        showToast(t.listening);

        recognition.start();

        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            input.value = speechResult;

            micBtn.style.color = 'var(--primary-color)';
            micBtn.style.borderColor = 'var(--primary-color)';

            // Auto-send
            sendMessage();
        };

        recognition.onspeechend = () => {
            recognition.stop();
            micBtn.style.color = 'var(--primary-color)';
            micBtn.style.borderColor = 'var(--primary-color)';
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            micBtn.style.color = 'var(--primary-color)';
            micBtn.style.borderColor = 'var(--primary-color)';

            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                 alert("MICROPHONE BLOCKED: You are likely on HTTP or have denied permission. Please reload directly with HTTPS.");
            } else {
                 showToast("Error: " + event.error);
            }
        };
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
        utterance.lang = currentLang; // Use selected language
        utterance.rate = 1.1;

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
