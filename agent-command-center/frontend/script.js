// ============================================================
//  GOLDEN ORB — canvas-based 3D energy sphere
// ============================================================
class GoldenOrb {
    constructor(canvas) {
        this.cv  = canvas;
        this.ctx = canvas.getContext('2d');
        this.W   = canvas.width;
        this.H   = canvas.height;
        this.cx  = this.W / 2;
        this.cy  = this.H / 2;
        this.R   = Math.min(this.W, this.H) * 0.3;  // scales with canvas size

        this.rotY = 0;
        this.rotX = 0.38;        // slight forward tilt, like the reference image

        this.intensity    = 0;   // target 0..1
        this.curIntensity = 0;   // smoothed
        this.wordPulse    = 0;   // spikes on each spoken word, decays fast
        this.frame        = 0;

        this.particles = [];

        // 5 rings at different 3-D orientations
        this.rings = [
            { ax: 0,                  ay: 0                },   // equatorial
            { ax: Math.PI / 2,        ay: 0                },   // polar vertical
            { ax: Math.PI / 2,        ay: Math.PI / 2      },   // polar horizontal
            { ax:  Math.PI / 3,       ay: Math.PI / 5      },   // tilted A
            { ax: -Math.PI * 0.28,    ay: Math.PI * 0.65   },   // tilted B
        ];

        this._loop();
    }

    // ---- state ----
    setState(state) {
        const map = { idle: 0, processing: 0.28, listening: 0.55, speaking: 0.9 };
        this.intensity = map[state] ?? 0;
    }

    pulse() {                       // call on each spoken word boundary
        this.wordPulse = 1.0;
    }

    // ---- math ----
    rot(x, y, z) {                  // apply global rotX then rotY
        const cosX = Math.cos(this.rotX), sinX = Math.sin(this.rotX);
        const y1 = y * cosX - z * sinX;
        const z1 = y * sinX + z * cosX;
        const cosY = Math.cos(this.rotY), sinY = Math.sin(this.rotY);
        const x2 =  x  * cosY + z1 * sinY;
        const z2 = -x  * sinY + z1 * cosY;
        return [x2, y1, z2];
    }

    proj(x, y, z) {                 // perspective projection
        const fov = 340;
        const s = fov / (fov + z + this.R);
        return [this.cx + x * s, this.cy + y * s, z];
    }

    ringPts(ax, ay, n = 72) {       // ring points in screen-space
        const pts = [];
        const cosAX = Math.cos(ax), sinAX = Math.sin(ax);
        const cosAY = Math.cos(ay), sinAY = Math.sin(ay);
        for (let i = 0; i <= n; i++) {
            const t = (i / n) * Math.PI * 2;
            let x = this.R * Math.cos(t);
            let y = this.R * Math.sin(t);
            let z = 0;
            // ring-local rotation
            const y2 = y * cosAX - z * sinAX;
            const z2 = y * sinAX + z * cosAX;
            const x3 = x * cosAY + z2 * sinAY;
            const z3 = -x * sinAY + z2 * cosAY;
            // global rotation
            const [rx, ry, rz] = this.rot(x3, y2, z3);
            const [px, py]     = this.proj(rx, ry, rz);
            pts.push({ x: px, y: py, z: rz });
        }
        return pts;
    }

    // ---- drawing ----
    drawRing(ax, ay) {
        const ctx = this.ctx;
        const pts = this.ringPts(ax, ay);
        const ci  = this.curIntensity;
        const wp  = this.wordPulse;

        for (let i = 0; i < pts.length - 1; i++) {
            const p = pts[i];
            const q = pts[i + 1];
            const depth = (p.z + this.R) / (2 * this.R);   // 0=back 1=front

            const baseAlpha = 0.15 + depth * 0.65;
            const alpha     = baseAlpha * (0.4 + ci * 0.5 + wp * 0.1);
            const green     = Math.floor(80 + depth * 110 + wp * 70);
            const lw        = 0.8 + depth * 0.9 + wp * 0.6;

            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = `rgba(255,${green},8,${alpha})`;
            ctx.lineWidth   = lw;

            if (depth > 0.5 && (ci > 0.2 || wp > 0.15)) {
                ctx.shadowBlur  = 4 + wp * 14 + ci * 6;
                ctx.shadowColor = `rgba(255,140,0,${depth * (ci * 0.6 + wp * 0.4)})`;
            } else {
                ctx.shadowBlur = 0;
            }
            ctx.stroke();
        }
        ctx.shadowBlur = 0;
    }

