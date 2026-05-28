"""
Database Utility

Handles PostgreSQL connections for GTM Ops Agent.
Used by HR Onboarding to store and retrieve state.

Connection details from docker-compose.yml:
- Host: localhost
- Port: 5432
- User: gtmuser
- Password: gtmpassword
- Database: gtmops
"""

import asyncpg
import logging
import json
import os

logger = logging.getLogger(__name__)

# Database connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://gtmuser:gtmpassword@localhost:5432/gtmops"
)


async def get_connection():
    """
    Get a database connection.
    Always close after use.
    """
    return await asyncpg.connect(DATABASE_URL)


async def save_onboarding_state(state: dict) -> bool:
    """
    Save HR onboarding state to database.
    Called by /hr/onboard after planning.
    Returns True if saved successfully.
    """
    conn = None
    try:
        conn = await get_connection()

        await conn.execute("""
            INSERT INTO hr_onboarding (
                request_id,
                employee_name,
                employee_email,
                role,
                department,
                start_date,
                manager_name,
                office_location,
                systems_to_provision,
                slack_channels,
                drive_folder_path,
                requires_github,
                requires_figma,
                provisioning_plan_summary,
                approval_sent
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8,
                $9, $10, $11, $12, $13, $14, $15
            )
            ON CONFLICT (request_id) DO UPDATE SET
                approval_sent = $15,
                updated_at = NOW()
        """,
            state.get("request_id"),
            state.get("employee_name"),
            state.get("employee_email"),
            state.get("role"),
            state.get("department"),
            state.get("start_date"),
            state.get("manager_name"),
            state.get("office_location"),
            json.dumps(state.get("systems_to_provision", [])),
            json.dumps(state.get("slack_channels", [])),
            state.get("drive_folder_path"),
            state.get("requires_github", False),
            state.get("requires_figma", False),
            state.get("provisioning_plan_summary"),
            state.get("approval_sent", False)
        )

        logger.info(
            f"Saved onboarding state for "
            f"request_id={state.get('request_id')}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to save state: {str(e)}")
        return False

    finally:
        if conn:
            await conn.close()


async def get_onboarding_state(request_id: str) -> dict:
    """
    Retrieve HR onboarding state from database.
    Called by /hr/provision after manager approves.
    Returns state dict or None if not found.
    """
    conn = None
    try:
        conn = await get_connection()

        row = await conn.fetchrow("""
            SELECT * FROM hr_onboarding
            WHERE request_id = $1
        """, request_id)

        if not row:
            logger.warning(
                f"No state found for request_id={request_id}"
            )
            return None

        state = dict(row)

        # Parse JSON fields
        state["systems_to_provision"] = json.loads(
            state.get("systems_to_provision") or "[]"
        )
        state["slack_channels"] = json.loads(
            state.get("slack_channels") or "[]"
        )

        logger.info(
            f"Retrieved state for "
            f"request_id={request_id}"
        )
        return state

    except Exception as e:
        logger.error(f"Failed to retrieve state: {str(e)}")
        return None

    finally:
        if conn:
            await conn.close()


async def update_provisioning_status(
    request_id: str,
    slack_invited: bool,
    welcome_email_sent: bool,
    confirmation_sent: bool
) -> bool:
    """
    Update provisioning results after deploy_and_notify runs.
    """
    conn = None
    try:
        conn = await get_connection()

        await conn.execute("""
            UPDATE hr_onboarding SET
                approved = TRUE,
                provisioning_complete = TRUE,
                slack_invited = $2,
                welcome_email_sent = $3,
                updated_at = NOW()
            WHERE request_id = $1
        """,
            request_id,
            slack_invited,
            welcome_email_sent
        )

        logger.info(
            f"Updated provisioning status for "
            f"request_id={request_id}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to update status: {str(e)}"
        )
        return False

    finally:
        if conn:
            await conn.close()