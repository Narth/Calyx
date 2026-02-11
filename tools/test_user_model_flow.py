"""Test UserModel confirmation feedback loop

Demonstrates:
 - First-time intent requires clarification
 - Confirmed intent increases confidence for subsequent messages
 - Rejected interpretation lowers future confidence

Run:
    python tools/test_user_model_flow.py
"""
from station_calyx.core.intent_gateway import process_inbound_message, echo_chain_info
from station_calyx.core.user_model import load_user_model, record_confirmation, record_rejection
from tools.svf_channels import send_message

user_id = "user-test-01"

# 1) First-time message -> should need clarification
res1 = process_inbound_message(channel='standard', sender=user_id, message='ping', metadata={'user_id': user_id})
print('First message result:', res1)

# Simulate user confirming the interpretation
if res1.get('status') == 'NEEDS_CLARIFICATION':
    # Simulate user confirming the intent via CLI/dashboard
    record_confirmation(user_id, res1.get('intent_id'), 'ping')
    print('Recorded confirmation')

# 2) Second message -> should be accepted (higher confidence)
res2 = process_inbound_message(channel='standard', sender=user_id, message='ping', metadata={'user_id': user_id})
print('Second message result:', res2)

# 3) Simulate a rejection for a different interpretation
res3 = process_inbound_message(channel='standard', sender=user_id, message='order now', metadata={'user_id': user_id})
print('Third message result:', res3)
if res3.get('status') == 'NEEDS_CLARIFICATION':
    record_rejection(user_id, res3.get('intent_id'), 'order now')
    print('Recorded rejection')

# 4) Re-sending rejected interpretation -> lower confidence expected
res4 = process_inbound_message(channel='standard', sender=user_id, message='order now', metadata={'user_id': user_id})
print('Fourth message result:', res4)

# Print current UserModel
model = load_user_model(user_id)
print('UserModel:', model.to_dict())
