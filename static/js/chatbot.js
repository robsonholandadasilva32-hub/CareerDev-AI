document.addEventListener("DOMContentLoaded", () => {
  const msgBox = document.getElementById("chatbot-message");
  const input = document.getElementById("chatbot-input");

  const btnHelp = document.getElementById("btn-help");
  const btnRepeat = document.getElementById("btn-repeat");
  const btnSend = document.getElementById("btn-send");
  const btnVoice = document.getElementById("btn-voice");

  if (!msgBox || !input) return;

  let lastMessage = msgBox.textContent || "";

  /* =====================================================
     🔊 TEXT TO SPEECH (TTS)
  ===================================================== */
  function speak(text) {
    if (!("speechSynthesis" in window)) return;

    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = document.documentElement.lang || "pt-BR";

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  }

  /* =====================================================
     💬 SET MESSAGE (centralizado)
  ===================================================== */
  function setMessage(text, speakIt = true) {
    msgBox.textContent = text;
    lastMessage = text;

    // Acessibilidade para leitores de tela
    msgBox.setAttribute("aria-live", "polite");

    if (speakIt) speak(text);
  }

  /* =====================================================
     🧠 RESPOSTAS CONTEXTUAIS BÁSICAS
     (base para IA futura)
  ===================================================== */
  function getContextualResponse(userText) {
    const lang = document.documentElement.lang;

    const lower = userText.toLowerCase();

    if (lower.includes("login") || lower.includes("entrar")) {
      return lang === "en"
        ? "To sign in, enter your email and password. If your email is not confirmed, you must confirm it first."
        : lang === "es"
        ? "Para iniciar sesión, introduce tu correo y contraseña. Si tu correo no está confirmado, primero debes confirmarlo."
        : "Para entrar, informe seu e-mail e senha. Se o e-mail não estiver confirmado, é necessário confirmá-lo primeiro.";
    }

    if (lower.includes("cadastro") || lower.includes("register")) {
      return lang === "en"
        ? "Create an account by filling in your name, email and password. A confirmation code will be sent."
        : lang === "es"
        ? "Crea una cuenta ingresando tu nombre, correo y contraseña. Se enviará un código de confirmación."
        : "Crie sua conta informando nome, e-mail e senha. Um código de confirmação será enviado.";
    }

    if (lower.includes("ajuda") || lower.includes("help")) {
      return lang === "en"
        ? "I can help you with login, registration, accessibility and navigation."
        : lang === "es"
        ? "Puedo ayudarte con inicio de sesión, registro, accesibilidad y navegación."
        : "Posso ajudar com login, cadastro, acessibilidade e navegação.";
    }

    return lang === "en"
      ? "I understood your message. Soon I will be able to assist you in a more intelligent way."
      : lang === "es"
      ? "Entendí tu mensaje. Pronto podré ayudarte de forma más inteligente."
      : "Entendi sua mensagem. Em breve poderei ajudar de forma mais inteligente.";
  }

  /* =====================================================
     📤 SEND (TEXTO)
  ===================================================== */
  if (btnSend) {
    btnSend.onclick = () => {
      const text = input.value.trim();
      if (!text) return;

      const response = getContextualResponse(text);
      setMessage(response);

      input.value = "";
    };
  }

  /* =====================================================
     ❓ HELP
  ===================================================== */
  if (btnHelp) {
    btnHelp.onclick = () => {
      const lang = document.documentElement.lang;

      setMessage(
        lang === "en"
          ? "Hello! I'm your CareerDev AI assistant. I can guide you through login, security and accessibility."
          : lang === "es"
          ? "¡Hola! Soy tu asistente CareerDev AI. Puedo guiarte en inicio de sesión, seguridad y accesibilidad."
          : "Olá! Sou o assistente do CareerDev AI. Posso orientar sobre login, segurança e acessibilidade."
      );
    };
  }

  /* =====================================================
     🔁 REPEAT
  ===================================================== */
  if (btnRepeat) {
    btnRepeat.onclick = () => {
      if (lastMessage) speak(lastMessage);
    };
  }

  /* =====================================================
     🎤 VOICE (STT)
  ===================================================== */
  if ("webkitSpeechRecognition" in window && btnVoice) {
    const rec = new webkitSpeechRecognition();
    rec.lang = document.documentElement.lang || "pt-BR";
    rec.continuous = false;

    btnVoice.onclick = () => {
      setMessage(
        document.documentElement.lang === "en"
          ? "Listening..."
          : document.documentElement.lang === "es"
          ? "Escuchando..."
          : "Ouvindo...",
        false
      );
      rec.start();
    };

    rec.onresult = (e) => {
      const spokenText = e.results[0][0].transcript;
      input.value = spokenText;
      btnSend.click();
    };
  } else if (btnVoice) {
    btnVoice.disabled = true;
  }
});

