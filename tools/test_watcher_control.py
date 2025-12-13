from __future__ import annotations

import time
from tools.agent_control import post_command

if __name__ == "__main__":
    # Send a banner update and a toast to validate the control channel.
    p1 = post_command("set_banner", {"text": "Agent1 control channel: hello 👋", "color": "#1f6feb"}, sender="tester")
    print("Wrote:", p1)
    time.sleep(0.1)
    p2 = post_command("show_toast", {"text": "This is a test message from Agent1."}, sender="tester")
    print("Wrote:", p2)
    time.sleep(0.1)
    p3 = post_command("append_log", {"text": "Appended a line from test."}, sender="tester")
    print("Wrote:", p3)
