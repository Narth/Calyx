#!/usr/bin/env python3
"""
Dashboard Backend Main
Phase A - Backend Skeleton
"""
from __future__ import annotations

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from data_broker import MetricsBroker
from pathlib import Path

# Configure Flask to use frontend directories
BASE_DIR = Path(__file__).resolve().parent.parent
app = Flask(__name__, 
            template_folder=str(BASE_DIR / 'frontend' / 'templates'),
            static_folder=str(BASE_DIR / 'frontend' / 'static'))
CORS(app)

# Initialize data broker
broker = MetricsBroker()
broker.start()


@app.route('/')
def index():
    """Serve dashboard HTML"""
    return render_template('dashboard.html')

@app.route('/api/health/current', methods=['GET'])
def get_current_health():
    """Get current system health"""
    from api.health import get_current_health
    return jsonify(get_current_health())


@app.route('/api/health/history', methods=['GET'])
def get_health_history():
    """Get historical health data"""
    from api.health import get_health_history
    range_param = request.args.get('range', '24h')
    return jsonify(get_health_history(range_param))


@app.route('/api/health/pressure', methods=['GET'])
def get_pressure_heatmap():
    """Get resource pressure heatmap"""
    from api.health import get_pressure_heatmap
    return jsonify(get_pressure_heatmap())

@app.route('/api/analytics/tes-trend', methods=['GET'])
def get_tes_trend():
    """Get TES trend data"""
    from api.analytics import get_tes_trend
    days = request.args.get('days', 7, type=int)
    return jsonify(get_tes_trend(days))

@app.route('/api/analytics/lease-efficiency', methods=['GET'])
def get_lease_efficiency():
    """Get lease efficiency metrics"""
    from api.analytics import get_lease_efficiency
    return jsonify(get_lease_efficiency())


@app.route('/api/agents/list', methods=['GET'])
def list_agents():
    """List all agents"""
    from api.agents import list_agents
    return jsonify(list_agents())


@app.route('/api/agents/<agent_id>/status', methods=['GET'])
def get_agent_status(agent_id):
    """Get agent detailed status"""
    from api.agents import get_agent_status
    return jsonify(get_agent_status(agent_id))


@app.route('/api/agents/<agent_id>/logs', methods=['GET'])
def get_agent_logs(agent_id):
    """Get agent logs"""
    from api.agents import get_agent_logs
    limit = request.args.get('limit', 100, type=int)
    return jsonify(get_agent_logs(agent_id, limit))


@app.route('/api/leases/active', methods=['GET'])
def list_active_leases():
    """List active leases"""
    from api.leases import list_active_leases
    return jsonify(list_active_leases())


@app.route('/api/leases/<lease_id>/status', methods=['GET'])
def get_lease_status(lease_id):
    """Get lease detailed status"""
    from api.leases import get_lease_status
    return jsonify(get_lease_status(lease_id))


@app.route('/api/leases/<lease_id>/approve', methods=['POST'])
def approve_lease(lease_id):
    """Approve a lease"""
    from api.leases import approve_lease
    data = request.json
    human_id = data.get('human_id', 'user1')
    reason = data.get('reason', '')
    success = approve_lease(lease_id, human_id, reason)
    return jsonify({"success": success})


@app.route('/api/approvals/pending', methods=['GET'])
def list_pending_approvals():
    """List pending approvals"""
    from api.approvals import list_pending_approvals
    return jsonify(list_pending_approvals())


@app.route('/api/approvals/<approval_id>/approve', methods=['POST'])
def approve_request(approval_id):
    """Approve a request"""
    from api.approvals import approve_request
    success = approve_request(approval_id)
    return jsonify({"success": success})


@app.route('/api/approvals/<approval_id>/reject', methods=['POST'])
def reject_request(approval_id):
    """Reject a request"""
    from api.approvals import reject_request
    data = request.json
    reason = data.get('reason', '')
    success = reject_request(approval_id, reason)
    return jsonify({"success": success})


@app.route('/api/chat/history', methods=['GET'])
def get_chat_history():
    """Get chat history"""
    from api.chat import get_chat_history
    limit = request.args.get('limit', 50, type=int)
    return jsonify(get_chat_history(limit))


@app.route('/api/chat/broadcast', methods=['POST'])
def send_broadcast():
    """Send broadcast message"""
    from api.chat import send_broadcast
    data = request.json
    content = data.get('content', '')
    priority = data.get('priority', 'medium')
    success = send_broadcast(content, priority)
    return jsonify({"success": success})


@app.route('/api/chat/direct', methods=['POST'])
def send_direct_message():
    """Send direct message"""
    from api.chat import send_direct_message
    data = request.json
    recipient = data.get('recipient', '')
    content = data.get('content', '')
    success = send_direct_message(recipient, content)
    return jsonify({"success": success})

@app.route('/api/chat/agent-responses', methods=['GET'])
def get_agent_responses():
    """Get agent responses"""
    from api.chat import get_agent_responses
    limit = request.args.get('limit', 20, type=int)
    return jsonify(get_agent_responses(limit))

@app.route('/api/chat/receipts/<msg_id>', methods=['GET'])
def get_receipt_status(msg_id):
    """Get receipt status for a message"""
    from api.chat import get_receipt_status
    return jsonify(get_receipt_status(msg_id))


if __name__ == '__main__':
    print("Starting Station Calyx Dashboard Backend...")
    print("Phase A: Backend Skeleton")
    app.run(host='127.0.0.1', port=8080, debug=True)