    drawSpokes() {
        const ctx = this.ctx;
        const ci  = this.curIntensity;
        const wp  = this.wordPulse;
        const N   = 6;

        for (let i = 0; i < N; i++) {
            const angle = (i / N) * Math.PI * 2;
            // spokes follow equatorial plane
            const sx = this.R * Math.cos(angle);
            const sy = this.R * Math.sin(angle) * Math.cos(this.rotX);
            const sz = this.R * Math.sin(angle) * Math.sin(this.rotX) * 0.45;

            const [rx, ry, rz] = this.rot(sx, sy, sz);
            const [ex, ey]     = this.proj(rx, ry, rz);
            const depth = (rz + this.R) / (2 * this.R);

            const alpha = (0.15 + depth * 0.5) * (0.3 + ci * 0.5 + wp * 0.2);

            const gr = ctx.createLinearGradient(this.cx, this.cy, ex, ey);
            gr.addColorStop(0, `rgba(255,210,60,${alpha})`);
            gr.addColorStop(1, `rgba(255,90,0,${alpha * 0.3})`);

            ctx.beginPath();
            ctx.moveTo(this.cx, this.cy);
            ctx.lineTo(ex, ey);
            ctx.strokeStyle = gr;
            ctx.lineWidth   = 0.7 + ci * 0.5 + wp * 0.6;

            if (ci > 0.25 || wp > 0.2) {
                ctx.shadowBlur  = 3 + wp * 10;
                ctx.shadowColor = 'rgba(255,150,0,0.5)';
            }
            ctx.stroke();
        }
        ctx.shadowBlur = 0;
    }

    drawCore() {
        const ctx = this.ctx;
        const ci  = this.curIntensity;
        const wp  = this.wordPulse;
        const r   = 9 + ci * 5 + wp * 11;

        // ambient halo
        const ag = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, r * 7);
        ag.addColorStop(0, `rgba(255,170,20,${0.12 + ci * 0.18 + wp * 0.14})`);
        ag.addColorStop(1, 'rgba(255,70,0,0)');
        ctx.fillStyle = ag;
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, r * 7, 0, Math.PI * 2);
        ctx.fill();

        // glow ring
        ctx.shadowBlur  = 18 + ci * 28 + wp * 35;
        ctx.shadowColor = `rgba(255,160,0,${0.75 + ci * 0.2 + wp * 0.05})`;

        // core sphere gradient
        const cg = ctx.createRadialGradient(
            this.cx - r * 0.32, this.cy - r * 0.36, 0,
            this.cx, this.cy, r
        );
        cg.addColorStop(0,   '#ffffff');
        cg.addColorStop(0.22, '#fff0a0');
        cg.addColorStop(0.55, '#ff9900');
        cg.addColorStop(1,   `rgba(180,40,0,${0.6 + ci * 0.4})`);

        ctx.fillStyle = cg;
        ctx.beginPath();
        ctx.arc(this.cx, this.cy, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;

        // specular highlight
        ctx.fillStyle = `rgba(255,255,230,${0.55 + wp * 0.25})`;
        ctx.beginPath();
        ctx.arc(this.cx - r * 0.30, this.cy - r * 0.34, r * 0.22, 0, Math.PI * 2);
        ctx.fill();
    }

    spawnParticle() {
        const ring = this.rings[Math.floor(Math.random() * this.rings.length)];
        const t = Math.random() * Math.PI * 2;
        const cosAX = Math.cos(ring.ax), sinAX = Math.sin(ring.ax);
        const cosAY = Math.cos(ring.ay), sinAY = Math.sin(ring.ay);

        let x = this.R * Math.cos(t);
        let y = this.R * Math.sin(t);
        let z = 0;
        const y2 = y * cosAX - z * sinAX;
        const z2 = y * sinAX + z * cosAX;
        const x3 = x * cosAY + z2 * sinAY;
        const z3 = -x * sinAY + z2 * cosAY;

        const speed = 0.3 + Math.random() * 0.9;
        this.particles.push({
            x: x3, y: y2, z: z3,
            vx: (Math.random() - 0.5) * speed,
            vy: (Math.random() - 0.5) * speed,
            vz: (Math.random() - 0.5) * speed * 0.4,
            life: 1,
            size: 1 + Math.random() * 2,
        });
    }

    drawParticles() {
        const ctx = this.ctx;
        const ci  = this.curIntensity;
        const wp  = this.wordPulse;

        this.frame++;
        const rate = ci > 0.7 ? 1 : ci > 0.4 ? 3 : ci > 0.1 ? 8 : 20;
        if (this.frame % rate === 0) {
            const n = wp > 0.5 ? 5 : ci > 0.5 ? 2 : 1;
            for (let i = 0; i < n; i++) this.spawnParticle();
        }

        this.particles = this.particles.filter(p => {
            p.life -= 0.022 + ci * 0.008;
            if (p.life <= 0) return false;

            p.x += p.vx; p.y += p.vy; p.z += p.vz;

            const [rx, ry, rz] = this.rot(p.x, p.y, p.z);
            const [sx, sy]     = this.proj(rx, ry, rz);
            const depth = (rz + this.R) / (2 * this.R);
            const alpha = p.life * (0.4 + depth * 0.6);
            const g     = Math.floor(90 + Math.random() * 130);

            ctx.shadowBlur  = 5;
            ctx.shadowColor = `rgba(255,130,0,${alpha * 0.8})`;
            ctx.fillStyle   = `rgba(255,${g},15,${alpha})`;
            ctx.beginPath();
            ctx.arc(sx, sy, p.size, 0, Math.PI * 2);
            ctx.fill();
            return true;
        });
        ctx.shadowBlur = 0;
    }

    _loop() {
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.W, this.H);

        // smooth intensity / decay pulse
        this.curIntensity += (this.intensity - this.curIntensity) * 0.045;
        this.wordPulse    *= 0.87;

        // rotation speed scales with activity
        this.rotY += 0.0035 + this.curIntensity * 0.012 + this.wordPulse * 0.006;

        // draw back→front: rings → spokes → particles → core
        this.rings.forEach(r => this.drawRing(r.ax, r.ay));
        this.drawSpokes();
        this.drawParticles();
        this.drawCore();

        requestAnimationFrame(() => this._loop());
    }
}

