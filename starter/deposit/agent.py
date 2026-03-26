import os

from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService

from toolbox_core import ToolboxSyncClient

# Configure short-term session to use the in-memory service
session_service = InMemorySessionService()

# Read the instructions from a file in the same
# directory as this agent.py file.
script_dir = os.path.dirname(os.path.abspath(__file__))
instruction_file_path = os.path.join(script_dir, "agent-prompt.txt")
with open(instruction_file_path, "r") as f:
  instruction = f.read()

# Set up the tools that we will be using for the root agent
toolbox_url = os.environ.get("TOOLBOX_URL", "http://127.0.0.1:5000")
print(f"Connecting to Toolbox at {toolbox_url}")
db_client = ToolboxSyncClient(toolbox_url)
tools = [
  db_client.load_tool("get-account-balance"),
  db_client.load_tool("get-recent-transactions"),
  db_client.load_tool("list-accounts"),
]

# Use the Gemini 2.5 Flash model since it performs quickly
# and handles the processing well.
model = "gemini-2.5-flash"

# Create our agent
root_agent = Agent(
  name="deposit",
  model=model,
  instruction=instruction,
  tools=tools,
)