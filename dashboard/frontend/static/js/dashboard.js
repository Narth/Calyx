// Station Calyx Dashboard - JavaScript

const API_BASE = 'http://localhost:8080/api';
let updateInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Station Calyx Dashboard initialized');
    
    // Start real-time updates
    startUpdates();
    
    // Load initial data
    loadSystemHealth();
    loadAgents();
    loadApprovals();
    loadChatHistory();
    
    // Set up event listeners
    setupEventListeners();
});

// Start real-time updates
function startUpdates() {
    // Update every 5 seconds
    updateInterval = setInterval(() => {
        loadSystemHealth();
        loadAgents();
        loadApprovals();
    }, 5000);
    
    // Update chat every 2 seconds
    setInterval(() => {
        loadChatHistory();
    }, 2000);
}

// Event listeners
function setupEventListeners() {
    // Send message button
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    
    // Broadcast button
    document.getElementById('broadcast-btn').addEventListener('click', sendBroadcast);
    
    // Direct to CBO button
    document.getElementById('direct-btn').addEventListener('click', sendDirect);
    
    // Enter key in message input
    document.getElementById('message-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

// Load system health
async function loadSystemHealth() {
    try {
        const response = await fetch(`${API_BASE}/health/current`);
        const data = await response.json();
        
        updateHealthMetrics(data);
        updateLastSync();
    } catch (error) {
        console.error('Error loading health:', error);
    }
}

// Update health metrics display
function updateHealthMetrics(data) {
    // CPU
    const cpu = data.cpu?.usage_pct || 0;
    document.getElementById('cpu-value').textContent = `${cpu}%`;
    const cpuBar = document.getElementById('cpu-bar');
    cpuBar.style.width = `${cpu}%`;
    cpuBar.className = 'metric-bar-fill' + getBarClass(cpu);
    
    // RAM
    const ram = data.ram?.usage_pct || 0;
    document.getElementById('ram-value').textContent = `${ram}%`;
    const ramBar = document.getElementById('ram-bar');
    ramBar.style.width = `${ram}%`;
    ramBar.className = 'metric-bar-fill' + getBarClass(ram);
    
    // Disk
    const disk = data.disk?.usage_pct || 0;
    document.getElementById('disk-value').textContent = `${disk}%`;
    const diskBar = document.getElementById('disk-bar');
    diskBar.style.width = `${disk}%`;
    diskBar.className = 'metric-bar-fill' + getBarClass(disk);
    
    // TES
    const tes = data.tes?.current || 0;
    document.getElementById('tes-value').textContent = tes.toFixed(1);
    const tesBar = document.getElementById('tes-bar');
    tesBar.style.width = `${tes}%`;
    tesBar.className = 'metric-bar-fill' + getBarClass(tes);
    
    // Network
    const network = data.network?.status || 'closed';
    document.getElementById('network-value').textContent = network.toUpperCase();
    document.getElementById('network-icon').textContent = network === 'open' ? '✅' : '⛔';
    
    // Phase
    const phases = data.phases || {};
    const phaseIndicators = document.getElementById('phase-indicators');
    ['phase0', 'phase1', 'phase2', 'phase3'].forEach((phase, idx) => {
        const dot = phaseIndicators.children[idx];
        if (phases[phase] === 'active') {
            dot.classList.add('active');
        } else {
            dot.classList.remove('active');
        }
    });
    
    // Footer metrics
    const tesDelta = data.tes?.delta_24h || 0;
    document.getElementById('tes-trend').textContent = `${tesDelta >= 0 ? '▲' : '▼'} ${Math.abs(tesDelta).toFixed(1)}%`;
}

// Get bar class based on value
function getBarClass(value) {
    if (value >= 90) return ' danger';
    if (value >= 70) return ' warning';
    return '';
}

// Update last sync time
function updateLastSync() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
    document.getElementById('last-sync').textContent = `Last Sync: ${timeStr}`;
}

// Load agents
async function loadAgents() {
    try {
        const response = await fetch(`${API_BASE}/agents/list`);
        const agents = await response.json();
        
        displayAgents(agents);
    } catch (error) {
        console.error('Error loading agents:', error);
    }
}

// Display agents in grid
function displayAgents(agents) {
    const grid = document.getElementById('agent-grid');
    grid.innerHTML = '';
    
    agents.forEach(agent => {
        const card = createAgentCard(agent);
        grid.appendChild(card);
    });
}

// Create agent card
function createAgentCard(agent) {
    const card = document.createElement('div');
    card.className = `agent-card ${agent.status}`;
    
    const statusIcon = agent.status === 'active' ? 'active' : 'inactive';
    
    card.innerHTML = `
        <div class="agent-name">${agent.name}</div>
        <div class="agent-role">${agent.role}</div>
        <div class="agent-status">
            <span class="status-icon ${statusIcon}"></span>
            <span>${agent.status.toUpperCase()}</span>
        </div>
        <div class="agent-last-activity">${formatTimeAgo(agent.last_activity)}</div>
    `;
    
    card.addEventListener('click', () => {
        console.log('Agent clicked:', agent.agent_id);
        // TODO: Open agent detail modal
    });
    
    return card;
}

// Format time ago
function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
}

