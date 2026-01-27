class SmartLoader {
    constructor() {
        this.messages = [
            "Compiling career strategy...",
            "Refactoring imposter syndrome...",
            "Optimizing success metrics...",
            "Pulling latest commits...",
            "Aligning chakras with market trends...",
            "Decrypting recruiter signals..."
        ];
        this.interval = null;
        this.overlay = null;
        this.textElement = null;
        this.injectStyles();
    }

    injectStyles() {
        if (document.getElementById('smart-loader-styles')) return;
        const style = document.createElement('style');
        style.id = 'smart-loader-styles';
        style.innerHTML = `
            .smart-loader-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(5, 10, 20, 0.95);
                z-index: 99999;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(5px);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .smart-loader-content {
                text-align: center;
            }
            .smart-loader-spinner {
                width: 50px;
                height: 50px;
                border: 3px solid rgba(0, 243, 255, 0.3);
                border-radius: 50%;
                border-top-color: #00f3ff;
                animation: spin 1s ease-in-out infinite;
                margin: 0 auto 20px auto;
                box-shadow: 0 0 15px rgba(0, 243, 255, 0.5);
            }
            .smart-loader-text {
                font-family: 'Courier New', monospace;
                color: #00f3ff;
                font-size: 1.2rem;
                text-shadow: 0 0 10px rgba(0, 243, 255, 0.5);
                min-height: 1.5em;
            }
            @keyframes spin {
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }

    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'smart-loader-overlay';

        const content = document.createElement('div');
        content.className = 'smart-loader-content';

        const spinner = document.createElement('div');
        spinner.className = 'smart-loader-spinner';

        this.textElement = document.createElement('div');
        this.textElement.className = 'smart-loader-text';
        this.textElement.innerText = "Initializing...";

        content.appendChild(spinner);
        content.appendChild(this.textElement);
        this.overlay.appendChild(content);

        document.body.appendChild(this.overlay);

        // Force reflow for transition
        void this.overlay.offsetWidth;
        this.overlay.style.opacity = '1';
    }

    startCycling() {
        let index = 0;
        this.textElement.innerText = this.messages[0];

        this.interval = setInterval(() => {
            index = (index + 1) % this.messages.length;
            this.textElement.innerText = this.messages[index];
        }, 800);
    }

    show() {
        if (this.overlay) return; // Already showing
        this.createOverlay();
        this.startCycling();
    }

    hide() {
        if (!this.overlay) return;

        this.overlay.style.opacity = '0';
        clearInterval(this.interval);

        setTimeout(() => {
            if (this.overlay && this.overlay.parentNode) {
                this.overlay.parentNode.removeChild(this.overlay);
            }
            this.overlay = null;
        }, 300);
    }
}

// Global Instance
window.CareerLoader = new SmartLoader();
