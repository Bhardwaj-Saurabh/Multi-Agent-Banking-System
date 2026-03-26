import logging
import os
from typing import AsyncGenerator

from google.adk.agents import SequentialAgent, ParallelAgent, LlmAgent, BaseAgent, InvocationContext
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH
from google.adk.events import Event, EventActions
from google.genai.types import Content, Part
from google.adk.tools import load_artifacts

from toolbox_core import ToolboxSyncClient

def load_instructions(prompt_file: str):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    instruction_file_path = os.path.join(script_dir, prompt_file)
    with open(instruction_file_path, "r") as f:
        return f.read()

# Model to use for all LLM agents
model = "gemini-2.5-flash"

# Base URL for A2A agents
base_url = os.environ.get("A2A_BASE_URL", "http://localhost:8000")

# GCS bucket for policy and customer documents
gcs_bucket = os.environ.get("GCS_BUCKET", "")

# Set up toolbox client for loan tools
toolbox_url = os.environ.get("TOOLBOX_URL", "http://127.0.0.1:5000")
db_client = ToolboxSyncClient(toolbox_url)

# ============================================================================
# Sub-Agent 1: Get Requested Loan Value
# Extracts loan type and amount from customer request
# ============================================================================
get_requested_value_agent = LlmAgent(
    name="get_requested_value_agent",
    model=model,
    instruction=load_instructions("loan-request-prompt.txt"),
    output_key="loan_request",
    output_schema={
        "type": "object",
        "properties": {
            "loan_type": {"type": "string"},
            "amount": {"type": "number"}
        },
        "required": ["loan_type", "amount"]
    },
)

# ============================================================================
# Sub-Agent 2: Get Outstanding Balance
# Gets total outstanding balance from all loans
# ============================================================================
outstanding_balance_agent = LlmAgent(
    name="outstanding_balance_agent",
    model=model,
    instruction=load_instructions("outstanding-balance-prompt.txt"),
    tools=[db_client.load_tool("get-total-outstanding-balance")],
    output_key="outstanding_balance",
    output_schema={
        "type": "object",
        "properties": {
            "total_outstanding_balance": {"type": "number"}
        },
        "required": ["total_outstanding_balance"]
    },
)

# ============================================================================
# Sub-Agent 3: Policy Agent
# Loads policy PDF from GCS and extracts criteria
# ============================================================================
policy_agent_instruction = """You are analyzing the loan policy document to extract the criteria for a specific loan type and amount.

Based on the loan_request in the state (loan_type and amount), find the matching criteria from the policy document.

The policy document defines different debt-to-equity ratios and minimum customer ratings for different loan types and amounts.

Loan type mappings:
- "auto" -> Auto Loans
- "personal" -> Personal Loans
- "recreational" -> Recreational Vehicles
- "home_improvement" -> Home Improvement
- "mortgage" -> Use Home Improvement criteria as fallback

Output the criteria in the following JSON format:
{
  "debt_to_equity_ratio": <number>,
  "required_rating": "<rating>"
}

Rating levels from best to worst: excellent, great, good, fair, poor
"""

policy_agent = LlmAgent(
    name="policy_agent",
    model=model,
    instruction=policy_agent_instruction,
    tools=[load_artifacts],
    output_key="policy_criteria",
    output_schema={
        "type": "object",
        "properties": {
            "debt_to_equity_ratio": {"type": "number"},
            "required_rating": {"type": "string"}
        },
        "required": ["debt_to_equity_ratio", "required_rating"]
    },
)

