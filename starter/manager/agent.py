import logging
import os
from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.sessions import InMemorySessionService

# Configure short-term session to use the in-memory service
session_service = InMemorySessionService()

# Read the instructions from a file in the same
# directory as this agent.py file.
script_dir = os.path.dirname(os.path.abspath(__file__))
instruction_file_path = os.path.join(script_dir, "agent-prompt.txt")
with open(instruction_file_path, "r") as f:
  instruction = f.read()

# Set up the tools that we will be using for the root agent
tools = []

# Base URL for A2A agents (can be configured via environment variable)
base_url = os.environ.get("A2A_BASE_URL", "http://localhost:8000")

# Set up other agents that we can delegate to via A2A
deposit_agent = RemoteA2aAgent(
  name="deposit_agent",
  description="Handles questions about deposit accounts including checking and savings. Can provide account balances, transaction history, and list accounts.",
  agent_card_url=f"{base_url}/a2a/deposit/{AGENT_CARD_WELL_KNOWN_PATH}",
)

loan_agent = RemoteA2aAgent(
  name="loan_agent",
  description="Handles questions about loans including auto loans, personal loans, and mortgages. Can provide loan balances, payment details, loan terms, and process loan applications.",
  agent_card_url=f"{base_url}/a2a/loan/{AGENT_CARD_WELL_KNOWN_PATH}",
)

sub_agents = [
  deposit_agent,
  loan_agent,
]

# Use the Gemini 2.5 Flash model since it performs quickly
# and handles the processing well.
model = "gemini-2.5-flash"

# Create our agent
root_agent = Agent(
  name="manager",
  model=model,
  instruction=instruction,
  tools=tools,
  sub_agents=sub_agents,
)
