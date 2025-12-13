# AI-for-All Teaching System

A comprehensive baseline teaching methods implementation for the Calyx Terminal, designed to improve learning and training efficiency across all agents and copilots.

## Overview

The AI-for-All project introduces systematic teaching and learning methods to enhance agent performance, adaptability, and efficiency. This includes standardized approaches for knowledge transfer, adaptive learning algorithms, performance tracking, and cross-agent knowledge sharing.

## Features

### 🎯 **Adaptive Learning**
- Dynamic adjustment of learning parameters based on performance
- Multi-modal feedback integration (success rates, timing, resource usage)
- Automatic difficulty scaling and optimization

### 📊 **Performance Tracking**
- Comprehensive metrics collection and analysis
- Trend identification and forecasting
- Baseline establishment and improvement measurement

### 🧠 **Knowledge Integration**
- Cross-agent pattern sharing and transfer
- Successful behavior pattern identification
- Knowledge validation and adaptation

### 🔍 **Pattern Recognition**
- Behavioral pattern analysis and classification
- Success pattern identification and reinforcement
- Inefficient pattern detection and mitigation

## Architecture

### Core Components

```
Projects/AI_for_All/
├── teaching/                 # Core teaching framework
│   ├── framework.py         # Main teaching orchestration
│   ├── adaptive_learner.py  # Dynamic parameter adjustment
│   ├── performance_tracker.py # Metrics and trend analysis
│   ├── knowledge_integrator.py # Cross-agent knowledge sharing
│   └── pattern_recognition.py  # Behavioral pattern analysis
├── integration/             # Integration with existing agents
│   ├── agent_teaching_integration.py # Agent integration layer
│   └── example_integration.py # Usage examples
├── config/                  # Configuration files
│   └── teaching_config.yaml # System configuration
└── .vscode/                 # Development tools
    └── tasks.json           # VS Code integration
```

### Key Classes

- **`TeachingFramework`**: Main orchestration engine
- **`AdaptiveLearner`**: Handles dynamic parameter adjustment
- **`PerformanceTracker`**: Comprehensive performance analysis
- **`KnowledgeIntegrator`**: Manages cross-agent learning
- **`PatternRecognition`**: Identifies successful behaviors
- **`AgentTeachingIntegration`**: Easy integration for existing agents

## Quick Start

### 1. Initialize the System

```bash
# Navigate to the project directory
cd Projects/AI_for_All

# Start the teaching system
python ai4all_teaching.py --start

# Check system status
python ai4all_teaching.py --status
```

### 2. Enable Teaching for Agents

```bash
# Enable teaching for Agent1
python ai4all_teaching.py --agent-status agent1

# Enable teaching for Triage
python ai4all_teaching.py --agent-status triage

# Enable teaching for copilots
python ai4all_teaching.py --agent-status cp6
```

### 3. Monitor and Optimize

```bash
# Get teaching recommendations
python ai4all_teaching.py --recommendations

# Export learning data for analysis
python ai4all_teaching.py --export outgoing/ai4all/export/data.json
```

## Integration Examples

### Basic Agent Integration

```python
from Projects.AI_for_All.integration.agent_teaching_integration import AgentTeachingIntegration

class MyAgent:
    def __init__(self):
        # Initialize teaching integration
        self.teaching = AgentTeachingIntegration("my_agent")
        self.teaching.enable_teaching(['task_efficiency', 'stability'])

    def perform_task(self):
        # Your agent logic here
        metrics = {
            'tes': 85.0,
            'stability': 0.9,
            'velocity': 0.7,
            'error_rate': 0.05
        }

        # Update teaching system
        response = self.teaching.update_performance(metrics)

        # Apply teaching adaptations
        if response.get('adaptations_applied'):
            for adaptation in response['adaptations_applied']:
                self.apply_adaptation(adaptation)
```

### Framework Direct Usage

```python
from Projects.AI_for_All.teaching.framework import TeachingFramework
from Projects.AI_for_All.teaching.agent_interface import AgentTeachingInterface

# Initialize framework
framework = TeachingFramework("config/teaching_config.yaml")
agent_interface = AgentTeachingInterface(framework)

# Enable teaching for an agent
agent_interface.enable_teaching("my_agent", ['task_efficiency'])

# Update performance and get feedback
response = agent_interface.update_agent_performance(
    "my_agent",
    {"tes": 85, "stability": 0.9, "velocity": 0.7}
)

# Get learning progress
progress = framework.get_learning_progress(session_id)
```

## Configuration

### Main Configuration

The system is configured via `config/teaching_config.yaml`:

```yaml
# Adaptive learning parameters
adaptive_learning:
  learning_rate: 0.1
  min_improvement_threshold: 0.05
  max_adaptation_attempts: 10

# Performance tracking
performance_tracking:
  retention_days: 30
  improvement_threshold: 0.1

# Pattern recognition
pattern_recognition:
  min_occurrences: 3
  strength_threshold: 0.7
```

