#!/usr/bin/env python3
"""
Test script to verify onboarding dialog checkbox/button behavior.
"""
import sys

try:
    from PySide6.QtWidgets import QApplication, QDialog
    from station_calyx_desktop.dialogs import OnboardingDialog
except ImportError as e:
    print(f"Import error: {e}")
    print("PySide6 may not be installed. Skipping GUI test.")
    sys.exit(0)

def test_onboarding_dialog():
    """Test that checkbox toggling enables/disables continue button."""
    app = QApplication.instance() or QApplication(sys.argv)
    
    dialog = OnboardingDialog()
    
    # Initial state: checkbox unchecked, button disabled
    print(f"Initial checkbox state: {dialog._ack_checkbox.isChecked()}")
    print(f"Initial button enabled: {dialog._continue_btn.isEnabled()}")
    
    assert not dialog._ack_checkbox.isChecked(), "Checkbox should be unchecked initially"
    assert not dialog._continue_btn.isEnabled(), "Button should be disabled initially"
    
    # Simulate checking the checkbox
    dialog._ack_checkbox.setChecked(True)
    
    print(f"After check - checkbox state: {dialog._ack_checkbox.isChecked()}")
    print(f"After check - button enabled: {dialog._continue_btn.isEnabled()}")
    
    assert dialog._ack_checkbox.isChecked(), "Checkbox should be checked"
    assert dialog._continue_btn.isEnabled(), "Button should be enabled after checking"
    
    # Simulate unchecking the checkbox
    dialog._ack_checkbox.setChecked(False)
    
    print(f"After uncheck - checkbox state: {dialog._ack_checkbox.isChecked()}")
    print(f"After uncheck - button enabled: {dialog._continue_btn.isEnabled()}")
    
    assert not dialog._ack_checkbox.isChecked(), "Checkbox should be unchecked"
    assert not dialog._continue_btn.isEnabled(), "Button should be disabled after unchecking"
    
    # Test QDialog.Accepted constant access
    print(f"\nVerifying QDialog constants...")
    print(f"QDialog.Accepted = {QDialog.Accepted}")
    print(f"QDialog.Rejected = {QDialog.Rejected}")
    
    print("\n? All tests passed! Checkbox/button synchronization working correctly.")
    print("? QDialog.Accepted/Rejected constants accessible.")
    return True

if __name__ == "__main__":
    success = test_onboarding_dialog()
    sys.exit(0 if success else 1)
