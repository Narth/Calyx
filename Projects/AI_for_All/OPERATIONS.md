# AI-for-All Teaching System - Operations Guide

This guide provides operational procedures for using and maintaining the AI-for-All teaching system in the Calyx Terminal.

## Overview

The AI-for-All teaching system implements baseline teaching methods to improve learning and training efficiency across agents. It provides:

- **Adaptive Learning**: Dynamic adjustment of learning parameters
- **Performance Tracking**: Comprehensive metrics and trend analysis
- **Knowledge Integration**: Cross-agent pattern sharing
- **Pattern Recognition**: Behavioral pattern identification and optimization

## Quick Start

### 1. Initialize the Teaching System

```bash
# From Calyx Terminal root directory
cd Projects/AI_for_All

# Start the teaching system
python ai4all_teaching.py --start
```

### 2. Enable Teaching for Agents

The teaching system can be enabled for different agents:

```bash
# Enable teaching for Agent1
python ai4all_teaching.py --agent-status agent1

# Enable teaching for Triage
python ai4all_teaching.py --agent-status triage

# Enable teaching for copilots
python ai4all_teaching.py --agent-status cp6
```

### 3. Monitor System Status

```bash
# Get overall system status
python ai4all_teaching.py --status

# Get recommendations for all agents
python ai4all_teaching.py --recommendations
```

## Integration with Existing Agents

### Method 1: Import Integration Module

Add teaching integration to existing agents by importing and using the integration module:

```python
from Projects.AI_for_All.integration.agent_teaching_integration import AgentTeachingIntegration

class MyAgent:
    def __init__(self):
        self.teaching = AgentTeachingIntegration("my_agent_id")

        # Enable teaching
        self.teaching.enable_teaching(['task_efficiency', 'stability'])

    def perform_task(self, metrics):
        # Update performance metrics
        response = self.teaching.update_performance(metrics)

        # Apply any teaching adaptations
        if response.get('adaptations_applied'):
            for adaptation in response['adaptations_applied']:
                self.apply_adaptation(adaptation)
```

### Method 2: Direct Framework Integration

For more control, use the teaching framework directly:

```python
from Projects.AI_for_All.teaching.framework import TeachingFramework
from Projects.AI_for_All.teaching.agent_interface import AgentTeachingInterface

# Initialize framework
framework = TeachingFramework("config/teaching_config.yaml")
agent_interface = AgentTeachingInterface(framework)

# Enable teaching for agent
agent_interface.enable_teaching("my_agent", ['task_efficiency'])

# Update performance
response = agent_interface.update_agent_performance(
    "my_agent",
    {"tes": 85, "stability": 0.9, "velocity": 0.7}
)
```

## Configuration

### Main Configuration File

The teaching system is configured via `config/teaching_config.yaml`:

```yaml
# Adaptive Learning Parameters
adaptive_learning:
  learning_rate: 0.1
  momentum: 0.9
  min_improvement_threshold: 0.05

# Performance Tracking
performance_tracking:
  retention_days: 30
  improvement_threshold: 0.1

# Integration Settings
system_integration:
  heartbeat_interval: 60
  log_level: "INFO"
```

### Agent-Specific Configuration

Create agent configurations in `config/agent_teaching_configs.json`:

```json
{
  "agent1": {
    "teaching_enabled": true,
    "learning_objectives": ["task_efficiency", "stability"],
    "baseline_metrics": {"tes": 85, "stability": 0.9}
  },
  "triage": {
    "teaching_enabled": true,
    "learning_objectives": ["latency_optimization"],
    "baseline_metrics": {"tes": 90, "velocity": 0.8}
  }
}
```

## Monitoring and Metrics

### System Heartbeat

The teaching system emits regular heartbeats to `outgoing/ai4all/teaching_heartbeat.json`:

```bash
# View latest heartbeat
cat outgoing/ai4all/teaching_heartbeat.json
```

