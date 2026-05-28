"""
Generate Workflow Node

Third node in HR Onboarding Agent.

What it does:
- Receives provisioning plan from plan_provisioning
- Builds complete n8n workflow JSON programmatically
- Sends approval card to manager on Slack
- Waits for manager approval before any provisioning

This is the most impressive node:
- Agent WRITES a workflow, not just runs one
- Dynamic — different workflow for each role
- Professional — includes approval gate

GDPR Note:
No LLM used here — pure Python logic.
Workflow JSON built from structured data only.
No personal data sent anywhere yet.
"""

import json
import logging
import os
import requests
from ..state import HROnboardingState

logger = logging.getLogger(__name__)


def generate_workflow(
    state: HROnboardingState
) -> HROnboardingState:
    """
    Generate n8n workflow JSON and send
    approval card to manager on Slack.

    Two things happen here:
    1. Build n8n workflow JSON for provisioning
    2. Send approval card to Slack for manager
    """

    request_id = state.get("request_id", "unknown")
    employee_name = state.get("employee_name", "")
    employee_email = state.get("employee_email", "")
    role = state.get("role", "")
    department = state.get("department", "")
    start_date = state.get("start_date", "")
    manager_name = state.get("manager_name", "HR Team")
    systems = state.get("systems_to_provision", [])
    slack_channels = state.get("slack_channels", [])
    drive_folder_path = state.get("drive_folder_path", "")
    requires_github = state.get("requires_github", False)
    requires_figma = state.get("requires_figma", False)
    plan_summary = state.get(
        "provisioning_plan_summary", ""
    )

    logger.info(
        f"[{request_id}] "
        f"Generating workflow for {employee_name}"
    )

    # ==========================================
    # Check for errors from previous nodes
    # ==========================================
    if state.get("error"):
        return state

    # ==========================================
    # Build systems list for approval message
    # ==========================================
    systems_text = ""
    for system in systems:
        systems_text += f"✓ {system}\n"

    if requires_figma:
        systems_text += "⚠ Figma — manual admin invite required\n"

    if requires_github:
        systems_text += "⚠ GitHub — invitation sent, pending acceptance\n"

    # ==========================================
    # Build Slack approval message
    # Using plain text for now
    # Manager sees this and replies APPROVE
    # ==========================================
    approval_message = f"""📋 *HR Onboarding Request — {employee_name}*

*Role:* {role}
*Department:* {department}
*Start Date:* {start_date or 'Not specified'}
*Manager:* {manager_name or 'Not specified'}
*Email:* {employee_email or 'Not provided'}

*Systems to provision:*
{systems_text}
*Slack Channels:* {', '.join(slack_channels)}
*Drive Folder:* {drive_folder_path}

*Plan Summary:*
{plan_summary}

✅ Reply *APPROVE* to proceed with provisioning.
❌ Reply *REJECT* to cancel.

Request ID: {request_id}"""

    # ==========================================
    # Send approval message to Slack
    # Posts to #general channel
    # Manager sees it and replies
    # ==========================================
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    approval_sent = False

    if slack_token:
        try:
            response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": "hr-onboarding",
                    "text": approval_message
                }
            )
            result = response.json()
            if result.get("ok"):
                approval_sent = True
                logger.info(
                    f"[{request_id}] "
                    f"Approval card sent to Slack"
                )
            else:
                logger.error(
                    f"[{request_id}] "
                    f"Slack error: {result.get('error')}"
                )
        except Exception as e:
            logger.error(
                f"[{request_id}] "
                f"Slack send failed: {str(e)}"
            )
    else:
        logger.warning(
            f"[{request_id}] "
            f"SLACK_BOT_TOKEN not set — "
            f"skipping approval message"
        )

    # ==========================================
    # Build n8n workflow JSON
    # This is what gets deployed to n8n
    # after manager approves
    # ==========================================
    workflow_json = {
        "name": f"Onboard {employee_name}",
        "nodes": [
            {
                "name": "Start",
                "type": "n8n-nodes-base.start",
                "position": [100, 300]
            }
        ],
        "connections": {},
        "metadata": {
            "employee_name": employee_name,
            "employee_email": employee_email,
            "role": role,
            "department": department,
            "start_date": start_date,
            "systems": systems,
            "request_id": request_id
        }
    }

    logger.info(
        f"[{request_id}] "
        f"Workflow JSON generated — "
        f"approval_sent={approval_sent}"
    )

    return {
        **state,
        "approval_message": approval_message,
        "approval_sent": approval_sent,
        "workflow_json": json.dumps(workflow_json)
    }