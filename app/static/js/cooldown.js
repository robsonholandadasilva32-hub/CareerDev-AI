document.addEventListener('DOMContentLoaded', function() {
  const resendBtn = document.getElementById('resend-btn');
  if (resendBtn) {
    const cooldownTime = 30; // seconds
    let timeLeft = cooldownTime;
    const originalText = resendBtn.innerText;
    const storageKey = 'resend_cooldown_' + window.location.pathname;

    function startTimer(initialTime) {
      timeLeft = initialTime;
      resendBtn.disabled = true;
      resendBtn.style.opacity = '0.5';
      resendBtn.style.cursor = 'not-allowed';
      resendBtn.innerText = originalText + ' (' + timeLeft + 's)';

      const timer = setInterval(function() {
        timeLeft--;
        resendBtn.innerText = originalText + ' (' + timeLeft + 's)';

        // Save state
        const now = Date.now();
        const expiry = now + (timeLeft * 1000);
        sessionStorage.setItem(storageKey, expiry);

        if (timeLeft <= 0) {
          clearInterval(timer);
          sessionStorage.removeItem(storageKey);
          resendBtn.disabled = false;
          resendBtn.innerText = originalText;
          resendBtn.style.opacity = '1';
          resendBtn.style.cursor = 'pointer';
        }
      }, 1000);
    }

    // Check for existing cooldown
    const storedExpiry = sessionStorage.getItem(storageKey);
    if (storedExpiry) {
      const now = Date.now();
      const remaining = Math.ceil((parseInt(storedExpiry) - now) / 1000);

      if (remaining > 0) {
        startTimer(remaining);
      } else {
        sessionStorage.removeItem(storageKey);
        // Ensure button starts disabled if simply loading page fresh implies cooldown?
        // Requirement says "Ao carregar a página ... desabilite".
        // This implies a mandatory cooldown on load for these specific pages.
        startTimer(cooldownTime);
      }
    } else {
        // Start fresh timer on page load as requested
        startTimer(cooldownTime);
    }

    // Add click listener just in case (though form submission reloads page usually)
    resendBtn.addEventListener('click', function() {
       // The form submission will reload the page, restarting the logic.
       // If it's an AJAX button, we'd need this.
       // For safety, we can restart timer here too if it wasn't disabled.
    });
  }
});
