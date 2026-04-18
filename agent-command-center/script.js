const input = document.getElementById('promptInput');
const btn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const log = document.getElementById('outputLog');
const voiceOverlay = document.getElementById('voiceOverlay');

// --- VOICE RECOGNITION (Continuous Mode) ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let isContinuousListening = false;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = true; // Stay active
    recognition.lang = 'en-US';
    recognition.interimResults = false;

    recognition.onstart = () => {
        micBtn.classList.add('active');
        voiceOverlay.classList.add('active');
        input.placeholder = "Jarvis is listening for everything...";
        addLog("Voice Mode: Continuous Listening Enabled", "system");
    };

    recognition.onend = () => {
        // If we want it to REALLY always listen, we restart it if it stops
        if (isContinuousListening) {
            recognition.start();
        } else {
            micBtn.classList.remove('active');
            voiceOverlay.classList.remove('active');
            input.placeholder = "Speak or type a command...";
        }
    };

    recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript;
        if (transcript.trim()) {
            input.value = transcript;
            executeTask();
        }
    };
}

// --- VOICE SYNTHESIS (Speaking) ---
function speak(text) {
    // Stop any current speaking before starting new one
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();
    utterance.voice = voices.find(v => v.lang === 'en-US') || voices[0];
    utterance.pitch = 1;
    utterance.rate = 1.1;
    window.speechSynthesis.speak(utterance);
}

// --- LOGGING ---
function addLog(text, type = 'system') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = text;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    return entry;
}

// Typing effect
async function typeLog(text, type = 'system') {
    const entry = addLog('', type);
    const prefix = "AI: ";
    entry.textContent = prefix;
    
    speak(text);

    for (let i = 0; i < text.length; i++) {
        entry.textContent += text.charAt(i);
        log.scrollTop = log.scrollHeight;
        await new Promise(resolve => setTimeout(resolve, 20));
    }
}

// --- EXECUTION ---
async function executeTask() {
    const prompt = input.value.trim();
    if (!prompt) return;

    addLog(`> ${prompt}`, 'user');
    input.value = '';
    btn.disabled = true;

    try {
        const response = await fetch('http://localhost:8000/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        const data = await response.json();

        if (data.message) {
            await typeLog(data.message, 'system');
        }

        if (data.results && data.results.length > 0) {
            data.results.forEach(res => {
                addLog(`Executing: ${res.command}`, 'command');
                if (res.stdout && res.stdout.trim() !== "Done.") {
                    addLog(res.stdout, 'success');
                }
                if (res.stderr) addLog(res.stderr, 'error');
            });
        }
    } catch (err) {
        addLog(`Error: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
    }
}

// Event Listeners
btn.addEventListener('click', executeTask);
input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') executeTask();
});

if (recognition) {
    micBtn.addEventListener('click', () => {
        if (!isContinuousListening) {
            isContinuousListening = true;
            recognition.start();
        } else {
            isContinuousListening = false;
            recognition.stop();
        }
    });
} else {
    micBtn.style.display = 'none';
    addLog("Speech recognition not supported.", "error");
}