# ============================================================================
# Sub-Agent 4: Total Value Agent (Custom - NOT LLM)
# Computes minimum required equity based on debt and debt-to-equity ratio
# Formula: minimum_equity = (outstanding_balance + requested_amount) / debt_to_equity_ratio
# ============================================================================
class TotalValueAgent(BaseAgent):
    """
    Custom agent that computes the minimum required equity.
    This is NOT an LLM agent - it performs pure mathematical computation.
    """

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # Get values from state
        state = ctx.session.state

        # Get loan request details
        loan_request = state.get("loan_request", {})
        requested_amount = loan_request.get("amount", 0)

        # Get outstanding balance
        outstanding = state.get("outstanding_balance", {})
        total_outstanding = outstanding.get("total_outstanding_balance", 0)

        # Get policy criteria
        policy = state.get("policy_criteria", {})
        debt_to_equity_ratio = policy.get("debt_to_equity_ratio", 1)

        # Calculate total debt (existing + new loan)
        total_debt = total_outstanding + requested_amount

        # Calculate minimum required equity
        # minimum_equity = total_debt / debt_to_equity_ratio
        if debt_to_equity_ratio > 0:
            minimum_equity = total_debt / debt_to_equity_ratio
        else:
            minimum_equity = float('inf')

        # Store result in state
        result = {
            "total_debt": total_debt,
            "minimum_equity": minimum_equity
        }

        # Yield completion event
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"minimum_equity": result}),
            content=Content(parts=[Part(text=f"Calculated minimum equity requirement: ${minimum_equity:.2f}")])
        )

total_value_agent = TotalValueAgent(name="total_value_agent")

# ============================================================================
# Sub-Agent 5: Check Equity Agent
# Uses A2A to communicate with deposit agent to check minimum balance
# ============================================================================
deposit_a2a_agent = RemoteA2aAgent(
    name="deposit_agent",
    description="Handles questions about deposit accounts. Can check if total balance meets a minimum threshold.",
    agent_card_url=f"{base_url}/a2a/deposit/{AGENT_CARD_WELL_KNOWN_PATH}",
)

check_equity_agent = LlmAgent(
    name="check_equity_agent",
    model=model,
    instruction=load_instructions("check-equity-prompt.txt"),
    sub_agents=[deposit_a2a_agent],
    output_key="equity_check",
    output_schema={
        "type": "object",
        "properties": {
            "meets_equity_requirement": {"type": "boolean"}
        },
        "required": ["meets_equity_requirement"]
    },
)

# ============================================================================
# Sub-Agent 6: User Profile Agent
# Loads customer profile PDF from GCS and determines rating
# ============================================================================
user_profile_agent = LlmAgent(
    name="user_profile_agent",
    model=model,
    instruction=load_instructions("user-profile-base-prompt.txt"),
    tools=[load_artifacts],
    output_key="user_profile",
    output_schema={
        "type": "object",
        "properties": {
            "customer_rating": {"type": "string"}
        },
        "required": ["customer_rating"]
    },
)

# ============================================================================
# Sub-Agent 7: Approval Decision Agent
# Makes final approval decision based on all gathered information
# ============================================================================
approval_decision_agent = LlmAgent(
    name="approval_decision_agent",
    model=model,
    instruction=load_instructions("approval-report-prompt.txt"),
    output_key="approval_decision",
)

# ============================================================================
# Orchestration: Parallel and Sequential Agents
# ============================================================================

# Phase 1: Get loan request details (must be first)
phase1_agent = get_requested_value_agent

# Phase 2: Run in parallel - outstanding balance, policy lookup, and user profile
# These can all run simultaneously since they don't depend on each other
phase2_parallel_agent = ParallelAgent(
    name="phase2_parallel_data_gathering",
    sub_agents=[
        outstanding_balance_agent,
        policy_agent,
        user_profile_agent,
    ],
)

# Phase 3: Calculate minimum equity (needs outstanding balance and policy)
phase3_agent = total_value_agent

# Phase 4: Check equity with deposit agent (needs minimum equity)
phase4_agent = check_equity_agent

# Phase 5: Make final decision
phase5_agent = approval_decision_agent

# ============================================================================
# Main Loan Approval Agent - Sequential orchestration
# ============================================================================
loan_approval_agent = SequentialAgent(
    name="loan_approval_agent",
    description="Processes loan applications by evaluating customer equity, loan history, and policy criteria to approve or reject loan requests.",
    sub_agents=[
        phase1_agent,           # Get loan request
        phase2_parallel_agent,  # Gather data in parallel
        phase3_agent,           # Calculate minimum equity
        phase4_agent,           # Check equity with deposit agent
        phase5_agent,           # Make decision
    ],
)
