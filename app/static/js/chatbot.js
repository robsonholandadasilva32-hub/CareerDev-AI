document.addEventListener("DOMContentLoaded", () => {
    // --- Seletores do DOM ---
    const widget = document.getElementById('chatbot-widget');
    const openBtn = document.getElementById('chatbot-open-btn');
    const closeBtn = document.getElementById('chatbot-close-btn');
    const sendBtn = document.getElementById('chatbot-send-btn');
    const micBtn = document.getElementById('chatbot-mic-btn');
    const input = document.getElementById('chatbot-input');
    const messagesArea = document.getElementById('chatbot-messages');

    // Variáveis de Estado
    let currentLang = document.documentElement.lang || 'en'; 
    
    // Objeto de traduções simples para fallback
    const translations = {
        'en': { listening: "Listening...", error_mic: "Microphone access denied." },
        'pt': { listening: "Ouvindo...", error_mic: "Acesso ao microfone negado." },
        'es': { listening: "Escuchando...", error_mic: "Acceso al micrófono denegado." }
    };

    // --- Event Listeners Iniciais ---
    if (openBtn) openBtn.addEventListener('click', toggleChat);
    if (closeBtn) closeBtn.addEventListener('click', toggleChat);
    if (micBtn) micBtn.addEventListener('click', startVoiceInput);
    if (sendBtn) sendBtn.addEventListener('click', sendMessage);
    
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    // --- Modal Events ---
    const closeMicBtn = document.getElementById('btn-close-mic-modal');
    const dismissMicBtn = document.getElementById('btn-dismiss-mic-modal');
    
    if (closeMicBtn) closeMicBtn.addEventListener('click', closeMicModal);
    if (dismissMicBtn) dismissMicBtn.addEventListener('click', closeMicModal);

    // --- Core Logic ---

    function showMicModal() {
        const modal = document.getElementById('mic-modal');
        if (modal) modal.style.display = 'flex';
    }

    function closeMicModal() {
        const modal = document.getElementById('mic-modal');
        if (modal) modal.style.display = 'none';
    }

    function toggleChat() {
        if (!widget) return;
        if (widget.style.display === 'none' || widget.style.display === '') {
            widget.style.display = 'flex';
            if (input) input.focus();
        } else {
            widget.style.display = 'none';
        }
    }

    function showToast(message) {
        let toast = document.getElementById('chatbot-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'chatbot-toast';
            toast.className = 'chatbot-toast';
            widget.appendChild(toast);
        }
        toast.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    // --- Voice Input Logic (Corrigida e Estabilizada) ---
    function startVoiceInput() {
        // 1. Definição única da API
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        // 2. Verificação de suporte
        if (!SpeechRecognition) {
            console.error("CRITICAL: Browser does not support Speech API");
            showToast("Browser does not support voice recognition.");
            alert("Voice features are optimized for Chrome and Edge. Please switch browsers for the best experience.");
            return;
        }

        // 3. Inicialização
        const recognition = new SpeechRecognition();
        const t = translations[currentLang] || translations['en'];

        recognition.lang = currentLang;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        // 4. Indicadores Visuais
        micBtn.style.color = ''; 
        micBtn.style.borderColor = '';
        micBtn.classList.add('pulse-red');
        
        showToast(t.listening || "Listening...");

        // 5. Iniciar reconhecimento com segurança
        try {
            recognition.start();
        } catch (e) {
            console.error("Recognition Start Error:", e);
            micBtn.classList.remove('pulse-red');
            showToast("Error starting microphone");
        }

        // --- Event Handlers da API ---
        
        recognition.onresult = (event) => {
            const speechResult = event.results[0][0].transcript;
            if (input) input.value = speechResult;

            micBtn.classList.remove('pulse-red');
            
            // Envio automático
            sendMessage();
        };

        recognition.onspeechend = () => {
            recognition.stop();
            micBtn.classList.remove('pulse-red');
        };

        recognition.onerror = (event) => {
            console.error("Speech Recognition Error:", event.error);
            micBtn.classList.remove('pulse-red');

            if (event.error === 'not-allowed') {
                 showToast(t.error_mic || "Mic permission denied");
                 showMicModal();
            } else if (event.error === 'no-speech') {
                 showToast("No speech detected. Please speak clearly.");
            } else {
                 showToast("Error: " + event.error);
            }
        };

        recognition.onend = () => {
             micBtn.classList.remove('pulse-red');
        };
    }

    // --- Message Logic ---
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        appendMessage('user', text);
        input.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: text })
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();
            const botResponse = data.response || data.message || "No response received";
            
            appendMessage('bot', botResponse);

        } catch (error) {
            console.error('Error sending message:', error);
            appendMessage('bot', "Sorry, I encountered an error connecting to the server.");
        }
    }

    function appendMessage(sender, text) {
        if (!messagesArea) return;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}`; 
        msgDiv.textContent = text;
        
        messagesArea.appendChild(msgDiv);
        messagesArea.scrollTop = messagesArea.scrollHeight;
    }
});
