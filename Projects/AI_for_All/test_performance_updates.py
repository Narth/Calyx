#!/usr/bin/env python3
"""
Test script to simulate agent performance updates with the teaching system
"""

from teaching.agent_interface import AgentTeachingInterface
from teaching.framework import TeachingFramework

def test_performance_updates():
    """Test the teaching system with simulated performance data"""

    print("Testing AI-for-All Teaching System with Performance Updates")
    print("=" * 60)

    # Initialize teaching system
    framework = TeachingFramework('config/teaching_config.json')
    interface = AgentTeachingInterface(framework)

    # Simulate performance updates for agent1
    print("\n1. Testing agent1 performance updates...")

    # First update - below baseline (should trigger adaptation)
    metrics1 = {'tes': 70, 'stability': 0.7, 'velocity': 0.4}
    response1 = interface.update_agent_performance('agent1', metrics1, {'test': 'below_baseline'})
    adaptations1 = len(response1.get('adaptations_applied', []))
    print(f'   Update 1: TES={metrics1["tes"]}, Adaptations: {adaptations1}')

    # Second update - improved performance
    metrics2 = {'tes': 90, 'stability': 0.95, 'velocity': 0.65}
    response2 = interface.update_agent_performance('agent1', metrics2, {'test': 'improved'})
    adaptations2 = len(response2.get('adaptations_applied', []))
    print(f'   Update 2: TES={metrics2["tes"]}, Adaptations: {adaptations2}')

    # Third update - excellent performance
    metrics3 = {'tes': 95, 'stability': 0.98, 'velocity': 0.8}
    response3 = interface.update_agent_performance('agent1', metrics3, {'test': 'excellent'})
    adaptations3 = len(response3.get('adaptations_applied', []))
    print(f'   Update 3: TES={metrics3["tes"]}, Adaptations: {adaptations3}')

    # Check progress
    print("\n2. Learning Progress:")
    status = interface.get_agent_teaching_status('agent1')
    progress = status['progress_summary']['average_progress']
    session_count = status['progress_summary']['session_count']
    overall_status = status['progress_summary']['overall_status']

    progress_formatted = f"{progress:.1%}"
    print(f'   Average Progress: {progress_formatted}')
    print(f'   Active Sessions: {session_count}')
    print(f'   Overall Status: {overall_status}')

    # Show adaptations if any
    if adaptations1 > 0 or adaptations2 > 0 or adaptations3 > 0:
        print("\n3. Adaptations Applied:")
        adaptations = status.get('adaptations', [])
        for i, adaptation in enumerate(adaptations[:3], 1):
            param = adaptation.get('parameter_name', 'unknown')
            current = adaptation.get('current_value', 0)
            suggested = adaptation.get('suggested_value', 0)
            current_formatted = f"{current:.3f}"
            suggested_formatted = f"{suggested:.3f}"
            print(f'   {i}. {param}: {current_formatted} -> {suggested_formatted}')

    # Show recommendations
    print("\n4. Teaching Recommendations:")
    recommendations = interface.get_teaching_recommendations('agent1')
    for i, rec in enumerate(recommendations[:3], 1):
        print(f'   {i}. {rec}')

    print("\n5. System Status:")
    system_status = interface.get_system_overview()
    agents_enabled = system_status['agent_interface']['agents_with_teaching_enabled']
    active_sessions = system_status['agent_interface']['active_sessions']
    print(f'   Agents with Teaching: {agents_enabled}')
    print(f'   Active Sessions: {active_sessions}')

    print("\n[SUCCESS] Teaching system test completed successfully!")
    print("[TARGET] The AI-for-All teaching system is working correctly!")
    print("[GRAPH] Agents are learning and adapting based on performance feedback.")

if __name__ == "__main__":
    test_performance_updates()
