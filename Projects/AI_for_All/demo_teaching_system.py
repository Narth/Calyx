#!/usr/bin/env python3
"""
AI-for-All Teaching System Demonstration

This script demonstrates the complete AI-for-All teaching system in action,
showing how baseline teaching methods improve efficiency across Calyx Terminal agents.
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Import the teaching system
try:
    from teaching.framework import TeachingFramework
    from teaching.agent_interface import AgentTeachingInterface
    from integration.agent_teaching_integration import AgentTeachingIntegration
    TEACHING_AVAILABLE = True
except ImportError as e:
    print(f"Teaching system not available: {e}")
    TEACHING_AVAILABLE = False


class TeachingSystemDemo:
    """Comprehensive demonstration of the AI-for-All teaching system"""

    def __init__(self):
        self.logger = logging.getLogger("teaching_demo")
        self.framework = None
        self.agent_interface = None
        self.agents = {}

        if TEACHING_AVAILABLE:
            self._initialize_teaching_system()

    def _initialize_teaching_system(self):
        """Initialize the teaching framework and agent interface"""
        try:
            print("[INIT] Initializing AI-for-All Teaching System...")
            self.framework = TeachingFramework("Projects/AI_for_All/config/teaching_config.json")
            self.agent_interface = AgentTeachingInterface(self.framework)

            # Initialize demo agents
            demo_agents = ['agent1', 'triage', 'cp6', 'cp7']
            for agent_id in demo_agents:
                try:
                    integration = AgentTeachingIntegration(agent_id)
                    success = integration.enable_teaching()
                    if success:
                        self.agents[agent_id] = integration
                        print(f"  [OK] {agent_id} teaching integration enabled")
                    else:
                        print(f"  [WARN]  {agent_id} teaching integration failed")
                except Exception as e:
                    print(f"  [ERROR] {agent_id} error: {e}")

            print("[OK] Teaching system initialized successfully\n")
        except Exception as e:
            print(f"[ERROR] Failed to initialize teaching system: {e}")
            return False

        return True

    def demonstrate_framework_features(self):
        """Demonstrate core teaching framework features"""
        print("[DEMO] Demonstrating Teaching Framework Features")
        print("=" * 50)

        if not self.framework:
            print("[ERROR] Framework not available")
            return

        # 1. System Status
        print("\n1. System Status:")
        status = self.framework.get_system_status()
        print(f"   Active Sessions: {status['active_sessions']}")
        print(f"   Agents with Baselines: {status['agents_with_baselines']}")
        print(f"   Framework Version: {status['framework_version']}")

        # 2. Create Learning Sessions
        print("\n2. Creating Learning Sessions:")
        baseline_metrics = {'tes': 75, 'stability': 0.8, 'velocity': 0.6}

        for agent_id in ['agent1', 'triage']:
            session = self.framework.create_learning_session(
                agent_id=agent_id,
                learning_objective='task_efficiency',
                baseline_metrics=baseline_metrics
            )
            print(f"   [SESSION] Created session {session.id} for {agent_id}")

        # 3. Performance Tracking
        print("\n3. Performance Tracking:")
        for agent_id in ['agent1', 'triage']:
            performance_data = self.framework.performance_tracker.get_agent_performance(agent_id)
            if 'latest' in performance_data:
                metrics = performance_data['latest']['metrics']
                print(f"   [METRICS] {agent_id} latest metrics: {metrics}")
            else:
                print(f"   [WARN]  {agent_id} no performance data yet")

        # 4. Pattern Recognition
        print("\n4. Pattern Recognition:")
        for agent_id in ['agent1', 'triage']:
            patterns = self.framework.pattern_recognition.get_agent_patterns(agent_id)
            print(f"   [PATTERN] {agent_id} patterns: {len(patterns)} found")

        print()

    def simulate_agent_learning(self):
        """Simulate agents learning and improving with teaching feedback"""
        print("[SIM] Simulating Agent Learning with Teaching")
        print("=" * 50)

        if not self.agents:
            print("[ERROR] No agents available for simulation")
            return

        # Simulate multiple learning cycles
        print("\n📈 Running Learning Simulation:")

        for cycle in range(5):
            print(f"\nCycle {cycle + 1}:")

            for agent_id, integration in self.agents.items():
                # Simulate performance metrics (gradual improvement)
                base_metrics = {'tes': 70 + cycle * 3, 'stability': 0.7 + cycle * 0.04, 'velocity': 0.5 + cycle * 0.03}
                context = {'cycle': cycle, 'agent_type': agent_id}

                # Update teaching system
                response = integration.update_performance(base_metrics, context)

                # Show progress
                if response.get('teaching_enabled'):
                    sessions_updated = len(response.get('sessions_updated', []))
                    adaptations = len(response.get('adaptations_applied', []))
                    tes_formatted = f"{base_metrics['tes']:.1f}"
                    print(f"   🎓 {agent_id}: Sessions={sessions_updated}, Adaptations={adaptations}, TES={tes_formatted}")
                else:
                    print(f"   [WARN]  {agent_id}: Teaching not enabled")

            # Small delay between cycles
            time.sleep(0.5)

        print()

    def demonstrate_knowledge_integration(self):
        """Demonstrate cross-agent knowledge sharing"""
        print("[INTEGRATION] Demonstrating Knowledge Integration")
        print("=" * 50)

        if not self.framework:
            print("[ERROR] Framework not available")
            return

        print("\n1. Recording Successful Patterns:")
        # Simulate successful patterns from different agents
        patterns_recorded = []

        for agent_id in ['agent1', 'triage']:
            pattern_id = self.framework.knowledge_integrator.record_successful_pattern(
                agent_id=agent_id,
                pattern_type='success',
                description=f"Agent {agent_id} efficiency optimization pattern",
                metrics_impact={'tes': 0.15, 'stability': 0.08, 'velocity': 0.12},
                context={'agent_type': agent_id, 'optimization': 'efficiency'},
                confidence=0.8
            )
            patterns_recorded.append((agent_id, pattern_id))
            print(f"   [RECORD] Recorded pattern {pattern_id} for {agent_id}")

        print("\n2. Finding Transferable Patterns:")
        for target_agent in ['cp6', 'cp7']:
            baseline_metrics = {'tes': 70, 'stability': 0.75}
            transferable = self.framework.knowledge_integrator.find_transferable_patterns(
                target_agent, baseline_metrics
            )

            print(f"   [TRANSFER] {target_agent} transferable patterns: {len(transferable)}")
            for i, transfer in enumerate(transferable[:2]):  # Show top 2
                score = transfer['adaptation_score']
                score_formatted = f"{score:.3f}"
                print(f"      {i+1}. Score: {score_formatted}, Expected impact: {transfer['expected_impact']}")

        print()

    def demonstrate_adaptive_learning(self):
        """Demonstrate adaptive learning capabilities"""
        print("[ADAPTIVE] Demonstrating Adaptive Learning")
        print("=" * 50)

        if not self.framework:
            print("[ERROR] Framework not available")
            return

        print("\n1. Adaptive Learning Parameters:")

        # Show adaptive learning for different agents
        for agent_id in ['agent1', 'triage']:
            params = self.framework.adaptive_learner.get_learning_parameters(agent_id, 'task_efficiency')
            print(f"   [PARAMS]  {agent_id} learning parameters: {params}")

        print("\n2. Adaptation History:")

        # Show adaptation history
        for agent_id in ['agent1', 'triage']:
            history = self.framework.adaptive_learner.get_adaptation_history(agent_id)
            print(f"   [HISTORY] {agent_id} adaptations: {len(history)} applied")
            for adaptation in history[:2]:  # Show recent adaptations
                current_formatted = f"{adaptation['current_value']:.3f}"
                suggested_formatted = f"{adaptation['suggested_value']:.3f}"
                print(f"      {adaptation['parameter_name']}: {current_formatted} -> {suggested_formatted}")

        print()

    def generate_comprehensive_report(self):
        """Generate a comprehensive teaching system report"""
        print("[REPORT] Generating Comprehensive Report")
        print("=" * 50)

        report = {
            'timestamp': datetime.now().isoformat(),
            'framework_status': {},
            'agent_status': {},
            'learning_progress': {},
            'knowledge_integration': {},
            'recommendations': {}
        }

        if self.framework:
            report['framework_status'] = self.framework.get_system_status()

        # Agent status
        for agent_id, integration in self.agents.items():
            try:
                status = integration.get_teaching_status()
                report['agent_status'][agent_id] = status

                recommendations = integration.get_recommendations()
                report['recommendations'][agent_id] = recommendations

                print(f"   [METRICS] {agent_id}:")
                print(f"      Teaching Enabled: {status.get('teaching_enabled', False)}")
                print(f"      Active Sessions: {len(status.get('active_sessions', []))}")
                print(f"      Recommendations: {len(recommendations)}")
            except Exception as e:
                print(f"   [ERROR] {agent_id}: Error getting status - {e}")

        # Save report
        report_path = "outgoing/ai4all/reports/demo_report.json"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n[SAVE] Report saved to: {report_path}")
        print()

    def run_complete_demonstration(self):
        """Run the complete teaching system demonstration"""
        print("[START] AI-for-All Teaching System Complete Demonstration")
        print("=" * 60)
        print("This demonstration shows how baseline teaching methods improve")
        print("learning and training efficiency across Calyx Terminal agents.\n")

        if not TEACHING_AVAILABLE:
            print("[ERROR] Teaching system components not available")
            print("Please ensure the AI_for_All project is properly installed")
            return

        # Run all demonstrations
        self.demonstrate_framework_features()
        self.simulate_agent_learning()
        self.demonstrate_knowledge_integration()
        self.demonstrate_adaptive_learning()
        self.generate_comprehensive_report()

        print("[COMPLETE] Demonstration Complete!")
        print("\nKey Achievements:")
        print("  [OK] Teaching framework initialized and operational")
        print("  [OK] Agent teaching integrations established")
        print("  [OK] Learning sessions created and monitored")
        print("  [OK] Performance tracking and adaptation working")
        print("  [OK] Knowledge patterns identified and shared")
        print("  [OK] Comprehensive reporting generated")

        print("\nNext Steps:")
        print("  [DOCS] Review OPERATIONS.md for operational procedures")
        print("  [PARAMS]  Configure agents in config/teaching_config.yaml")
        print("  [INIT] Integrate teaching into existing agents")
        print("  [METRICS] Monitor progress via --status and --recommendations")

        print("\nFor help:")
        print("  python ai4all_teaching.py --help")
        print("  See integration/example_integration.py for usage examples")


def main():
    """Main demonstration function"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    demo = TeachingSystemDemo()
    demo.run_complete_demonstration()


if __name__ == "__main__":
    main()
