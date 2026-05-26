// ================================================
// RC Car Web Interface - Frontend JavaScript
// ================================================

// === Visible Debug Panel (for development & testing) ===
function createDebugPanel() {
    let debug = document.getElementById('debug-panel');
    if (!debug) {
        debug = document.createElement('div');
        debug.id = 'debug-panel';
        debug.style.cssText = 'position:fixed; top:10px; left:10px; background:rgba(0,0,0,0.8); color:#0f0; padding:8px 12px; font-size:14px; border-radius:6px; z-index:9999; font-family:monospace;';
        document.body.appendChild(debug);
    }
    return debug;
}
const debugPanel = createDebugPanel();

/**
 * Updates the on-screen debug panel with current control states
 */
function updateDebug(steering, thrust) {
    debugPanel.innerHTML = `
        Steering: <b>${steering || '—'}</b><br>
        Thrust: <b>${thrust ? 'ACTIVE' : '—'}</b><br>
    `;
}

// === Status Indicator ===
function setStatus(text) {
    document.getElementById('status').textContent = text;
}
setStatus('Connected ✅');

// === Sensor Data Polling ===
function updateSensor() {
    fetch('/sensor_data')
        .then(response => response.json())
        .then(data => {
            console.log("📡 Received sensor data:", data);   // ← Check this in console

            // Front sensor
            if (data.front !== undefined && data.front !== null) {
                const frontEl = document.getElementById('front-distance');
                const val = Math.round(data.front);
                frontEl.textContent = `${val} cm`;
                frontEl.style.color = val < 30 ? '#ff4444' : val < 60 ? '#ffaa00' : '#00ff88';
            }

            // Left sensor
            if (data.left !== undefined && data.left !== null) {
                const leftEl = document.getElementById('left-distance');
                const val = Math.round(data.left);
                leftEl.textContent = `${val} cm`;
                leftEl.style.color = val < 30 ? '#ff4444' : val < 60 ? '#ffaa00' : '#00ff88';
            }

            // Right sensor
            if (data.right !== undefined && data.right !== null) {
                const rightEl = document.getElementById('right-distance');
                const val = Math.round(data.right);
                rightEl.textContent = `${val} cm`;
                rightEl.style.color = val < 30 ? '#ff4444' : val < 60 ? '#ffaa00' : '#00ff88';
            } else {
                console.log("⚠️ Right sensor is null or missing");
            }
        })
        .catch(err => {
            console.error("❌ Failed to fetch sensor data:", err);
        });
}
setInterval(updateSensor, 300);
updateSensor();   // Initial call

// === Camera Streaming (Dynamic URL) ===
function initCamera() {
    const cam = document.getElementById('camera-feed');
    if (cam) {
        const host = window.location.hostname;
        cam.src = `http://${host}:8080/stream?topic=/camera_node/image_raw&type=ros_compressed`;
        console.log(host)
        console.log("Camera stream set to: " + cam.src)
    }
}
initCamera();

// === Command sender ===
function sendCommand(type, value) {
    console.log(`[JS] Sending → ${type}: ${value}`);

    fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, value })
    });
}

// === Multi-Touch Control Logic ===
let activeSteering = null;
let steerInterval = null;
let thrustActive = false;

/**
 * Handles pointer down (mouse or touch start)
 */
const handleDown = (e) => {
    e.preventDefault();
    const btn = e.currentTarget;
    if (btn.classList.contains('dir-btn')) {
        const dir = btn.dataset.dir;
        if (activeSteering === dir) return;
        activeSteering = dir;
        btn.classList.add('active');
        sendCommand('direction', dir);

        // Repeat command while button is held
        steerInterval = setInterval(() => sendCommand('direction', dir), 80);
    } else if (btn.classList.contains('thrust-btn')) {
        thrustActive = true;
        btn.classList.add('active');
        sendCommand('throttle', 'forward');
    }
    updateDebug(activeSteering, thrustActive);
};

/**
 * Handles pointer up / cancel (mouse or touch end)
 */
const handleUp = (e) => {
    e.preventDefault();
    const btn = e.currentTarget;
    if (btn.classList.contains('dir-btn')) {
        if (activeSteering) {
            clearInterval(steerInterval);
            sendCommand('direction', 'stop');
            btn.classList.remove('active');
            activeSteering = null;
        }
    } else if (btn.classList.contains('thrust-btn')) {
        thrustActive = false;
        btn.classList.remove('active');
        sendCommand('throttle', 'stop');
    }
    updateDebug(activeSteering, thrustActive);
};

// Attach to buttons
document.querySelectorAll('.dir-btn, .thrust-btn').forEach(btn => {
    btn.addEventListener('pointerdown', handleDown, { passive: false });
    btn.addEventListener('pointerup', handleUp, { passive: false });
    btn.addEventListener('pointerleave', handleUp, { passive: false });
    btn.addEventListener('pointercancel', handleUp, { passive: false });
});