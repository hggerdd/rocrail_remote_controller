// Compact ESP32 Configuration App
const API = '/api';
let scanning = false;

// DOM Elements cache
const $ = id => document.getElementById(id);
const els = {
    deviceInfo: $('device-info'), message: $('message'), currentWifiConfig: $('current-wifi-config'),
    currentRocrailConfig: $('current-rocrail-config'), savedNetworksList: $('saved-networks-list'),
    loading: $('loading'), ssid: $('ssid'), customGroup: $('custom-group'), customSsid: $('custom-ssid'),
    password: $('password'), rocrailIp: $('rocrail-ip'), rocrailPort: $('rocrail-port')
};

// Utility functions
const getTempClass = t => t === null ? 'unavailable' : t < 40 ? 'normal' : t < 60 ? 'warm' : t < 80 ? 'hot' : 'critical';
const isValidIP = ip => /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(ip);
const getSignalText = rssi => rssi >= -50 ? 'Excellent' : rssi >= -60 ? 'Good' : rssi >= -70 ? 'Fair' : 'Poor';

function showMessage(msg, type = 'info') {
    els.message.textContent = msg;
    els.message.className = `message ${type}`;
    els.message.style.display = 'block';
    setTimeout(() => els.message.style.display = 'none', 5000);
}

function showLoading(show = true) {
    els.loading.style.display = show ? 'block' : 'none';
}

function setButtonsEnabled(enabled = true) {
    ['save-wifi-btn', 'test-wifi-btn', 'save-rocrail-btn', 'clear-rocrail-btn', 'refresh-btn', 'forget-wifi-btn', 'restart-btn']
        .forEach(id => $(id).disabled = !enabled);
}

