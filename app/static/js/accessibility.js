// --- ACCESSIBILITY MODULE ---

// 1. STATE INITIALIZATION (Prevent FOUC)
// This runs immediately when the file is loaded.
(function initAccessibility() {
    if (typeof localStorage === 'undefined') return;

    // Class-based toggles
    const toggles = ['dyslexic-font', 'high-contrast', 'reduced-motion', 'big-targets'];
    toggles.forEach(cls => {
        if (localStorage.getItem(cls) === 'true') {
            document.documentElement.classList.add(cls);
        }
    });

    // Filters
    const savedFilter = localStorage.getItem('color-filter');
    if (savedFilter && savedFilter !== 'none') {
        document.documentElement.setAttribute('data-color-filter', savedFilter);
    }

    // Font Size
    const savedSize = localStorage.getItem('font-size');
    if (savedSize) {
        document.documentElement.style.fontSize = savedSize + '%';
    }
})();

// 2. DOM EVENT LISTENERS (UI SYNC)
document.addEventListener("DOMContentLoaded", () => {
    // Sync Toggle Inputs
    const toggles = ['dyslexic-font', 'high-contrast', 'reduced-motion', 'big-targets'];
    toggles.forEach(cls => {
        const el = document.getElementById('a11y-' + cls);
        if (el && localStorage.getItem(cls) === 'true') {
            el.checked = true;
        }
    });

    // Sync State Toggles (Non-class based)
    const stateToggles = ['visual-alerts', 'simple-text'];
    stateToggles.forEach(key => {
        const el = document.getElementById('a11y-' + key);
        if (el && localStorage.getItem(key) === 'true') {
            el.checked = true;
        }
    });

    // Sync Filters
    const savedFilter = localStorage.getItem('color-filter');
    const filterEl = document.getElementById('color-filter');
    if (filterEl && savedFilter && savedFilter !== 'none') {
        filterEl.value = savedFilter;
    }

    // Sync Font Size
    const savedSize = localStorage.getItem('font-size') || 100;
    const rangeEl = document.getElementById('font-size-range');
    if (rangeEl) {
        rangeEl.value = savedSize;
    }

    // Restore Reading Guide state
    if (localStorage.getItem('readingGuide') === 'active') {
        const guideCheck = document.getElementById('a11y-guide');
        if (guideCheck) guideCheck.checked = true;
        // Force enable without toggling
        if (typeof window.toggleReadingGuide === 'function') {
            window.toggleReadingGuide(true);
        }
    }
});


// --- CORE FUNCTIONS (Global Scope for inline onchange handlers, or attached via JS) ---

// Make functions available globally so `onchange="..."` in HTML still works
window.toggleA11y = function(className) {
    document.documentElement.classList.toggle(className);
    localStorage.setItem(className, document.documentElement.classList.contains(className));
};

window.toggleA11yState = function(key) {
    const el = document.getElementById('a11y-' + key);
    if(el) localStorage.setItem(key, el.checked);
};

window.applyColorFilter = function(filterName) {
    document.documentElement.setAttribute('data-color-filter', filterName);
    localStorage.setItem('color-filter', filterName);
};

window.updateFontSize = function(val) {
    document.documentElement.style.fontSize = val + '%';
    localStorage.setItem('font-size', val);
};


// --- READING GUIDE ---
let guideActive = false;
window.toggleReadingGuide = function(forceState) {
    if (typeof forceState === 'boolean') {
        guideActive = forceState;
    } else {
        guideActive = !guideActive;
    }

    localStorage.setItem('readingGuide', guideActive ? 'active' : 'inactive');

    let bar = document.getElementById('reading-guide-bar');

    // Create bar if missing (e.g. on pages other than accessibility.html if we want it global)
    // For now, we assume the HTML exists or we create it.
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'reading-guide-bar';
        bar.style.cssText = "display: none; position: fixed; height: 30px; width: 100%; background: rgba(255, 242, 0, 0.15); pointer-events: none; z-index: 99999; border-top: 2px solid #ffee00; border-bottom: 2px solid #ffee00; top: 0; left: 0; box-shadow: 0 0 100px rgba(0,0,0,0.5);";
        document.body.appendChild(bar);
    }

    bar.style.display = guideActive ? 'block' : 'none';

    if (guideActive) {
        document.addEventListener('mousemove', moveGuide);
    } else {
        document.removeEventListener('mousemove', moveGuide);
    }
};

function moveGuide(e) {
    const bar = document.getElementById('reading-guide-bar');
    if(bar) bar.style.top = (e.clientY - 15) + 'px';
}


// --- VOICE NAVIGATION (Web Speech API) ---
let recognition;

window.toggleVoiceNav = function() {
    const statusEl = document.getElementById('voice-status');
    const checkbox = document.getElementById('a11y-voice');

    if (!checkbox) return; // Guard clause

    if (!checkbox.checked) {
        if (recognition) recognition.stop();
        if (statusEl) statusEl.style.display = 'none';
        return;
    }

    // Browser Support Check
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Your browser does not support Voice Commands. Try Chrome or Edge.");
        checkbox.checked = false;
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    try {
        recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = false;

        recognition.onstart = () => {
            if (statusEl) {
                statusEl.style.display = 'block';
                statusEl.innerText = "🎤 Listening... (Say 'Help' for commands)";
            }
        };

        recognition.onresult = (event) => {
            if (event.results.length > 0) {
                const command = event.results[event.results.length - 1][0].transcript.trim().toLowerCase();
                console.log("Voice Command:", command);
                if (statusEl) statusEl.innerText = `🎤 Heard: "${command}"`;
                handleVoiceCommand(command);
            }
        };

        recognition.onerror = (e) => {
            console.error("Voice Recognition Error:", e);
            if (statusEl) statusEl.innerText = "❌ Error listening. Please toggle off/on.";
            // Don't auto-uncheck, let user retry
        };

        recognition.onend = () => {
             // If still checked, restart?
             // SpeechRecognition often stops automatically.
             // For now, we leave it be or it might loop indefinitely if error.
             if(checkbox.checked && recognition) {
                 try { recognition.start(); } catch(e) {}
             }
        };

        recognition.start();

    } catch (err) {
        console.error("Failed to initialize speech recognition", err);
        checkbox.checked = false;
        alert("Failed to access microphone or speech API.");
    }
};

function handleVoiceCommand(cmd) {
    // Navigation Map
    if (cmd.includes("dashboard") || cmd.includes("home")) {
        window.location.href = "/dashboard";
    } else if (cmd.includes("config") || cmd.includes("security")) {
        window.location.href = "/dashboard/security";
    } else if (cmd.includes("accessibility")) {
        window.location.href = "/dashboard/accessibility";
    } else if (cmd.includes("logout") || cmd.includes("exit")) {
        window.location.href = "/logout";
    } else if (cmd.includes("down") || cmd.includes("scroll down")) {
        window.scrollBy({ top: 400, behavior: 'smooth' });
    } else if (cmd.includes("up") || cmd.includes("scroll up")) {
        window.scrollBy({ top: -400, behavior: 'smooth' });
    } else if (cmd.includes("help")) {
        alert("Commands: 'Go to Dashboard', 'Settings', 'Accessibility', 'Logout', 'Scroll Down', 'Scroll Up'");
    }
}