### Performance Metrics

Performance data is stored in `outgoing/ai4all/metrics/`:

```bash
# View agent performance
python ai4all_teaching.py --agent-status agent1

# Export performance data
python ai4all_teaching.py --export outgoing/ai4all/export/data.json
```

### Learning Progress

Track learning progress via the framework:

```python
from Projects.AI_for_All.teaching.framework import TeachingFramework

framework = TeachingFramework()
status = framework.get_system_status()

for session_id, session in framework.active_sessions.items():
    progress = framework.get_learning_progress(session_id)
    print(f"Session {session_id}: {progress['session']['progress_score']:.2%} complete")
```

## Teaching Methods

### 1. Adaptive Learning

The system automatically adjusts learning parameters based on performance:

- **Learning Rate**: Adjusted based on improvement rate
- **Momentum**: Modified for stability vs. exploration balance
- **Exploration Factor**: Tuned for pattern discovery

### 2. Pattern Recognition

Identifies successful behavioral patterns:

- **Temporal Patterns**: Behavior sequences that lead to success
- **Resource Patterns**: Optimal resource usage patterns
- **Interaction Patterns**: Successful agent interaction patterns
- **Performance Patterns**: Context that correlates with good performance

### 3. Knowledge Integration

Shares successful patterns across agents:

- **Pattern Transfer**: Moves successful patterns to other agents
- **Adaptation Suggestions**: Recommends pattern modifications
- **Impact Prediction**: Estimates pattern effectiveness

### 4. Performance Tracking

Comprehensive performance analysis:

- **Trend Analysis**: Identifies improving/declining metrics
- **Baseline Comparison**: Measures improvement from baseline
- **Composite Scoring**: Combines multiple metrics into scores

## Operational Commands

### System Management

```bash
# Start teaching system
python ai4all_teaching.py --start

# Stop teaching system (Ctrl+C)

# Check system status
python ai4all_teaching.py --status

# Get system recommendations
python ai4all_teaching.py --recommendations
```

### Agent-Specific Operations

```bash
# Enable teaching for specific agent
python ai4all_teaching.py --agent-status agent1

# Get recommendations for agent
python ai4all_teaching.py --agent-recommendations agent1

# Export agent data
python ai4all_teaching.py --export path/to/export.json
```

### Monitoring

```bash
# Emit heartbeat manually
python ai4all_teaching.py --heartbeat

# View verbose logs
python ai4all_teaching.py --verbose --status
```

## Troubleshooting

### Common Issues

#### 1. Teaching System Not Available

```bash
# Check if teaching framework can be imported
python -c "from Projects.AI_for_All.teaching.framework import TeachingFramework; print('OK')"

# Check configuration file
ls -la Projects/AI_for_All/config/teaching_config.yaml
```

#### 2. Agent Not Responding to Teaching

```bash
# Check agent status
python ai4all_teaching.py --agent-status <agent_id>

# Verify metrics are being updated
tail -f outgoing/ai4all/teaching_heartbeat.json
```

#### 3. Performance Not Improving

```bash
# Check recommendations
python ai4all_teaching.py --recommendations

# Review learning objectives
python ai4all_teaching.py --agent-status <agent_id>
```

### Debugging

Enable verbose logging:

```bash
python ai4all_teaching.py --verbose --status
```

Check log files:

```bash
# System logs
tail -f logs/agent_metrics.log

# Teaching system logs (if configured)
tail -f outgoing/ai4all/teaching.log
```

### Recovery Procedures

#### Reset Agent Teaching

```python
from Projects.AI_for_All.integration.agent_teaching_integration import AgentTeachingIntegration

agent = AgentTeachingIntegration("problematic_agent")
agent.disable_teaching()
agent.enable_teaching(['task_efficiency'])  # Start fresh
```

#### Clear Performance History