### Agent-Specific Configuration

Configure individual agents in `config/agent_teaching_configs.json`:

```json
{
  "agent1": {
    "teaching_enabled": true,
    "learning_objectives": ["task_efficiency", "stability"],
    "baseline_metrics": {"tes": 85, "stability": 0.9}
  }
}
```

## Teaching Methods

### 1. **Adaptive Baseline Teaching**
- Establishes performance baselines for each agent
- Dynamically adjusts teaching parameters based on progress
- Scales difficulty and focus areas automatically

### 2. **Pattern Recognition Teaching**
- Identifies successful behavioral patterns
- Analyzes performance correlations
- Transfers successful patterns to other agents

### 3. **Collaborative Learning**
- Shares knowledge across agents
- Identifies transferable patterns
- Adapts patterns for different agent types

### 4. **Predictive Optimization**
- Forecasts performance trends
- Proactively adjusts parameters
- Prevents performance degradation

## Monitoring and Metrics

### System Heartbeat

Monitor system health via heartbeat files:

```bash
# Latest heartbeat
cat outgoing/ai4all/teaching_heartbeat.json

# Framework status
python ai4all_teaching.py --status
```

### Performance Metrics

Track agent performance and learning progress:

```bash
# Agent-specific status
python ai4all_teaching.py --agent-status agent1

# System-wide recommendations
python ai4all_teaching.py --recommendations
```

### Learning Progress

Monitor learning sessions and progress:

```python
# Get all active sessions
for session_id, session in framework.active_sessions.items():
    progress = framework.get_learning_progress(session_id)
    print(f"Session {session_id}: {progress['session']['progress_score']:.1%} complete")
```

## VS Code Integration

Use VS Code tasks for easy operation:

- **AI4All: Start Teaching System** - Start the teaching system
- **AI4All: System Status** - Check system status
- **AI4All: Teaching Recommendations** - Get optimization recommendations
- **AI4All: Agent1 Teaching Status** - Check Agent1 teaching status
- **AI4All: Run Integration Example** - Run example integration
- **AI4All: Export Learning Data** - Export learning data

## Operational Commands

### System Management

```bash
# Start teaching system
python ai4all_teaching.py --start

# Check status
python ai4all_teaching.py --status

# Get recommendations
python ai4all_teaching.py --recommendations

# Export data
python ai4all_teaching.py --export path/to/export.json
```

### Agent Management

```bash
# Enable teaching for agent
python ai4all_teaching.py --agent-status <agent_id>

# Get agent recommendations
python ai4all_teaching.py --agent-recommendations <agent_id>
```

### Monitoring

```bash
# Emit heartbeat
python ai4all_teaching.py --heartbeat

# Verbose output
python ai4all_teaching.py --verbose --status
```

## Integration with Calyx Terminal

The teaching system integrates seamlessly with existing Calyx Terminal components:

- **Agent System**: Enhanced with learning capabilities
- **Metrics Collection**: Extended with teaching effectiveness metrics
- **Scheduler**: Improved with learning-aware task distribution
- **Triage**: Enhanced with adaptive learning thresholds
- **Navigator**: Optimized with pattern-based routing
- **SVF Protocol**: Integrated with knowledge sharing

## Safety and Ethics

The teaching system prioritizes:

- **System Stability**: Safety gates prevent performance degradation
- **Reversibility**: All changes can be rolled back
- **Resource Management**: Respects system resource constraints
- **Privacy**: Local-only operation, no external data sharing

## Troubleshooting

### Common Issues

1. **Teaching System Not Starting**
   ```bash
   # Check configuration
   python -c "from teaching.framework import TeachingFramework; print('OK')"

   # Check dependencies
   pip list | grep -E "(numpy|scipy|statistics)"
   ```

2. **Agent Not Responding to Teaching**
   ```bash
   # Check agent integration
   python ai4all_teaching.py --agent-status <agent_id>

   # Verify metrics updates
   tail outgoing/ai4all/teaching_heartbeat.json
   ```

3. **Performance Degradation**
   ```bash
   # Get recommendations
   python ai4all_teaching.py --recommendations

   # Check system status
   python ai4all_teaching.py --status
   ```

### Getting Help

- Check the [Operations Guide](OPERATIONS.md) for detailed procedures
- Review [Configuration Guide](config/README.md) for setup options
- Examine [Integration Examples](integration/example_integration.py) for usage patterns

## Contributing

When extending the teaching system:

1. **Maintain Compatibility**: Ensure backward compatibility with existing agents
2. **Include Metrics**: Add comprehensive evaluation metrics
3. **Document Changes**: Update documentation for any modifications
4. **Test Thoroughly**: Validate with multiple agent types and scenarios

## License

This project is part of the Calyx Terminal ecosystem and follows the same operational and safety guidelines.

---

**AI-for-All Teaching System v1.0.0**
*Improving efficiency through systematic teaching and learning*