// Load approvals
async function loadApprovals() {
    try {
        const response = await fetch(`${API_BASE}/approvals/pending`);
        const approvals = await response.json();
        
        displayApprovals(approvals);
    } catch (error) {
        console.error('Error loading approvals:', error);
    }
}

// Display approvals
function displayApprovals(approvals) {
    const list = document.getElementById('approvals-list');
    list.innerHTML = '';
    
    document.getElementById('pending-count').textContent = approvals.length;
    document.getElementById('footer-pending').textContent = approvals.length;
    
    approvals.forEach(approval => {
        const item = createApprovalItem(approval);
        list.appendChild(item);
    });
}

// Create approval item
function createApprovalItem(approval) {
    const item = document.createElement('div');
    item.className = 'approval-item';
    
    item.innerHTML = `
        <div class="approval-id">${approval.intent_id}</div>
        <div class="approval-status">${approval.type} - ${approval.status}</div>
        <div class="action-buttons" style="margin-top: 0.5rem;">
            <button class="btn-primary" onclick="approveRequest('${approval.approval_id}')">Approve</button>
            <button class="btn-secondary" onclick="rejectRequest('${approval.approval_id}')">Reject</button>
        </div>
    `;
    
    return item;
}

// Approve request (global scope for onclick)
window.approveRequest = async function(approvalId) {
    try {
        const response = await fetch(`${API_BASE}/approvals/${approvalId}/approve`, {
            method: 'POST'
        });
        
        if (response.ok) {
            alert('Approval processed successfully!');
            loadApprovals();
            addChatMessage('User1', 'Approval processed');
        } else {
            alert('Failed to process approval');
        }
    } catch (error) {
        console.error('Error approving:', error);
        alert('Error processing approval: ' + error.message);
    }
}

