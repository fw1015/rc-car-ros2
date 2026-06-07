// ==========================================================
// RC Robot Vehicle Teleoperation & Dashboard Interface Module
// ==========================================================

/**
 * Initializes the system connectivity feedback banner.
 * @param {string} text - The status message to display.
 */
function setStatus(text) {
    document.getElementById('status').textContent = text;
}
setStatus('Connected ✅');

/**
 * Dynamically updates the SVG proximity radar and full-screen warning overlays.
 * Applies color-coded safety constraints based on sensor distance.
 * * @param {number} distance - Distance in centimeters.
 * @param {string} coneId - DOM ID of the SVG cone element.
 * @param {string} warningId - DOM ID of the screen edge warning overlay.
 * @returns {Object} State object containing the `isDanger` boolean.
 */
function updateRadarUI(distance, coneId, warningId) {
    const cone = document.getElementById(coneId);
    const warning = document.getElementById(warningId);
    
    // Safety check if DOM nodes are missing
    if (!cone) console.error(`Missing SVG element: ${coneId}`);
    if (!warning) console.error(`Missing warning overlay: ${warningId}`);

    if (distance === null || distance === undefined) return { isDanger: false };

    // Clamp calculations to standard limits (0cm up to max 100cm filter)
    const d = Math.max(0, Math.min(100, distance));
    let color = 'rgba(0, 255, 136, 0.3)'; // Default Safety Green
    let overlayOpacity = 0;
    let isDanger = false;

    if (d <= 30) {
        // Critical Danger: Force Red Cone + Linear Screen Border Glare Fade
        color = 'rgba(255, 68, 68, 0.8)'; 
        overlayOpacity = 0.8 * (1.0 - (d / 30.0)); 
        isDanger = true;
    } else if (d <= 60) {
        // Moderate Warning Area: Shift graphic color state to Yellow
        color = 'rgba(255, 170, 0, 0.6)'; 
    }

    // Apply immediate visual rendering updates to view elements
    if (cone) cone.setAttribute('fill', color);
    if (warning) warning.style.opacity = overlayOpacity;

    return { isDanger };
}

/**
 * Asynchronous Telemetry Poller.
 * Fetches real-time sensor data from the Flask backend and updates the UI.
 */
function updateSensor() {
    fetch('/sensor_data')
        .then(response => response.json())
        .then(data => {
            // Live Debug console reporting trace map for performance monitoring
            console.log(`[Telemetry] F:${data.front} L:${data.left} R:${data.right} | T:${data.throttle} S:${data.steering}`);

            // 1. Refresh Graphical Core Vector Map
            const front = updateRadarUI(data.front, 'cone-front', 'warning-top');
            const left = updateRadarUI(data.left, 'cone-left', 'warning-left');
            const right = updateRadarUI(data.right, 'cone-right', 'warning-right');

            // 2. Populate Numeric Readouts inside the Left Diagnostic panel
            document.getElementById('db-front').textContent = (data.front !== null && data.front !== undefined) ? `${Math.round(data.front)} cm` : '---';
            document.getElementById('db-left').textContent  = (data.left  !== null && data.left  !== undefined) ? `${Math.round(data.left)} cm` : '---';
            document.getElementById('db-right').textContent = (data.right !== null && data.right !== undefined) ? `${Math.round(data.right)} cm` : '---';
            
            document.getElementById('db-throttle').textContent = (data.throttle !== null && data.throttle !== undefined) ? data.throttle.toFixed(2) : '0.00';
            document.getElementById('db-servo').textContent    = (data.steering !== null && data.steering !== undefined) ? data.steering.toFixed(2) : '0.00';

            // 3. Cycle Text Banner state directly beneath vectors
            const readout = document.getElementById('radar-readout');
            if (front.isDanger || left.isDanger || right.isDanger) {
                readout.textContent = "PROXIMITY WARNING";
                readout.style.color = "#ff4444";
            } else {
                readout.textContent = "ALL CLEAR";
                readout.style.color = "#00ff88";
            }
        })
        .catch(err => console.error("❌ Failed to process incoming telemetry data stream:", err));
}
// 150ms execution window generates high refresh speeds for safety alerts
setInterval(updateSensor, 150);
updateSensor(); // Instant baseline loop invocation

/**
 * Initializes the live MJPEG camera stream.
 * Dynamically resolves the host IP to prevent CORS and hardcoding issues.
 */
function initCamera() {
    const cam = document.getElementById('camera-feed');
    if (cam) {
        const host = window.location.hostname;
        cam.src = `http://${host}:8080/stream?topic=/camera_node/image_raw&type=ros_compressed`;
        console.log(`Camera stream set dynamically to host: ${host}`);
    }
}
initCamera();

/**
 * Synchronous Command Transmission Handler.
 * Dispatches JSON hardware commands to the Flask web server.
 * * @param {string} type - The command type ('direction' or 'throttle').
 * @param {string} value - The requested state ('left', 'right', 'forward', 'reverse', 'stop').
 */
function sendCommand(type, value) {
    fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, value })
    });
}

// === Asynchronous Multi-Touch State Engine ===
let activeSteering = null;
let steerInterval = null;

const handleDown = (e) => {
    e.preventDefault();
    const btn = e.currentTarget;
    if (btn.classList.contains('dir-btn')) {
        const dir = btn.dataset.dir;
        if (activeSteering === dir) return;
        activeSteering = dir;
        sendCommand('direction', dir);
        
        // Loop execution while pointer maintains active state prevents command drops
        clearInterval(steerInterval);
        steerInterval = setInterval(() => sendCommand('direction', dir), 80);
    } else if (btn.classList.contains('thrust-btn')) {
        const action = btn.dataset.thrust;
        sendCommand('throttle', action);
    }
};

const handleUp = (e) => {
    e.preventDefault();
    const btn = e.currentTarget;
    if (btn.classList.contains('dir-btn')) {
        if (activeSteering) {
            clearInterval(steerInterval);
            sendCommand('direction', 'stop');
            activeSteering = null;
        }
    } else if (btn.classList.contains('thrust-btn')) {
        // Releasing a drive button naturally cuts power and triggers neutral brake state
        sendCommand('throttle', 'stop'); 
    }
};

// Wire engine touch/pointer maps cleanly to HTML interface elements
document.querySelectorAll('.dir-btn, .thrust-btn').forEach(btn => {
    btn.addEventListener('pointerdown', handleDown, { passive: false });
    btn.addEventListener('pointerup', handleUp, { passive: false });
    btn.addEventListener('pointerleave', handleUp, { passive: false });
    btn.addEventListener('pointercancel', handleUp, { passive: false });
});