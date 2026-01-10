async function sendMessage() {
  const input = document.getElementById("chat-input");
  const box = document.getElementById("chat-box");

  const userMessage = input.value;
  if (!userMessage) return;

  box.innerHTML += `<p><strong>Você:</strong> ${userMessage}</p>`;
  input.value = "";

  const response = await fetch("/chatbot/message", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: userMessage})
  });

  const data = await response.json();
  box.innerHTML += `<p><strong>AI:</strong> ${data.response}</p>`;
}

function speak(text) {
  if (!window.speechSynthesis) return;

  // 🔴 IMPORTANTE: limpa qualquer fala anterior
  window.speechSynthesis.cancel();

  const lang = document.documentElement.lang || "pt";

  const msg = new SpeechSynthesisUtterance(text);

  msg.lang =
    lang === "en" ? "en-US" :
    lang === "es" ? "es-ES" :
    "pt-BR";

  window.speechSynthesis.speak(msg);
}


function listenCommand(callback) {
  if (!window.SpeechRecognition && !window.webkitSpeechRecognition) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = document.documentElement.lang;

  recognition.onresult = function(event) {
    callback(event.results[0][0].transcript);
  };

  recognition.start();
}

function repeatMessage() {
  speak("Digite o código de seis dígitos enviado para você. Ele expira em poucos minutos.");
}