// Reject request (global scope for onclick)
window.rejectRequest = async function(approvalId) {
    const reason = prompt('Reason for rejection:');
    if (!reason) return;
    
    try {
        const response = await fetch(`${API_BASE}/approvals/${approvalId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        });
        
        if (response.ok) {
            alert('Request rejected successfully!');
            loadApprovals();
            addChatMessage('User1', 'Request rejected: ' + reason);
        } else {
            alert('Failed to reject request');
        }
    } catch (error) {
        console.error('Error rejecting:', error);
        alert('Error rejecting request: ' + error.message);
    }
}

// Load chat history
async function loadChatHistory() {
    try {
        const response = await fetch(`${API_BASE}/chat/history?limit=50`);
        const messages = await response.json();
        
        // Enrich messages with receipt status
        for (let msg of messages) {
            if (msg.message_id && msg.sender === 'user1') {
                try {
                    const receiptResponse = await fetch(`${API_BASE}/chat/receipts/${msg.message_id}`);
                    if (receiptResponse.ok) {
                        const receiptData = await receiptResponse.json();
                        msg.metadata = msg.metadata || {};
                        msg.metadata.receipt_status = receiptData.status;
                        msg.metadata.receipt_delivered = receiptData.delivered;
                        msg.metadata.receipt_read = receiptData.read;
                        msg.metadata.receipt_total = receiptData.total_recipients;
                    }
                } catch (e) {
                    console.error('Error fetching receipt:', e);
                }
            }
        }
        
        // Also check for agent responses
        const agentResponses = await loadAgentResponses();
        const allMessages = [...messages, ...agentResponses].sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
        );
        
        displayChatHistory(allMessages);
    } catch (error) {
        console.error('Error loading chat:', error);
    }
}

// Load agent responses
async function loadAgentResponses() {
    try {
        const response = await fetch(`${API_BASE}/chat/agent-responses?limit=20`);
        const responses = await response.json();
        return responses;
    } catch (error) {
        // If endpoint doesn't exist yet, return empty array
        return [];
    }
}

// Display chat history
function displayChatHistory(messages) {
    const history = document.getElementById('terminal-history');
    
    // Save scroll position before update
    const wasAtBottom = history.scrollHeight - history.scrollTop <= history.clientHeight + 10;
    
    history.innerHTML = '';
    
    messages.forEach(msg => {
        const item = createMessageItem(msg);
        history.appendChild(item);
    });
    
    // Only auto-scroll if user was already at bottom
    if (wasAtBottom) {
        history.scrollTop = history.scrollHeight;
    }
}

// Create message item
function createMessageItem(msg) {
    const item = document.createElement('div');
    item.className = 'message-item';
    
    // Handle different timestamp formats
    let timestamp;
    try {
        timestamp = new Date(msg.timestamp).toLocaleTimeString('en-US', { hour12: false });
    } catch (e) {
        timestamp = 'now';
    }
    
    // Highlight CBO responses
    const senderClass = msg.sender === 'CBO' ? 'cbo-response' : '';
    
    // Get receipt indicator
    const receiptIndicator = getReceiptIndicator(msg);
    
    item.innerHTML = `
        <div>
            <span class="message-agent ${senderClass}">${msg.sender}</span>
            <span class="message-time">${timestamp}</span>
            ${receiptIndicator}
        </div>
        <div class="message-content">${msg.content}</div>
    `;
    
    return item;
}

// Get receipt indicator for message
function getReceiptIndicator(msg) {
    // Only show for user's own messages
    if (msg.sender !== 'user1') {
        return '';
    }
    
    // Check if message has metadata with receipt info
    if (msg.metadata && msg.metadata.receipt_status) {
        const status = msg.metadata.receipt_status;
        if (status === 'read') {
            return '<span class="receipt-status" title="Read">&check;&check;</span>';
        } else if (status === 'delivered') {
            return '<span class="receipt-status" title="Delivered">&check;</span>';
        } else {
            return '<span class="receipt-status queued" title="Queued">...</span>';
        }
    }
    
    // Default: queued
    return '<span class="receipt-status queued" title="Queued">...</span>';
}

// Send message
async function sendMessage() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    
    if (!content) {
        alert('Please enter a message');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/chat/broadcast`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, priority: 'medium' })
        });
        
        if (response.ok) {
            input.value = '';
            addChatMessage('User1', content);
            setTimeout(loadChatHistory, 500);
        } else {
            alert('Failed to send message');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Error sending message: ' + error.message);
    }
}

// Send broadcast
async function sendBroadcast() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    
    if (!content) {
        alert('Please enter a message');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/chat/broadcast`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, priority: 'high' })
        });
        
        if (response.ok) {
            input.value = '';
            addChatMessage('User1', '[BROADCAST] ' + content);
            setTimeout(loadChatHistory, 500);
        } else {
            alert('Failed to broadcast message');
        }
    } catch (error) {
        console.error('Error broadcasting:', error);
        alert('Error broadcasting: ' + error.message);
    }
}

// Send direct to CBO
async function sendDirect() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();
    
    if (!content) {
        alert('Please enter a message');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/chat/direct`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recipient: 'cbo', content })
        });
        
        if (response.ok) {
            input.value = '';
            addChatMessage('User1', '@CBO: ' + content);
            setTimeout(loadChatHistory, 500);
        } else {
            alert('Failed to send direct message');
        }
    } catch (error) {
        console.error('Error sending direct:', error);
        alert('Error sending direct message: ' + error.message);
    }
}

// Add chat message (for UI feedback)
function addChatMessage(sender, content) {
    const history = document.getElementById('terminal-history');
    const item = createMessageItem({
        sender,
        content,
        timestamp: new Date().toISOString()
    });
    history.appendChild(item);
    
    // Always scroll to bottom when user sends a message
    history.scrollTop = history.scrollHeight;
}

