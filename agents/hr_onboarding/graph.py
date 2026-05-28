"""
HR Onboarding Agent — Graph Definition

Connects all 4 nodes in the correct order.

Flow:
parse_request → plan_provisioning →
generate_workflow → deploy_and_notify

Two separate entry points:
1. /hr/onboard — runs nodes 1, 2, 3
   Sends approval card to Slack
   
2. /hr/provision — runs node 4 only
   Called by n8n after manager approves
   Provisions all systems

"""

import logging
from langgraph.graph import StateGraph, END
from .state import HROnboardingState
from .nodes.parse_request import parse_request
from .nodes.plan_provisioning import plan_provisioning
from .nodes.generate_workflow import generate_workflow
from .nodes.deploy_and_notify import deploy_and_notify

logger = logging.getLogger(__name__)


def should_continue(state: HROnboardingState) -> str:
    """
    Edge condition — stop if any node failed.
    Same pattern as all other agents.
    """
    if state.get("error"):
        logger.warning(
            f"[{state.get('request_id')}] "
            f"Stopping — error: {state.get('error')}"
        )
        return "end"
    return "continue"


# ==========================================
# Graph 1 — Onboarding Plan
# Runs nodes 1, 2, 3
# Called by /hr/onboard endpoint
# ==========================================
onboarding_workflow = StateGraph(HROnboardingState)

onboarding_workflow.add_node(
    "parse_request", parse_request
)
onboarding_workflow.add_node(
    "plan_provisioning", plan_provisioning
)
onboarding_workflow.add_node(
    "generate_workflow", generate_workflow
)

onboarding_workflow.set_entry_point("parse_request")

onboarding_workflow.add_conditional_edges(
    "parse_request",
    should_continue,
    {
        "continue": "plan_provisioning",
        "end": END
    }
)

onboarding_workflow.add_conditional_edges(
    "plan_provisioning",
    should_continue,
    {
        "continue": "generate_workflow",
        "end": END
    }
)

onboarding_workflow.add_edge("generate_workflow", END)

hr_onboarding_graph = onboarding_workflow.compile()


# ==========================================
# Graph 2 — Provisioning
# Runs node 4 only
# Called by /hr/provision endpoint
# Triggered by n8n after manager approves
# ==========================================
provisioning_workflow = StateGraph(HROnboardingState)

provisioning_workflow.add_node(
    "deploy_and_notify", deploy_and_notify
)

provisioning_workflow.set_entry_point("deploy_and_notify")
provisioning_workflow.add_edge("deploy_and_notify", END)

hr_provisioning_graph = provisioning_workflow.compile()

logger.info(
    "HR Onboarding graphs compiled successfully"
)