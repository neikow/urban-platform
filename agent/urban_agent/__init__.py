"""Deployment agent: runs the platform's websites on one host, as the control plane asks.

See agent/README.md for the protocol and how to install it.
"""

import os

VERSION = os.environ.get("AGENT_VERSION", "dev")