// ============================================================
//  APP WIRING
// ============================================================
const input        = document.getElementById('promptInput');
const sendBtn      = document.getElementById('sendBtn');
const micBtn       = document.getElementById('micBtn');
const micLabel     = document.getElementById('micLabel');
const log          = document.getElementById('outputLog');
const clearBtn     = document.getElementById('clearBtn');
const orbLabelEl   = document.getElementById('orbLabel');
const ollamaStatus = document.getElementById('ollamaStatus');

const orb = new GoldenOrb(document.getElementById('orbCanvas'));

let isContinuousListening = false;
let currentController     = null;
let commandHistory        = [];
let historyIndex          = -1;
let conversationHistory   = [];   // runtime cache; backed by DB + localStorage

// ---- MEMORY PERSISTENCE ----
function saveHistoryLocal() {
    try {
        const trimmed = conversationHistory.slice(-50);
        localStorage.setItem('jarvis_history', JSON.stringify(trimmed));
    } catch {}
}

async function loadHistory() {
    try {
        const res  = await fetch('/history', { signal: AbortSignal.timeout(3000) });
        const data = await res.json();
        if (data.history?.length) {
            conversationHistory = data.history;
            addLog(`Memory restored — ${data.history.length} previous exchange${data.history.length > 1 ? 's' : ''} loaded.`, 'system');
            return;
        }
    } catch {}
    // fallback: localStorage
    try {
        const saved = localStorage.getItem('jarvis_history');
        if (saved) {
            conversationHistory = JSON.parse(saved);
            if (conversationHistory.length)
                addLog(`Local memory restored — ${conversationHistory.length} exchange${conversationHistory.length > 1 ? 's' : ''}.`, 'system');
        }
    } catch {}
}

// ---- ORB LABEL ----
function setOrbLabel(state, text) {
    orbLabelEl.className = `orb-label ${state}`;
    orbLabelEl.textContent = text;
    orb.setState(state);
}

// ---- HEALTH CHECK ----
async function checkHealth() {
    try {
        const res  = await fetch('/health', { signal: AbortSignal.timeout(4000) });
        const data = await res.json();
        if (data.ollama) {
            setStatus('online', data.models[0] || 'ready');
        } else {
            setStatus('offline', 'Ollama offline');
        }
    } catch {
        setStatus('offline', 'Server offline');
    }
}
function setStatus(state, label) {
    ollamaStatus.className = `ollama-status ${state}`;
    ollamaStatus.querySelector('.label').textContent = label;
}

// ---- VOICE RECOGNITION ----
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let recognitionRunning  = false;   // true only between onstart and onend
let recognitionPaused   = false;   // paused during TTS to avoid feedback loop
let restartTimer        = null;
let watchdogTimer       = null;

