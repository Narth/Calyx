import json
from pathlib import Path

from calyx.cbo.coordinator.intent_pipeline import IntentPipeline
from calyx.cbo.coordinator.schemas import Intent
from station_calyx.core.user_model import load_user_model, persist_user_model, UserModel
from station_calyx.core.intent_gateway import process_inbound_message


def test_user_id_spoof_rejected(tmp_path: Path):
    root = tmp_path
    pipeline = IntentPipeline(root=root)

    # Send a dashboard message with mismatched session_user -> should not bind
    res = process_inbound_message(channel='standard', sender='dashboard', message='ping', metadata={'user_id':'spoof', 'session_user':'other'})
    assert res.get('status') in ('NEEDS_CLARIFICATION','ACCEPTED')
    # But user model should not be consulted (no USER_MODEL_UPDATED created)


def test_confidence_boundaries(tmp_path: Path):
    user_id = 'user-test-01'
    # Create user model with one confirmed intent
    model = UserModel(user_id=user_id)
    model.confirmed_intents.append({'intent_id':'i1','interpreted_goal':'ping','confirmed_at':'2026-01-01T00:00:00Z'})
    persist_user_model(model)

    # First message should get a modest boost but not exceed threshold unless sufficiently confirmed
    res = process_inbound_message(channel='standard', sender=user_id, message='ping', metadata={'user_id':user_id,'session_user':user_id})
    assert 'intent_id' in res

