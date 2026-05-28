"""
HR Onboarding Agent — State Definition

Shared notebook flowing through all 4 nodes.

Flow:
parse_request → plan_provisioning →
generate_workflow → deploy_and_notify

Real business scenario:
HR types "Onboard Sarah Chen as Product Designer"
Agent plans, gets manager approval, then:
- Creates Google Drive folder
- Shares Google Calendar
- Invites to Slack channels
- Sends welcome email via Gmail
All in under 5 minutes.
"""

from typing import Optional, List
from typing_extensions import TypedDict


class HROnboardingState(TypedDict):
    """
    Complete state for HR Onboarding Agent.
    Each node reads from and adds to this state.
    """

    # ==========================================
    # INPUT — natural language request from HR
    # ==========================================
    onboarding_request: Optional[str]   # raw HR input

    # ==========================================
    # PARSED — from parse_request node
    # Structured data extracted from NL request
    # ==========================================
    employee_name: Optional[str]
    employee_email: Optional[str]
    role: Optional[str]
    department: Optional[str]
    start_date: Optional[str]
    manager_name: Optional[str]
    office_location: Optional[str]

    # ==========================================
    # PROVISIONING PLAN — from plan_provisioning
    # Agent decides what to provision based on role
    # ==========================================
    systems_to_provision: Optional[List[str]]
    slack_channels: Optional[List[str]]
    drive_folder_name: Optional[str]
    drive_folder_path: Optional[str]
    requires_github: Optional[bool]
    requires_figma: Optional[bool]
    provisioning_plan_summary: Optional[str]

    # ==========================================
    # APPROVAL — from generate_workflow node
    # Slack approval card sent to manager
    # ==========================================
    approval_message: Optional[str]
    approval_sent: Optional[bool]
    workflow_json: Optional[str]

    # ==========================================
    # RESULTS — from deploy_and_notify node
    # What was actually provisioned
    # ==========================================
    drive_folder_created: Optional[bool]
    drive_folder_url: Optional[str]
    calendar_shared: Optional[bool]
    slack_invited: Optional[bool]
    welcome_email_sent: Optional[bool]
    confirmation_sent: Optional[bool]

    # ==========================================
    # METADATA — tracking and audit
    # ==========================================
    request_id: Optional[str]
    error: Optional[str]
    completed: Optional[bool]