// Consolidated API function
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(API + endpoint, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Load device status
async function loadDeviceStatus() {
    try {
        const data = await apiCall('/status');
        const temp = data.temperature !== null ? 
            `<br><b>Temperature:</b> <span class="temp-${getTempClass(data.temperature)}">${data.temperature}°C</span>` : 
            '<br><b>Temperature:</b> <span class="temp-unavailable">N/A</span>';
        
        els.deviceInfo.innerHTML = `<b>Device:</b> ${data.device}<br><b>Memory:</b> ${data.memory} KB${temp}<br><b>AP:</b> ${data.ap_ssid}${data.failure_count > 0 ? `<br><b>⚠️ Failures:</b> ${data.failure_count}` : ''}`;
        return data;
    } catch (error) {
        els.deviceInfo.innerHTML = '<b>Device:</b> ESP32/ESP8266<br><b>Memory:</b> Loading...<br><b>Temperature:</b> <span class="temp-unavailable">N/A</span><br><b>Status:</b> Error';
        showMessage('Failed to load device status', 'error');
    }
}

// Load WiFi status
async function loadWifiStatus() {
    try {
        const data = await apiCall('/status');
        const status = data.current_ssid || 'Not configured';
        const warning = data.failure_count > 0 ? ` ⚠️ (${data.failure_count} failures)` : '';
        const info = data.saved_networks_count ? ` • ${data.saved_networks_count} saved` : '';
        els.currentWifiConfig.innerHTML = `<b>Current:</b> ${status}${warning}${info}`;
        return data;
    } catch (error) {
        showMessage('Failed to load WiFi status', 'error');
    }
}

// Load saved networks
async function loadSavedNetworks() {
    try {
        const data = await apiCall('/wifi-networks');
        const networks = data.networks || [];
        const countEl = $('network-count');
        if (countEl) countEl.textContent = networks.length;
        
        els.savedNetworksList.innerHTML = networks.length === 0 ? 
            '<div class="empty-networks">No networks saved yet.</div>' :
            networks.map((n, i) => `
                <div class="network-item">
                    <div class="network-info">
                        <div class="network-name">${n.ssid}</div>
                        <div class="network-details">${n.failures > 0 ? `❌ ${n.failures} failures` : '✅ Working'}${i === 0 ? ' • Primary' : ''}</div>
                    </div>
                    <div class="network-actions">
                        <button class="btn btn-warning btn-small" onclick="removeNetwork('${n.ssid}')">🗑️ Remove</button>
                    </div>
                </div>
            `).join('');
        return networks;
    } catch (error) {
        els.savedNetworksList.innerHTML = '<div class="empty-networks">Failed to load networks</div>';
        if ($('network-count')) $('network-count').textContent = '0';
        showMessage('Failed to load saved networks', 'error');
    }
}

// Load Rocrail status
async function loadRocrailStatus() {
    try {
        const data = await apiCall('/rocrail');
        els.currentRocrailConfig.innerHTML = `<b>Current Server:</b> ${data.ip ? `${data.ip}:${data.port}` : 'Not configured'}`;
        els.rocrailIp.value = data.ip || '';
        els.rocrailPort.value = data.port || 8051;
        return data;
    } catch (error) {
        els.currentRocrailConfig.innerHTML = '<b>Current Server:</b> Not configured';
        els.rocrailIp.value = '';
        els.rocrailPort.value = '8051';
        showMessage('Failed to load Rocrail status', 'error');
    }
}

// Load available networks
async function loadNetworks() {
    if (scanning) return;
    scanning = true;
    setButtonsEnabled(false);
    showLoading(true);
    
    try {
        const data = await apiCall('/networks');
        els.ssid.innerHTML = '<option value="">Select network...</option>';
        
        const networks = data.networks_detailed || data.networks || [];
        networks.forEach(network => {
            const option = document.createElement('option');
            if (typeof network === 'object') {
                option.value = network.ssid;
                option.textContent = `${network.ssid} (${getSignalText(network.rssi)} - ${network.rssi} dBm)`;
                if (network.ssid === data.current_ssid) option.selected = true;
            } else {
                option.value = network;
                option.textContent = network;
                if (network === data.current_ssid) option.selected = true;
            }
            els.ssid.appendChild(option);
        });
        
        // Add custom option
        const customOption = document.createElement('option');
        customOption.value = '__custom__';
        customOption.textContent = 'Enter custom SSID';
        els.ssid.appendChild(customOption);
        
        showMessage(`Found ${networks.length} networks`, 'success');
    } catch (error) {
        showMessage('Failed to scan networks', 'error');
        els.ssid.innerHTML = '<option value="">Select network...</option><option value="__custom__">Enter custom SSID</option>';
    } finally {
        scanning = false;
        setButtonsEnabled(true);
        showLoading(false);
    }
}

// Add/test WiFi network
async function addWifiNetwork(test = false) {
    const ssid = els.ssid.value === '__custom__' ? els.customSsid.value : els.ssid.value;
    const password = els.password.value;
    
    if (!ssid.trim()) {
        showMessage('Please enter a network name', 'error');
        return;
    }
    
    setButtonsEnabled(false);
    showMessage(`${test ? 'Testing & adding' : 'Adding'} network...`, 'info');
    
    try {
        const data = await apiCall(test ? '/test' : '/wifi-networks', {
            method: 'POST',
            body: JSON.stringify({ ssid, password })
        });
        
        if (data.success) {
            showMessage(data.message, 'success');
            els.password.value = '';
            if (els.ssid.value === '__custom__') {
                els.customSsid.value = '';
                els.ssid.value = '';
                els.customGroup.style.display = 'none';
            } else {
                els.ssid.value = '';
            }
            setTimeout(() => { loadSavedNetworks(); loadWifiStatus(); }, 500);
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage(`Failed to ${test ? 'test &' : ''} add network`, 'error');
    } finally {
        setButtonsEnabled(true);
    }
}

// Remove network
async function removeNetwork(ssid) {
    if (!confirm(`Remove network "${ssid}"?`)) return;
    
    setButtonsEnabled(false);
    showMessage(`Removing ${ssid}...`, 'info');
    
    try {
        const data = await apiCall(`/wifi-networks/${encodeURIComponent(ssid)}`, { method: 'DELETE' });
        if (data.success) {
            showMessage(data.message, 'success');
            loadSavedNetworks();
            loadWifiStatus();
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Failed to remove network', 'error');
    } finally {
        setButtonsEnabled(true);
    }
}

// Save Rocrail config
async function saveRocrailConfig() {
    const ip = els.rocrailIp.value.trim();
    const port = parseInt(els.rocrailPort.value);
    
    if (ip && !isValidIP(ip)) {
        showMessage('Invalid IP address', 'error');
        return;
    }
    if (isNaN(port) || port < 1 || port > 65535) {
        showMessage('Invalid port number', 'error');
        return;
    }
    
    setButtonsEnabled(false);
    showMessage('Saving Rocrail config...', 'info');
    
    try {
        const data = await apiCall('/rocrail', {
            method: 'POST',
            body: JSON.stringify({ ip, port })
        });
        
        if (data.success) {
            showMessage(data.message, 'success');
            loadRocrailStatus();
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Failed to save Rocrail config', 'error');
    } finally {
        setButtonsEnabled(true);
    }
}

// Clear Rocrail config
async function clearRocrailConfig() {
    if (!confirm('Clear Rocrail configuration?')) return;
    
    setButtonsEnabled(false);
    showMessage('Clearing config...', 'info');
    
    try {
        const data = await apiCall('/rocrail', {
            method: 'POST',
            body: JSON.stringify({ ip: '', port: 8051 })
        });
        
        if (data.success) {
            showMessage(data.message, 'success');
            loadRocrailStatus();
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('Failed to clear config', 'error');
    } finally {
        setButtonsEnabled(true);
    }
}

// Forget all WiFi
async function forgetWiFi() {
    if (!confirm('Forget ALL WiFi networks?')) return;
    
    setButtonsEnabled(false);
    showMessage('Forgetting networks...', 'info');
    
    try {
        const data = await apiCall('/forget', { method: 'POST' });
        if (data.success) {
            showMessage(data.message, 'success');
            loadWifiStatus();
            loadSavedNetworks();
            loadNetworks();
            els.password.value = '';
        } else {
            showMessage(data.message || 'Failed to forget networks', 'error');
        }
    } catch (error) {
        showMessage('Failed to forget networks', 'error');
    } finally {
        setButtonsEnabled(true);
    }
}

// Restart device
async function restartDevice() {
    if (!confirm('Restart device?')) return;
    
    setButtonsEnabled(false);
    showMessage('Restarting...', 'info');
    
    try {
        await apiCall('/restart', { method: 'POST' });
        let countdown = 5;
        const interval = setInterval(() => {
            showMessage(`Restarting... ${countdown}s`, 'info');
            if (--countdown < 0) {
                clearInterval(interval);
                showMessage('Device restarted. You can close this page.', 'success');
            }
        }, 1000);
    } catch (error) {
        showMessage('Restart initiated', 'success');
    }
}

// Event handlers setup
function setupEvents() {
    // SSID selection
    els.ssid.addEventListener('change', () => {
        const isCustom = els.ssid.value === '__custom__';
        els.customGroup.style.display = isCustom ? 'block' : 'none';
        if (isCustom) els.customSsid.focus();
        else if (els.ssid.value) els.password.focus();
    });
    
    // Button events
    $('save-wifi-btn').addEventListener('click', e => { e.preventDefault(); addWifiNetwork(false); });
    $('test-wifi-btn').addEventListener('click', e => { e.preventDefault(); addWifiNetwork(true); });
    $('save-rocrail-btn').addEventListener('click', saveRocrailConfig);
    $('clear-rocrail-btn').addEventListener('click', clearRocrailConfig);
    $('refresh-btn').addEventListener('click', loadNetworks);
    $('forget-wifi-btn').addEventListener('click', forgetWiFi);
    $('restart-btn').addEventListener('click', restartDevice);
    
    // Form submissions
    $('wifi-form').addEventListener('submit', e => { e.preventDefault(); addWifiNetwork(true); });
    $('rocrail-form').addEventListener('submit', e => { e.preventDefault(); saveRocrailConfig(); });
    
    // IP validation
    els.rocrailIp.addEventListener('input', () => {
        const ip = els.rocrailIp.value.trim();
        els.rocrailIp.style.borderColor = ip && !isValidIP(ip) ? '#f44336' : '#e0e0e0';
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            loadNetworks();
        }
    });
}

// Initialize app
async function init() {
    els.deviceInfo.innerHTML = '<b>Device:</b> Loading...<br><b>Status:</b> Initializing...';
    els.savedNetworksList.innerHTML = '<div class="empty-networks">Loading...</div>';
    if ($('network-count')) $('network-count').textContent = '0';
    
    setupEvents();
    showLoading(true);
    
    try {
        await Promise.all([
            loadDeviceStatus(),
            loadWifiStatus(),
            loadSavedNetworks(),
            loadRocrailStatus(),
            loadNetworks()
        ]);
        
        setButtonsEnabled(true);
        
        // Periodic refresh
        setInterval(async () => {
            try {
                await Promise.all([loadDeviceStatus(), loadWifiStatus(), loadSavedNetworks(), loadRocrailStatus()]);
            } catch (e) { console.log('Background refresh failed:', e); }
        }, 30000);
        
    } catch (error) {
        showMessage('Initialization failed', 'error');
        els.deviceInfo.innerHTML = '<b>Device:</b> ESP32/ESP8266<br><b>Status:</b> ❌ Failed';
        els.currentRocrailConfig.innerHTML = '<b>Current Server:</b> Not configured';
        els.currentWifiConfig.innerHTML = '<b>Current:</b> Not configured';
        els.savedNetworksList.innerHTML = '<div class="empty-networks">Failed to load</div>';
        setButtonsEnabled(true);
    }
}

// Global functions for onclick handlers
window.removeNetwork = removeNetwork;
window.loadSavedNetworks = loadSavedNetworks;

// Start app
document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();