const input = document.getElementById('promptInput');
const btn = document.getElementById('sendBtn');
const log = document.getElementById('outputLog');

function addLog(text, type = 'system') {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = text;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
    return entry;
}

// Typing effect for AI messages
async function typeLog(text, type = 'system') {
    const entry = addLog('', type);
    const prefix = "AI: ";
    entry.textContent = prefix;
    
    for (let i = 0; i < text.length; i++) {
        entry.textContent += text.charAt(i);
        log.scrollTop = log.scrollHeight;
        await new Promise(resolve => setTimeout(resolve, 20)); // Adjust speed here
    }
}

async function executeTask() {
    const prompt = input.value.trim();
    if (!prompt) return;

    addLog(`> ${prompt}`, 'user');
    input.value = '';
    btn.disabled = true;
    btn.textContent = 'Thinking...';

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
        btn.textContent = 'Execute';
    }
}

btn.addEventListener('click', executeTask);
input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') executeTask();
});