function startWatchdog() {
    clearTimeout(watchdogTimer);
    watchdogTimer = setTimeout(() => {
        // If mic should be on but recognition died silently, revive it
        if (isContinuousListening && !recognitionRunning && !recognitionPaused) {
            scheduleRestart(200);
        }
    }, 8000);
}

function scheduleRestart(delay = 200) {
    clearTimeout(restartTimer);
    restartTimer = setTimeout(() => {
        if (!isContinuousListening || recognitionPaused || recognitionRunning) return;
        try {
            recognition.start();
        } catch (e) {
            // InvalidStateError = already running; anything else retry later
            if (!e.message.includes('already started')) scheduleRestart(600);
        }
    }, delay);
}

function pauseRecognition() {
    if (!recognitionRunning) return;
    recognitionPaused = true;
    try { recognition.stop(); } catch {}
}

function resumeRecognition() {
    recognitionPaused = false;
    if (isContinuousListening && !recognitionRunning) scheduleRestart(300);
}

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous     = true;
    recognition.lang           = 'en-US';
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        recognitionRunning = true;
        micBtn.classList.add('active');
        micLabel.textContent = 'LISTENING';
        setOrbLabel('listening', 'LISTENING');
        startWatchdog();
    };

    recognition.onend = () => {
        recognitionRunning = false;
        clearTimeout(watchdogTimer);
        if (isContinuousListening && !recognitionPaused) {
            // Small delay required — Chrome needs breathing room before restart
            scheduleRestart(200);
        } else if (!isContinuousListening) {
            micBtn.classList.remove('active');
            micLabel.textContent = 'VOICE OFF';
            setOrbLabel('idle', 'STANDBY');
        }
    };

    recognition.onresult = (event) => {
        startWatchdog(); // got audio — reset dead-man timer
        const latest     = event.results[event.results.length - 1];
        const transcript = latest[0].transcript.trim();
        input.value = transcript;
        if (latest.isFinal && transcript) executeTask();
    };

    recognition.onerror = (e) => {
        recognitionRunning = false;
        if (e.error === 'not-allowed' || e.error === 'audio-capture') {
            // Hard stop — user denied mic or no mic present
            isContinuousListening = false;
            micBtn.classList.remove('active');
            micLabel.textContent = 'VOICE OFF';
            setOrbLabel('idle', 'STANDBY');
            addLog(`Mic error: ${e.error}. Check browser permissions.`, 'error');
        }
        // no-speech / aborted / network → onend will fire and scheduleRestart handles it
    };
} else {
    micBtn.style.display = 'none';
}

// ---- VOICE SYNTHESIS ----
let selectedVoice = null;

const VOICE_PRIORITY = [
    v => v.name.includes('Premium'),
    v => v.name.includes('Enhanced'),
    v => v.name === 'Google US English',
    v => v.name === 'Samantha',
    v => v.lang === 'en-US' && v.localService,
    v => v.lang.startsWith('en-US'),
    v => v.lang.startsWith('en'),
];
function pickVoice() {
    const all = window.speechSynthesis.getVoices();
    if (!all.length) return;
    for (const test of VOICE_PRIORITY) {
        const m = all.find(test);
        if (m) { selectedVoice = m; return; }
    }
    selectedVoice = all[0];
}
window.speechSynthesis.addEventListener('voiceschanged', () => { if (!selectedVoice) pickVoice(); });
pickVoice();

