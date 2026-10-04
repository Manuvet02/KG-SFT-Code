# agent_client.py
import os
import sys

_mcp_dir = os.path.dirname(os.path.abspath(__file__))       
_app_dir = os.path.dirname(_mcp_dir)                  
_agent_dir = os.path.join(_app_dir, "agent")          

for _p in (_app_dir, _agent_dir):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from agent import SparqLLMAgent

agent = SparqLLMAgent()