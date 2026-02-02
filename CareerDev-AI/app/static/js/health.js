const HealthModule = {
    state: {
        postureEnabled: false,
        timer202020Enabled: false,
        timerHydrationEnabled: false,
        hydrationInterval: 30, // minutes
        stream: null,
        postureIntervalId: null,
        timers: {
            t202020: null, // timeout ID
            hydration: null // timeout ID
        }
    },

    init: function() {
        this.loadState();
        this.initUI();
        this.checkTimers();

        // Init Draggable PiP
        const pip = document.getElementById('pip-container');
        if (pip) makeDraggable(pip);
    },

    loadState: function() {
        this.state.postureEnabled = localStorage.getItem('health_posture') === 'true';
        this.state.timer202020Enabled = localStorage.getItem('health_202020') === 'true';
        this.state.timerHydrationEnabled = localStorage.getItem('health_hydration') === 'true';
        this.state.hydrationInterval = parseInt(localStorage.getItem('health_hydration_interval') || '30');
    },

    initUI: function() {
        const elPosture = document.getElementById('posture-toggle');
        const el202020 = document.getElementById('202020-toggle');
        const elHydration = document.getElementById('hydration-toggle');
        const elInterval = document.getElementById('hydration-interval');

        if (elPosture) elPosture.checked = this.state.postureEnabled;
        if (el202020) el202020.checked = this.state.timer202020Enabled;
        if (elHydration) elHydration.checked = this.state.timerHydrationEnabled;
        if (elInterval) elInterval.value = this.state.hydrationInterval;

        // Posture auto-start if enabled
        if (this.state.postureEnabled) {
            this.startPostureCheck();
        }
    },

    // --- NOTIFICATIONS ---
    requestPermissions: async function() {
        if (!("Notification" in window)) return false;
        if (Notification.permission === "granted") return true;
        if (Notification.permission !== "denied") {
            const permission = await Notification.requestPermission();
            return permission === "granted";
        }
        return false;
    },

    notify: function(title, body) {
        if (Notification.permission === "granted") {
            // Check if service worker is available for robust notifications (optional, standard is fine)
            new Notification(title, {
                body: body,
                icon: '/static/img/logo.png' // Fallback handled by browser
            });
        } else {
            this.showToast(title + ": " + body, "info");
        }
    },

    showToast: function(msg, type) {
        if (window.showToast) {
            window.showToast(msg, type);
        } else {
            console.log("Toast:", msg);
            alert(msg);
        }
    },

    // --- POSTURE ---
    togglePosture: async function() {
        const toggle = document.getElementById('posture-toggle');
        this.state.postureEnabled = toggle.checked;
        localStorage.setItem('health_posture', this.state.postureEnabled);

        if (this.state.postureEnabled) {
            await this.startPostureCheck();
        } else {
            this.stopPostureCheck();
        }
    },

    startPostureCheck: async function() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            this.state.stream = stream;

            this.showPiP(stream);

            // Start analysis loop (5 min)
            this.state.postureIntervalId = setInterval(() => this.analyzePosture(), 300000);

            // Initial check
            setTimeout(() => this.analyzePosture(), 2000);

            const indicator = document.getElementById('health-indicator');
            if (indicator) indicator.style.display = 'block';

            this.showToast("Posture AI Active", "success");

        } catch (err) {
            console.error("Camera Error:", err);
            this.showToast("Camera access required for Posture AI.", "warning");

            // Revert state
            const toggle = document.getElementById('posture-toggle');
            if (toggle) toggle.checked = false;
            this.state.postureEnabled = false;
            localStorage.setItem('health_posture', false);
        }
    },

    stopPostureCheck: function() {
        if (this.state.stream) {
            this.state.stream.getTracks().forEach(t => t.stop());
            this.state.stream = null;
        }
        if (this.state.postureIntervalId) {
            clearInterval(this.state.postureIntervalId);
            this.state.postureIntervalId = null;
        }

        const pip = document.getElementById('pip-container');
        if (pip) pip.style.display = 'none';

        const indicator = document.getElementById('health-indicator');
        if (indicator) indicator.style.display = 'none';

        // Ensure toggle matches state (if called from Close button)
        const toggle = document.getElementById('posture-toggle');
        if (toggle) toggle.checked = false;
        this.state.postureEnabled = false;
        localStorage.setItem('health_posture', false);

        this.showToast("Posture AI Stopped", "info");
    },

    showPiP: function(stream) {
        const pip = document.getElementById('pip-container');
        const video = document.getElementById('pip-video');
        if (pip && video) {
            video.srcObject = stream;
            video.play();
            pip.style.display = 'flex';
        }
    },

    analyzePosture: async function() {
        const video = document.getElementById('pip-video');
        if (!video || !this.state.stream) return;

        try {
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            const base64 = canvas.toDataURL('image/jpeg', 0.5);

            const res = await fetch('/api/v1/monitoring/analyze-posture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: base64 })
            });

            if (res.status === 401) return; // Session expired

            const data = await res.json();
            if (data.status === 'poor_posture') {
                this.notify("Posture Alert", data.message);
            }
        } catch (e) {
            console.error("Analysis failed:", e);
        }
    },

    // --- TIMERS ---

    // 20-20-20
    toggle202020: async function() {
        const toggle = document.getElementById('202020-toggle');
        const isEnabled = toggle.checked;

        if (isEnabled) {
            const granted = await this.requestPermissions();
            if (!granted) this.showToast("Notifications disabled. Using visual alerts only.", "warning");

            this.setTimer('t202020', 20); // 20 mins
        } else {
            this.clearTimer('t202020');
        }

        this.state.timer202020Enabled = isEnabled;
        localStorage.setItem('health_202020', isEnabled);
    },

    // Hydration
    updateHydrationInterval: function() {
        const val = document.getElementById('hydration-interval').value;
        this.state.hydrationInterval = parseInt(val);
        localStorage.setItem('health_hydration_interval', val);

        // If running, restart with new interval
        if (this.state.timerHydrationEnabled) {
            this.setTimer('hydration', this.state.hydrationInterval);
            this.showToast(`Hydration timer set to ${val} minutes.`, "success");
        }
    },

    toggleHydration: async function() {
        const toggle = document.getElementById('hydration-toggle');
        const isEnabled = toggle.checked;

        if (isEnabled) {
            const granted = await this.requestPermissions();
            if (!granted) this.showToast("Notifications disabled. Using visual alerts only.", "warning");

            this.setTimer('hydration', this.state.hydrationInterval);
        } else {
            this.clearTimer('hydration');
        }

        this.state.timerHydrationEnabled = isEnabled;
        localStorage.setItem('health_hydration', isEnabled);
    },

    // Core Timer Logic
    setTimer: function(key, minutes) {
        // Clear existing
        this.clearTimer(key, false);

        const target = Date.now() + (minutes * 60 * 1000);
        localStorage.setItem(`health_target_${key}`, target);

        this.scheduleNotification(key, minutes * 60 * 1000);
    },

    clearTimer: function(key, clearStorage = true) {
        if (this.state.timers[key]) {
            clearTimeout(this.state.timers[key]);
            this.state.timers[key] = null;
        }
        if (clearStorage) localStorage.removeItem(`health_target_${key}`);
    },

    scheduleNotification: function(key, delay) {
        this.state.timers[key] = setTimeout(() => {
            this.triggerAlert(key);
            // Restart
            const interval = key === 't202020' ? 20 : this.state.hydrationInterval;
            this.setTimer(key, interval);
        }, delay);
    },

    checkTimers: function() {
        // 20-20-20
        if (this.state.timer202020Enabled) this.resumeTimer('t202020', 20);
        // Hydration
        if (this.state.timerHydrationEnabled) this.resumeTimer('hydration', this.state.hydrationInterval);
    },

    resumeTimer: function(key, defaultIntervalMinutes) {
        const targetStr = localStorage.getItem(`health_target_${key}`);
        if (!targetStr) {
            // Should be running but no target? Start fresh.
            this.setTimer(key, defaultIntervalMinutes);
            return;
        }

        const target = parseInt(targetStr);
        const now = Date.now();
        const remaining = target - now;

        if (remaining > 0) {
            // Resume
            this.scheduleNotification(key, remaining);
        } else {
            // Missed it while away
            // User requested: "Just reset the timer to the next interval silently and show a small toast"
            const label = key === 't202020' ? 'Eye Rest' : 'Hydration';
            this.showToast(`Welcome back. ${label} timer restarted.`, "info");

            // Start fresh
            this.setTimer(key, defaultIntervalMinutes);
        }
    },

    triggerAlert: function(key) {
        if (key === 't202020') {
            this.notify("20-20-20 Rule", "Look away from the screen at something 20 feet away for 20 seconds!");
        } else {
            this.notify("Hydration Reminder", "Time to drink some water! 💧");
        }

        // Play subtle sound? (Optional, skipping for now as not requested)
    }
};

// Global Draggable Helper
function makeDraggable(elmnt) {
    var pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

    // Use header if available for drag handle
    const header = document.getElementById(elmnt.id + "-header");
    const target = header || elmnt;

    target.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
        elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";

        // Reset bottom/right to allow top/left positioning
        elmnt.style.bottom = 'auto';
        elmnt.style.right = 'auto';
    }

    function closeDragElement() {
        document.onmouseup = null;
        document.onmousemove = null;
    }
}
