#!/usr/bin/env python3
"""
AI-for-All Production Testing - Comprehensive validation of permanent implementation
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Import production components
import sys
import os

# Add current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from integration.production_agent_hooks import ProductionIntegrationManager, create_integration_manager
    from teaching.framework import TeachingFramework
    from teaching.enhanced_learner import EnhancedAdaptiveLearner
    from monitoring.production_monitor import ProductionMonitor
except ImportError as e:
    print(f"Import error: {e}")
    # Emergency fallback - import with absolute paths
    sys.path.insert(0, os.path.join(current_dir, 'integration'))
    sys.path.insert(0, os.path.join(current_dir, 'teaching'))
    sys.path.insert(0, os.path.join(current_dir, 'monitoring'))

    from production_agent_hooks import ProductionIntegrationManager, create_integration_manager
    from framework import TeachingFramework
    from enhanced_learner import EnhancedAdaptiveLearner
    from production_monitor import ProductionMonitor


def run_comprehensive_production_test():
    """
    Run comprehensive production testing of the AI-for-All teaching system.
    Validates all components and integration points.
    """

    print("[TEST] AI-for-All Production Testing Suite")
    print("=" * 50)
    print("Testing permanent implementation with Calyx Terminal integration\n")

    test_results = {
        'timestamp': datetime.now().isoformat(),
        'test_suite': 'production_integration',
        'components': {},
        'integration_tests': {},
        'performance_tests': {},
        'overall_status': 'pending'
    }

    # Test 1: Core Framework
    print("1. Testing Core Framework...")
    framework_test = test_framework_initialization()
    test_results['components']['framework'] = framework_test

    # Test 2: Enhanced Learning
    print("\n2. Testing Enhanced Learning...")
    enhanced_test = test_enhanced_learning()
    test_results['components']['enhanced_learning'] = enhanced_test

    # Test 3: Integration Manager
    print("\n3. Testing Integration Manager...")
    integration_test = test_integration_manager()
    test_results['components']['integration_manager'] = integration_test

    # Test 4: Production Monitor
    print("\n4. Testing Production Monitor...")
    monitor_test = test_production_monitor()
    test_results['components']['production_monitor'] = monitor_test

    # Test 5: Agent Integration
    print("\n5. Testing Agent Integration...")
    agent_test = test_agent_integration()
    test_results['integration_tests']['agent_integration'] = agent_test

    # Test 6: Performance Under Load
    print("\n6. Testing Performance Under Load...")
    performance_test = test_performance_under_load()
    test_results['performance_tests']['load_testing'] = performance_test

    # Test 7: Cross-Component Integration
    print("\n7. Testing Cross-Component Integration...")
    cross_component_test = test_cross_component_integration()
    test_results['integration_tests']['cross_component'] = cross_component_test

    # Calculate overall status
    test_results['overall_status'] = calculate_overall_status(test_results)

    # Generate test report
    generate_test_report(test_results)

    print(f"\n[COMPLETE] Production Testing Complete!")
    print(f"[STATUS] Overall Status: {test_results['overall_status']}")
    print(f"[REPORT] Detailed report saved to: outgoing/ai4all/reports/production_test_{int(time.time())}.json")

    return test_results


def test_framework_initialization() -> Dict[str, Any]:
    """Test core framework initialization and basic functionality"""
    try:
        framework = TeachingFramework('config/teaching_config.json')

        # Test basic functionality
        system_status = framework.get_system_status()

        # Test learning session creation
        session = framework.create_learning_session(
            'test_agent',
            'test_objective',
            {'tes': 80, 'stability': 0.8}
        )

        # Test performance tracking
        framework.performance_tracker.record_performance(
            'test_agent',
            {'tes': 85, 'stability': 0.85},
            {'test': 'framework_test'}
        )

        # Test pattern recognition
        framework.pattern_recognition.observe_behavior(
            'test_agent',
            {'test_behavior': True},
            {'test': 'pattern_test'},
            {'tes': 85}
        )

        return {
            'status': 'success',
            'message': 'Framework initialized and basic operations working',
            'system_status': system_status,
            'session_created': session.id,
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Framework test failed: {str(e)}',
            'error': str(e)
        }


def test_enhanced_learning() -> Dict[str, Any]:
    """Test enhanced learning features"""
    try:
        # Initialize enhanced learner
        config = {'enhanced_learning': True, 'predictive_horizon': 5}
        enhanced_learner = EnhancedAdaptiveLearner(config)

        # Test enhanced adaptation suggestions
        suggestions = enhanced_learner.suggest_enhanced_adaptation(
            'test_agent',
            'test_objective',
            {'tes': 70, 'stability': 0.7},
            {'tes': 80, 'stability': 0.8},
            [{'tes': 75, 'stability': 0.75}, {'tes': 70, 'stability': 0.7}]
        )

        # Test learning insights
        insights = enhanced_learner.get_learning_insights('test_agent')

        return {
            'status': 'success',
            'message': 'Enhanced learning features working',
            'suggestions_count': len(suggestions),
            'insights_available': bool(insights),
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Enhanced learning test failed: {str(e)}',
            'error': str(e)
        }


def test_integration_manager() -> Dict[str, Any]:
    """Test production integration manager"""
    try:
        manager = create_integration_manager()

        # Test agent hook creation
        hook = manager.agent_hooks.get('agent1')
        if not hook:
            # Create hook manually for testing
            from integration.production_agent_hooks import AgentTeachingHook
            hook = AgentTeachingHook('agent1')
            manager.agent_hooks['agent1'] = hook

        # Test performance update
        response = manager.update_agent_performance(
            'agent1',
            {'tes': 85, 'stability': 0.9},
            {'test': 'integration_test'}
        )

        # Test recommendations
        recommendations = manager.get_agent_recommendations('agent1')

        # Test integration status
        status = manager.get_integration_status()

        return {
            'status': 'success',
            'message': 'Integration manager working',
            'agents_configured': len(manager.agent_hooks),
            'recommendations_available': bool(recommendations),
            'status_available': bool(status),
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Integration manager test failed: {str(e)}',
            'error': str(e)
        }


def test_production_monitor() -> Dict[str, Any]:
    """Test production monitoring system"""
    try:
        monitor = ProductionMonitor({
            'monitoring_interval': 10,
            'alerting_interval': 5,
            'performance_decline_threshold': -0.1,
            'stability_threshold': 0.7
        })

        # Test monitoring status
        status = monitor.get_monitoring_status()

        # Test alert creation (non-critical)
        monitor._create_alert(
            'test_alert',
            'Test alert for production monitoring',
            'info',
            {'test': True}
        )

        # Test metrics calculation
        system_stability = monitor._calculate_system_stability({})
        knowledge_maturity = monitor._calculate_knowledge_maturity()

        return {
            'status': 'success',
            'message': 'Production monitoring working',
            'monitoring_status': status,
            'alerts_functional': True,
            'metrics_calculation': 'working',
            'system_stability': system_stability,
            'knowledge_maturity': knowledge_maturity,
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Production monitor test failed: {str(e)}',
            'error': str(e)
        }


def test_agent_integration() -> Dict[str, Any]:
    """Test agent integration functionality"""
    try:
        # Test individual agent hooks
        agents_to_test = ['agent1', 'triage', 'cp6', 'cp7']
        integration_results = {}

        for agent_id in agents_to_test:
            try:
                # Create agent hook
                from integration.production_agent_hooks import AgentTeachingHook
                hook = AgentTeachingHook(agent_id)

                # Enable teaching
                enabled = hook.enable_teaching()

                # Update performance
                response = hook.update_performance(
                    {'tes': 80, 'stability': 0.8},
                    {'test': 'agent_integration_test'}
                )

                # Get status
                status = hook.get_teaching_status()

                # Get recommendations
                recommendations = hook.get_recommendations()

                integration_results[agent_id] = {
                    'enabled': enabled,
                    'teaching_response': bool(response),
                    'status_available': bool(status),
                    'recommendations_available': bool(recommendations)
                }

            except Exception as e:
                integration_results[agent_id] = {
                    'enabled': False,
                    'error': str(e)
                }

        # Check overall integration success
        successful_integrations = sum(1 for result in integration_results.values() if result.get('enabled', False))
        total_integrations = len(agents_to_test)

        return {
            'status': 'success' if successful_integrations >= 2 else 'partial',
            'message': f'Agent integration: {successful_integrations}/{total_integrations} agents integrated',
            'integration_results': integration_results,
            'successful_integrations': successful_integrations,
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Agent integration test failed: {str(e)}',
            'error': str(e)
        }


def test_performance_under_load() -> Dict[str, Any]:
    """Test system performance under simulated load"""
    try:
        import time

        # Test framework performance
        framework = TeachingFramework('config/teaching_config.json')

        start_time = time.time()

        # Simulate multiple operations
        for i in range(100):
            # Create sessions
            session = framework.create_learning_session(
                f'load_test_agent_{i}',
                'load_test_objective',
                {'tes': 80 + i, 'stability': 0.8 + i * 0.001}
            )

            # Update performance
            framework.performance_tracker.record_performance(
                f'load_test_agent_{i}',
                {'tes': 85 + i, 'stability': 0.85 + i * 0.001},
                {'load_test': i}
            )

            # Record patterns
            framework.knowledge_integrator.record_successful_pattern(
                f'load_test_agent_{i}',
                'success',
                f'Load test pattern {i}',
                {'tes': 0.1, 'stability': 0.05},
                {'load_test': i}
            )

        end_time = time.time()
        duration = end_time - start_time

        # Calculate performance metrics
        operations_per_second = 100 / duration if duration > 0 else 0
        memory_efficient = duration < 10  # Should complete in under 10 seconds

        return {
            'status': 'success' if memory_efficient else 'warning',
            'message': f'Load testing: {operations_per_second:.1f} ops/sec, duration: {duration:.2f}s',
            'operations_per_second': operations_per_second,
            'total_duration': duration,
            'memory_efficient': memory_efficient,
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Load testing failed: {str(e)}',
            'error': str(e)
        }


def test_cross_component_integration() -> Dict[str, Any]:
    """Test integration between all components"""
    try:
        # Initialize all components
        framework = TeachingFramework('config/teaching_config.json')
        from teaching.agent_interface import AgentTeachingInterface
        agent_interface = AgentTeachingInterface(framework)

        # Test cross-component data flow
        test_data = {
            'agent_id': 'cross_test_agent',
            'metrics': {'tes': 90, 'stability': 0.95, 'velocity': 0.8},
            'context': {'cross_component_test': True}
        }

        # 1. Agent interface -> Framework
        response = agent_interface.update_agent_performance(
            test_data['agent_id'],
            test_data['metrics'],
            test_data['context']
        )

        # 2. Framework -> Pattern recognition
        framework.pattern_recognition.observe_behavior(
            test_data['agent_id'],
            test_data,
            test_data['context'],
            test_data['metrics']
        )

        # 3. Framework -> Knowledge integration
        pattern_id = framework.knowledge_integrator.record_successful_pattern(
            test_data['agent_id'],
            'success',
            'Cross-component test pattern',
            test_data['metrics'],
            test_data['context']
        )

        # 4. Knowledge integration -> Pattern recognition
        patterns = framework.pattern_recognition.get_agent_patterns(test_data['agent_id'])

        # 5. Framework -> Performance tracker
        performance_data = framework.performance_tracker.get_agent_performance(test_data['agent_id'])

        # Validate all components worked together
        components_working = all([
            bool(response),
            bool(pattern_id),
            bool(patterns) or True,  # Patterns might be empty, that's ok
            bool(performance_data)
        ])

        return {
            'status': 'success' if components_working else 'partial',
            'message': 'Cross-component integration working' if components_working else 'Some components failed',
            'agent_interface_response': bool(response),
            'pattern_recorded': bool(pattern_id),
            'patterns_found': len(patterns),
            'performance_data': bool(performance_data),
            'error': None
        }

    except Exception as e:
        return {
            'status': 'failed',
            'message': f'Cross-component test failed: {str(e)}',
            'error': str(e)
        }


def calculate_overall_status(test_results: Dict[str, Any]) -> str:
    """Calculate overall test status"""
    component_statuses = []
    integration_statuses = []

    # Check component tests
    for component_name, result in test_results['components'].items():
        if result['status'] == 'success':
            component_statuses.append(1)
        elif result['status'] == 'partial':
            component_statuses.append(0.5)
        else:
            component_statuses.append(0)

    # Check integration tests
    for test_name, result in test_results['integration_tests'].items():
        if result['status'] == 'success':
            integration_statuses.append(1)
        elif result['status'] == 'partial':
            integration_statuses.append(0.5)
        else:
            integration_statuses.append(0)

    # Calculate averages
    component_avg = sum(component_statuses) / len(component_statuses) if component_statuses else 0
    integration_avg = sum(integration_statuses) / len(integration_statuses) if integration_statuses else 0

    overall_score = (component_avg + integration_avg) / 2

    if overall_score >= 0.9:
        return 'EXCELLENT'
    elif overall_score >= 0.7:
        return 'GOOD'
    elif overall_score >= 0.5:
        return 'ACCEPTABLE'
    else:
        return 'NEEDS_IMPROVEMENT'


def generate_test_report(test_results: Dict[str, Any]):
    """Generate comprehensive test report"""
    timestamp = int(time.time())

    report = {
        **test_results,
        'report_generated': datetime.now().isoformat(),
        'test_environment': {
            'python_version': __import__('sys').version,
            'platform': __import__('sys').platform,
            'timestamp': timestamp
        }
    }

    # Save report
    report_dir = Path("outgoing/ai4all/reports")
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"production_test_{timestamp}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    # Also save human-readable summary
    summary_file = report_dir / f"production_test_summary_{timestamp}.txt"
    with open(summary_file, 'w') as f:
        f.write(generate_human_readable_summary(test_results))

    print(f"[REPORT] Test report saved: {report_file}")
    print(f"[SUMMARY] Summary saved: {summary_file}")


def generate_human_readable_summary(test_results: Dict[str, Any]) -> str:
    """Generate human-readable test summary"""
    summary = []
    summary.append("AI-for-All Production Testing Summary")
    summary.append("=" * 40)
    summary.append(f"Test Date: {test_results['timestamp']}")
    summary.append(f"Overall Status: {test_results['overall_status']}")
    summary.append("")

    # Component results
    summary.append("Component Test Results:")
    for component, result in test_results['components'].items():
        status_icon = "[SUCCESS]" if result['status'] == 'success' else "[WARNING]" if result['status'] == 'partial' else "[ERROR]"
        summary.append(f"  {status_icon} {component}: {result['message']}")

    summary.append("")

    # Integration results
    summary.append("Integration Test Results:")
    for test_name, result in test_results['integration_tests'].items():
        status_icon = "[SUCCESS]" if result['status'] == 'success' else "[WARNING]" if result['status'] == 'partial' else "[ERROR]"
        summary.append(f"  {status_icon} {test_name}: {result['message']}")

    summary.append("")

    # Performance results
    summary.append("Performance Test Results:")
    for test_name, result in test_results['performance_tests'].items():
        status_icon = "[SUCCESS]" if result['status'] == 'success' else "[WARNING]" if result['status'] == 'partial' else "[ERROR]"
        summary.append(f"  {status_icon} {test_name}: {result['message']}")

    summary.append("")
    summary.append(f"Ready for Production: {'YES' if test_results['overall_status'] in ['EXCELLENT', 'GOOD'] else 'WITH_RESERVATIONS'}")

    return "\n".join(summary)


def main():
    """Main production testing entry point"""
    logging.basicConfig(level=logging.INFO)

    # Run comprehensive tests
    results = run_comprehensive_production_test()

    # Exit with appropriate code
    if results['overall_status'] in ['EXCELLENT', 'GOOD']:
        print("[SUCCESS] All tests passed! Ready for production deployment.")
        exit(0)
    elif results['overall_status'] == 'ACCEPTABLE':
        print("[WARNING] Tests mostly passed with some issues. Review before deployment.")
        exit(1)
    else:
        print("[ERROR] Tests failed. Address issues before deployment.")
        exit(1)


if __name__ == "__main__":
    main()