function cleanForSpeech(t) {
    return t
        .replace(/\*\*(.*?)\*\*/g, '$1')
        .replace(/\*(.*?)\*/g, '$1')
        .replace(/`([^`]+)`/g, '$1')
        .replace(/```[\s\S]*?```/g, '')
        .replace(/#+\s/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/https?:\/\/\S+/g, '')
        .trim();
}

function speak(text) {
    if (!text) return;
    if (!selectedVoice) pickVoice();
    window.speechSynthesis.cancel();

    const clean = cleanForSpeech(text);
    if (!clean) return;

    const u = new SpeechSynthesisUtterance(clean);
    u.voice  = selectedVoice;
    u.pitch  = 0.97;
    u.rate   = 0.93;
    u.volume = 1;

    u.onstart    = () => { pauseRecognition(); setOrbLabel('speaking', 'SPEAKING'); };
    u.onboundary = () => orb.pulse();
    u.onend      = () => { setOrbLabel('idle', 'STANDBY'); resumeRecognition(); };
    u.onerror    = () => { setOrbLabel('idle', 'STANDBY'); resumeRecognition(); };

    window.speechSynthesis.speak(u);
}

// ---- LOGGING ----
function ts() {
    return new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
function addLog(text, type = 'system') {
    const entry   = document.createElement('div');
    entry.className = `log-entry ${type}`;
    const tsEl    = document.createElement('span');
    tsEl.className  = 'ts';
    tsEl.textContent = ts();
    const content = document.createElement('span');
    content.className = 'content';
    content.textContent = text;
    entry.appendChild(tsEl);
    entry.appendChild(content);
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    return content;
}

async function typeLog(text, type = 'ai') {
    const content = addLog('AI: ', type);
    speak(text);
    for (let i = 0; i < text.length; i++) {
        content.textContent += text[i];
        log.scrollTop = log.scrollHeight;
        await new Promise(r => setTimeout(r, 14));
    }
}

// ---- LOADING ----
function setLoading(on) {
    sendBtn.disabled = on;
    sendBtn.querySelector('.btn-text').style.display = on ? 'none' : '';
    sendBtn.querySelector('.btn-loader').style.display = on ? 'flex' : 'none';
    if (on) setOrbLabel('processing', 'PROCESSING');
}

// ---- EXECUTE ----
async function executeTask() {
    const prompt = input.value.trim();
    if (!prompt || sendBtn.disabled) return;

    if (currentController) currentController.abort();
    currentController = new AbortController();

    if (commandHistory[commandHistory.length - 1] !== prompt) {
        commandHistory.push(prompt);
        if (commandHistory.length > 100) commandHistory.shift();
    }
    historyIndex = -1;

    addLog(`> ${prompt}`, 'user');
    input.value = '';
    setLoading(true);

    try {
        const res = await fetch('/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, history: conversationHistory }),
            signal: currentController.signal,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
            throw new Error(err.detail || `Server error ${res.status}`);
        }

        const data = await res.json();

        if (data.message) {
            await typeLog(data.message, 'ai');
            conversationHistory.push({ user: prompt, assistant: data.message });
            if (conversationHistory.length > 50) conversationHistory.shift();
            saveHistoryLocal();
        }

        if (data.results?.length) {
            for (const r of data.results) {
                addLog(`$ ${r.command}`, 'command');
                if (r.status === 'blocked') {
                    addLog(r.stderr, 'warning');
                } else {
                    if (r.stdout) addLog(r.stdout, 'success');
                    else if (r.status === 'success') addLog('✓ Done', 'success');
                    if (r.stderr) addLog(r.stderr, 'error');
                }
            }
        }

        if (data.action_result) {
            const ar = data.action_result;
            const icon = ar.status === 'sent' || ar.status === 'ok' ? '✓' : '✗';
            const type = ar.status === 'failed' ? 'error' : 'success';
            addLog(`${icon} ${ar.label}: ${ar.detail}`, type);
        }

    } catch (err) {
        if (err.name === 'AbortError') return;
        addLog(`Error: ${err.message}`, 'error');
        setOrbLabel('idle', 'STANDBY');
    } finally {
        setLoading(false);
        currentController = null;
    }
}

// ---- CLEAR ----
function clearLog() {
    log.innerHTML = '';
    conversationHistory = [];
    localStorage.removeItem('jarvis_history');
    fetch('/history', { method: 'DELETE' }).catch(() => {});
    addLog('Memory cleared. Fresh start.', 'system');
}

// ---- EVENTS ----
sendBtn.addEventListener('click', executeTask);

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); executeTask();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (historyIndex < commandHistory.length - 1) {
            historyIndex++;
            input.value = commandHistory[commandHistory.length - 1 - historyIndex];
        }
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (historyIndex > 0) {
            historyIndex--;
            input.value = commandHistory[commandHistory.length - 1 - historyIndex];
        } else { historyIndex = -1; input.value = ''; }
    }
});

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'l') { e.preventDefault(); clearLog(); }
    if (e.ctrlKey && e.key === 'c' && currentController) {
        currentController.abort();
        setLoading(false);
        setOrbLabel('idle', 'STANDBY');
        addLog('Request cancelled.', 'warning');
    }
});

clearBtn.addEventListener('click', clearLog);

if (recognition) {
    micBtn.addEventListener('click', () => {
        if (!isContinuousListening) {
            isContinuousListening = true;
            recognitionPaused = false;
            scheduleRestart(0);
        } else {
            isContinuousListening = false;
            clearTimeout(restartTimer);
            clearTimeout(watchdogTimer);
            try { recognition.stop(); } catch {}
        }
    });
}

// ---- INIT ----
checkHealth();
setInterval(checkHealth, 30000);
loadHistory();
