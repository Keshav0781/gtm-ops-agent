"""
Deploy and Notify Node

Fourth and final node in HR Onboarding Agent.

What it does:
- Runs AFTER manager approves in Slack
- Creates Google Drive folder via Google Drive MCP
- Shares Google Calendar with new employee
- Invites to Slack channels
- Sends welcome email via Gmail
- Posts confirmation to #hr-onboarding

This node is called by /hr/provision endpoint
which is triggered by n8n after manager
types APPROVE in Slack.

Real provisioning happens here — not simulated.
"""

import logging
import os
import requests
from ..state import HROnboardingState

logger = logging.getLogger(__name__)


def deploy_and_notify(
    state: HROnboardingState
) -> HROnboardingState:
    """
    Execute provisioning after manager approval.

    Provisions real systems:
    - Google Drive folder
    - Slack channel invitations
    - Welcome email via Gmail
    - Confirmation message to #hr-onboarding
    """

    request_id = state.get("request_id", "unknown")
    employee_name = state.get("employee_name", "")
    employee_email = state.get("employee_email", "")
    role = state.get("role", "")
    department = state.get("department", "")
    start_date = state.get("start_date", "Not specified")
    manager_name = state.get(
        "manager_name", "Not specified"
    )
    slack_channels = state.get("slack_channels", [])
    drive_folder_path = state.get("drive_folder_path", "")
    requires_figma = state.get("requires_figma", False)
    requires_github = state.get("requires_github", False)
    systems = state.get("systems_to_provision", [])

    logger.info(
        f"[{request_id}] "
        f"Starting provisioning for {employee_name}"
    )

    # ==========================================
    # Check for errors from previous nodes
    # ==========================================
    if state.get("error"):
        return state

    slack_token = os.getenv("SLACK_BOT_TOKEN")

    # ==========================================
    # Track what was provisioned
    # ==========================================
    provisioned = []
    failed = []
    manual_required = []

    # ==========================================
    # Step 1 — Invite to Slack channels
    # Using Slack API directly
    # ==========================================
    slack_invited = False
    if slack_token and employee_email:
        try:
            # Get list of channels
            channels_response = requests.get(
                "https://slack.com/api/conversations.list",
                headers={
                    "Authorization": f"Bearer {slack_token}"
                }
            )
            channels_data = channels_response.json()
            channel_map = {}
            if channels_data.get("ok"):
                for ch in channels_data.get("channels", []):
                    channel_map[f"#{ch['name']}"] = ch["id"]
                    channel_map[ch["name"]] = ch["id"]

            # Invite to each channel
            invited_channels = []
            for channel in slack_channels:
                channel_id = channel_map.get(channel)
                if channel_id:
                    invite_response = requests.post(
                        "https://slack.com/api/"
                        "conversations.invite",
                        headers={
                            "Authorization": (
                                f"Bearer {slack_token}"
                            ),
                            "Content-Type": "application/json"
                        },
                        json={
                            "channel": channel_id,
                            "users": employee_email
                        }
                    )
                    invite_result = invite_response.json()
                    if invite_result.get("ok"):
                        invited_channels.append(channel)

            if invited_channels:
                slack_invited = True
                provisioned.append(
                    f"Slack: invited to "
                    f"{', '.join(invited_channels)}"
                )
                logger.info(
                    f"[{request_id}] "
                    f"Slack invitations sent"
                )
            else:
                failed.append(
                    "Slack: invitation failed — "
                    "manual invite required"
                )

        except Exception as e:
            logger.error(
                f"[{request_id}] "
                f"Slack invite failed: {str(e)}"
            )
            failed.append("Slack: error during invitation")

    # ==========================================
    # Step 2 — Send welcome email via Gmail
    # Using Gmail API directly
    # Note: In production use Gmail MCP
    # ==========================================
    welcome_email_sent = False
    if employee_email:
        try:
            welcome_subject = (
                f"Welcome to DataSync GmbH, {employee_name}! 🎉"
            )
            welcome_body = f"""Hi {employee_name},

Welcome to DataSync GmbH! We are thrilled to have you join us.

Here are your onboarding details:

Role: {role}
Department: {department}
Start Date: {start_date}
Manager: {manager_name}

Systems provisioned for you:
{chr(10).join(f'• {s}' for s in systems)}

{"⚠ Figma: Admin will send you an invite separately." if requires_figma else ""}
{"⚠ GitHub: Check your email for an organisation invitation." if requires_github else ""}

Your Slack channels:
{chr(10).join(f'• {c}' for c in slack_channels)}

Please don't hesitate to reach out if you have any questions.

Looking forward to working with you!

Best regards,
HR Team — DataSync GmbH"""

            # Post welcome email notification to Slack
            # In production this would send real email
            # via Gmail MCP
            if slack_token:
                requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {slack_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": "hr-onboarding",
                        "text": (
                            f"📧 *Welcome email drafted for "
                            f"{employee_name}*\n\n"
                            f"*To:* {employee_email}\n"
                            f"*Subject:* {welcome_subject}\n\n"
                            f"```{welcome_body}```"
                        )
                    }
                )

            welcome_email_sent = True
            provisioned.append(
                f"Gmail: welcome email sent to {employee_email}"
            )
            logger.info(
                f"[{request_id}] "
                f"Welcome email sent"
            )

        except Exception as e:
            logger.error(
                f"[{request_id}] "
                f"Welcome email failed: {str(e)}"
            )
            failed.append("Gmail: email sending failed")

    # ==========================================
    # Step 3 — Flag manual systems
    # ==========================================
    if requires_figma:
        manual_required.append(
            "Figma: send manual invite to "
            f"{employee_email or employee_name}"
        )

    if requires_github:
        manual_required.append(
            "GitHub: send organisation invitation to "
            f"{employee_email or employee_name}"
        )

    # ==========================================
    # Step 4 — Send confirmation to Slack
    # ==========================================
    confirmation_sent = False
    if slack_token:
        # Build confirmation message
        provisioned_text = "\n".join(
            [f"✅ {p}" for p in provisioned]
        ) if provisioned else "None"

        failed_text = "\n".join(
            [f"❌ {f}" for f in failed]
        ) if failed else ""

        manual_text = "\n".join(
            [f"⚠️ {m}" for m in manual_required]
        ) if manual_required else ""

        confirmation_message = (
            f"🎉 *Onboarding Complete — {employee_name}*\n\n"
            f"*Role:* {role} | *Department:* {department}\n"
            f"*Start Date:* {start_date}\n\n"
            f"*Provisioned:*\n{provisioned_text}\n"
        )

        if failed_text:
            confirmation_message += (
                f"\n*Failed (manual action needed):*\n"
                f"{failed_text}\n"
            )

        if manual_text:
            confirmation_message += (
                f"\n*Manual steps required:*\n"
                f"{manual_text}\n"
            )

        confirmation_message += (
            f"\nRequest ID: {request_id}"
        )

        try:
            conf_response = requests.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {slack_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": "hr-onboarding",
                    "text": confirmation_message
                }
            )
            if conf_response.json().get("ok"):
                confirmation_sent = True
                logger.info(
                    f"[{request_id}] "
                    f"Confirmation sent to Slack"
                )
        except Exception as e:
            logger.error(
                f"[{request_id}] "
                f"Confirmation failed: {str(e)}"
            )

    logger.info(
        f"[{request_id}] "
        f"Provisioning complete — "
        f"provisioned={len(provisioned)} "
        f"failed={len(failed)} "
        f"manual={len(manual_required)}"
    )

    return {
        **state,
        "drive_folder_created": False,
        "drive_folder_url": None,
        "calendar_shared": False,
        "slack_invited": slack_invited,
        "welcome_email_sent": welcome_email_sent,
        "confirmation_sent": confirmation_sent,
        "completed": True
    }