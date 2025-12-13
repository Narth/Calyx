#!/usr/bin/env python3
"""
Example Integration - Demonstrates how to integrate teaching methods with existing Calyx Terminal agents
"""

import json
import time
import logging
from datetime import datetime

# Example of how an existing agent would integrate with the teaching system
from .agent_teaching_integration import AgentTeachingIntegration


class ExampleAgentWithTeaching:
    """
    Example agent that demonstrates integration with the AI-for-All teaching system.
    This shows how existing agents in Calyx Terminal can be enhanced with teaching capabilities.
    """

    def __init__(self, agent_id: str = "example_agent"):
        """
        Initialize the example agent with teaching integration.

        Args:
            agent_id: Unique identifier for this agent
        """
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"example_agent.{agent_id}")

        # Initialize teaching integration
        self.teaching_integration = AgentTeachingIntegration(agent_id)

        # Agent state
        self.performance_metrics = {
            'tes': 75.0,
            'stability': 0.8,
            'velocity': 0.6,
            'error_rate': 0.1
        }

        self.task_count = 0
        self.success_count = 0

        # Enable teaching
        if self.teaching_integration.enable_teaching(['task_efficiency', 'stability']):
            self.logger.info("Teaching integration enabled")
        else:
            self.logger.warning("Teaching integration not available")

    def perform_task(self, task_type: str = "default") -> Dict[str, Any]:
        """
        Perform a simulated task and update teaching system.

        Args:
            task_type: Type of task being performed

        Returns:
            Task result with performance metrics
        """
        self.task_count += 1

        # Simulate task performance
        base_tes = 75.0
        base_stability = 0.8

        # Simulate some variation in performance
        import random
        random.seed()  # Use system time for randomness

        # Performance improves slightly over time (learning effect)
        improvement_factor = min(1.0, self.task_count / 100.0)

        # Add some randomness
        tes_variation = random.uniform(-5, 10) * (1 - improvement_factor)
        stability_variation = random.uniform(-0.1, 0.1) * (1 - improvement_factor)

        # Update metrics
        self.performance_metrics['tes'] = max(0, min(100, base_tes + tes_variation + (improvement_factor * 10)))
        self.performance_metrics['stability'] = max(0, min(1.0, base_stability + stability_variation + (improvement_factor * 0.1)))

        # Simulate task success based on performance
        success_threshold = 70.0
        task_success = self.performance_metrics['tes'] > success_threshold
        if task_success:
            self.success_count += 1

        self.performance_metrics['velocity'] = self.task_count / max(1, (datetime.now().timestamp() - time.time() + 3600))
        self.performance_metrics['error_rate'] = 1 - (self.success_count / max(1, self.task_count))

        # Prepare context
        context = {
            'task_type': task_type,
            'task_count': self.task_count,
            'success_rate': self.success_count / max(1, self.task_count),
            'improvement_factor': improvement_factor
        }

        # Update teaching system
        teaching_response = self.teaching_integration.update_performance(
            self.performance_metrics,
            context
        )

        # Apply any teaching adaptations
        if teaching_response.get('adaptations_applied'):
            for adaptation in teaching_response['adaptations_applied']:
                self._apply_adaptation(adaptation)

        # Return task result
        result = {
            'task_id': f"{self.agent_id}_task_{self.task_count}",
            'task_type': task_type,
            'success': task_success,
            'performance_metrics': self.performance_metrics.copy(),
            'teaching_response': teaching_response,
            'timestamp': datetime.now().isoformat()
        }

        tes_formatted = f"{self.performance_metrics['tes']:.1f}"
        self.logger.info(f"Task {self.task_count} completed: success={task_success}, TES={tes_formatted}")
        return result

    def _apply_adaptation(self, adaptation: Dict[str, Any]):
        """Apply teaching adaptation to agent behavior"""
        try:
            adaptation_desc = adaptation.get('adaptation', 'Unknown adaptation')

            # Example adaptations that could be applied:
            if 'learning_rate' in adaptation_desc.lower():
                # Adjust learning rate (example implementation)
                self.logger.info(f"Adjusting learning rate based on teaching feedback: {adaptation_desc}")

            elif 'stability' in adaptation_desc.lower():
                # Adjust stability parameters
                self.logger.info(f"Adjusting stability parameters based on teaching feedback: {adaptation_desc}")

            elif 'exploration' in adaptation_desc.lower():
                # Adjust exploration behavior
                self.logger.info(f"Adjusting exploration behavior based on teaching feedback: {adaptation_desc}")

            else:
                self.logger.info(f"Applied teaching adaptation: {adaptation_desc}")

        except Exception as e:
            self.logger.error(f"Error applying adaptation: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status including teaching integration"""
        status = {
            'agent_id': self.agent_id,
            'task_count': self.task_count,
            'success_count': self.success_count,
            'success_rate': self.success_count / max(1, self.task_count),
            'current_metrics': self.performance_metrics.copy(),
            'teaching_integration': self.teaching_integration.get_teaching_status(),
            'recommendations': self.teaching_integration.get_recommendations(),
            'timestamp': datetime.now().isoformat()
        }

        return status

    def run_simulation(self, num_tasks: int = 10, task_interval: float = 1.0):
        """
        Run a simulation of the agent performing tasks.

        Args:
            num_tasks: Number of tasks to simulate
            task_interval: Time between tasks in seconds
        """
        self.logger.info(f"Starting simulation with {num_tasks} tasks")

        results = []

        for i in range(num_tasks):
            # Vary task types
            task_types = ['default', 'complex', 'simple', 'urgent']
            task_type = task_types[i % len(task_types)]

            result = self.perform_task(task_type)
            results.append(result)

            # Wait between tasks
            if i < num_tasks - 1:  # Don't wait after last task
                time.sleep(task_interval)

        # Final status
        final_status = self.get_status()
        results.append({'final_status': final_status})

        self.logger.info(f"Simulation completed: {self.task_count} tasks, {self.success_count} successes")

        return results

    def export_results(self, output_path: str = None) -> str:
        """Export simulation results and performance data"""
        if not output_path:
            timestamp = int(time.time())
            output_path = f"outgoing/ai4all/examples/example_agent_{self.agent_id}_{timestamp}.json"

        # Get current status
        status = self.get_status()

        # Export teaching data
        teaching_export = self.teaching_integration.export_performance_data()

        export_data = {
            'agent_id': self.agent_id,
            'simulation_results': {
                'task_count': self.task_count,
                'success_count': self.success_count,
                'success_rate': self.success_count / max(1, self.task_count),
                'final_metrics': self.performance_metrics
            },
            'teaching_export_path': teaching_export,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        self.logger.info(f"Results exported to {output_path}")
        return output_path


def demonstrate_integration():
    """Demonstrate the teaching integration with a sample agent"""
    logging.basicConfig(level=logging.INFO)

    print("AI-for-All Teaching Integration Demonstration")
    print("=" * 50)

    # Create example agent
    agent = ExampleAgentWithTeaching("demo_agent")

    # Show initial status
    print("\nInitial Status:")
    status = agent.get_status()
    print(f"Agent: {status['agent_id']}")
    print(f"Teaching Enabled: {status['teaching_integration']['teaching_enabled']}")
    tes_formatted = f"{status['current_metrics']['tes']:.1f}"
    stability_formatted = f"{status['current_metrics']['stability']:.3f}"
    print(f"Initial TES: {tes_formatted}")
    print(f"Initial Stability: {stability_formatted}")

    # Run simulation
    print("\nRunning simulation...")
    results = agent.run_simulation(num_tasks=15, task_interval=0.5)

    # Show final status
    print("\nFinal Status:")
    final_status = agent.get_status()
    print(f"Tasks Completed: {final_status['task_count']}")
    success_rate_formatted = f"{final_status['success_rate']:.1%}"
    final_tes_formatted = f"{final_status['current_metrics']['tes']:.1f}"
    print(f"Success Rate: {success_rate_formatted}")
    print(f"Final TES: {final_tes_formatted}")
    final_stability_formatted = f"{final_status['current_metrics']['stability']:.3f}"
    print(f"Final Stability: {final_stability_formatted}")

    # Show teaching recommendations
    print("\nTeaching Recommendations:")
    recommendations = final_status['recommendations']
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    # Export results
    export_path = agent.export_results()
    print(f"\nResults exported to: {export_path}")

    return results


if __name__ == "__main__":
    demonstrate_integration()
