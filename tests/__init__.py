# -*- coding: utf-8 -*-
"""Test package for the agent_system project."""

import os

# Unit tests must never reach a real speech service, whatever the developer's
# .env says (an explicit environment value wins over .env).
os.environ["AGENT_TTS"] = "off"