```bash
# Stop teaching system
# Remove performance data
rm -rf outgoing/ai4all/metrics/
rm -rf outgoing/ai4all/sessions/

# Restart teaching system
python ai4all_teaching.py --start
```

## Best Practices

### 1. Gradual Integration

- Start with one agent to test integration
- Monitor performance impact before enabling for all agents
- Use conservative learning objectives initially

### 2. Performance Monitoring

- Monitor TES (Tool Efficacy Score) for degradation
- Watch for stability issues when adaptations are applied
- Review recommendations regularly

### 3. Configuration Management

- Keep backup of configuration files before changes
- Test configuration changes in non-production environment
- Document configuration changes and their impact

### 4. Resource Management

- Monitor system resource usage during teaching activities
- Adjust heartbeat intervals if system is under load
- Consider resource constraints when setting adaptation parameters

## Integration Examples

### Agent1 Integration

```python
# In agent1's main loop
from Projects.AI_for_All.integration.agent_teaching_integration import integrate_with_agent1

teaching = integrate_with_agent1()

# After each task
metrics = {
    'tes': current_tes,
    'stability': current_stability,
    'velocity': task_velocity,
    'error_rate': error_rate
}

response = teaching.update_performance(metrics, {'task_type': 'agent_task'})
```

### Triage Integration

```python
# In triage probe
from Projects.AI_for_All.integration.agent_teaching_integration import integrate_with_triage

teaching = integrate_with_triage()

# After each probe cycle
metrics = {
    'tes': probe_tes,
    'stability': stability_score,
    'velocity': probe_velocity,
    'latency': probe_latency
}

response = teaching.update_performance(metrics, {'probe_type': 'health_check'})
```

### Copilot Integration

```python
# In copilot implementation
from Projects.AI_for_All.integration.agent_teaching_integration import integrate_with_copilot

teaching = integrate_with_copilot("cp7")

# After each analysis cycle
metrics = {
    'accuracy': analysis_accuracy,
    'efficiency': processing_efficiency,
    'stability': output_stability
}

response = teaching.update_performance(metrics, {'analysis_type': 'diagnostic'})
```

## Maintenance

### Regular Tasks

1. **Weekly Review**
   - Check teaching recommendations for all agents
   - Review performance trends
   - Update baselines if needed

2. **Monthly Maintenance**
   - Clean up old performance data
   - Review and update agent configurations
   - Export comprehensive performance reports

3. **Quarterly Review**
   - Assess overall teaching system effectiveness
   - Update learning objectives based on system evolution
   - Review cross-agent pattern transfer success

### Backup and Recovery

```bash
# Backup teaching data
tar -czf ai4all_backup_$(date +%Y%m%d).tar.gz outgoing/ai4all/

# Restore teaching data
tar -xzf ai4all_backup_*.tar.gz -C /
```

### Log Rotation

```bash
# Rotate teaching logs (add to cron or scheduled task)
find outgoing/ai4all/ -name "*.log" -mtime +30 -delete
find outgoing/ai4all/ -name "*.json" -mtime +90 -delete
```

## Support and Troubleshooting

### Getting Help

1. **Check Status First**
   ```bash
   python ai4all_teaching.py --status
   python ai4all_teaching.py --recommendations
   ```

2. **Review Logs**
   ```bash
   # Check recent activity
   tail -50 outgoing/ai4all/teaching_heartbeat.json
   ```

3. **Consult Documentation**
   - Configuration options: `config/teaching_config.yaml`
   - Integration examples: `integration/example_integration.py`
   - Framework API: Framework and integration module docstrings

### Reporting Issues

When reporting issues, include:

- System status output
- Agent status for affected agents
- Recent heartbeat data
- Configuration files (with sensitive data removed)
- Steps to reproduce the issue

## Security Considerations

- Teaching system operates within Calyx Terminal's local-only security model
- No network access required or permitted
- All data remains within the project directory
- Integration respects existing agent permissions and safety gates
