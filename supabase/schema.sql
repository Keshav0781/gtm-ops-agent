-- ============================================
-- GTM Ops Agent - Database Schema
-- PostgreSQL schema for all agent data
-- Same structure works on:
--   - Local Docker PostgreSQL
--   - Supabase (production)
--   - Azure PostgreSQL (Siemens equivalent)
-- ============================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Table 1 — Leads
-- Stores every lead processed by
-- Lead Intelligence Agent
-- ============================================
CREATE TABLE IF NOT EXISTS leads (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Lead information
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    company_size VARCHAR(50),
    industry VARCHAR(100),
    message TEXT,
    
    -- Agent output
    research_summary TEXT,
    score VARCHAR(20),        -- HIGH, MEDIUM, LOW
    score_reasoning TEXT,
    draft_email TEXT,
    
    -- Human decision
    human_decision VARCHAR(20),  -- approved, rejected, edited
    edited_email TEXT,
    decided_by VARCHAR(100),
    decided_at TIMESTAMP,
    
    -- Metadata
    request_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Table 2 — Emails
-- Stores every email triaged by
-- Email Triage Agent
-- ============================================
CREATE TABLE IF NOT EXISTS emails (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Email information
    sender_email VARCHAR(255),
    sender_name VARCHAR(255),
    subject VARCHAR(500),
    body TEXT,
    received_at TIMESTAMP,
    
    -- Agent output
    classification VARCHAR(50),   -- sales, support, partnership, spam
    priority VARCHAR(20),         -- high, medium, low
    routing_to VARCHAR(100),
    draft_reply TEXT,
    classification_reasoning TEXT,
    
    -- Human decision
    human_decision VARCHAR(20),   -- approved, rejected, edited
    edited_reply TEXT,
    decided_by VARCHAR(100),
    decided_at TIMESTAMP,
    
    -- Metadata
    request_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Table 3 — Meetings
-- Stores every meeting summarised by
-- Meeting Intelligence Agent
-- ============================================
CREATE TABLE IF NOT EXISTS meetings (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Meeting information
    meeting_title VARCHAR(255),
    meeting_date TIMESTAMP,
    attendees TEXT,
    transcript TEXT,
    
    -- Agent output
    summary TEXT,
    decisions TEXT,
    action_items JSONB,    -- list of tasks with owners
    notion_tasks_created BOOLEAN DEFAULT FALSE,
    slack_posted BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    request_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Table 4 — CRM Alerts
-- Stores every stale deal flagged by
-- CRM Hygiene Agent
-- ============================================
CREATE TABLE IF NOT EXISTS crm_alerts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Deal information
    deal_id VARCHAR(100),
    deal_name VARCHAR(255),
    deal_owner VARCHAR(100),
    deal_stage VARCHAR(100),
    last_contact_date TIMESTAMP,
    days_inactive INTEGER,
    
    -- Agent output
    alert_type VARCHAR(50),     -- stale, missing_info, wrong_stage
    alert_reason TEXT,
    recommended_action TEXT,
    
    -- Human response
    was_actioned BOOLEAN DEFAULT FALSE,
    actioned_at TIMESTAMP,
    
    -- Metadata
    request_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Table 5 — Competitor Reports
-- Stores weekly reports from
-- Competitor Intelligence Agent
-- ============================================
CREATE TABLE IF NOT EXISTS competitor_reports (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Competitor information
    competitor_name VARCHAR(255),
    competitor_url VARCHAR(500),
    
    -- Agent output
    changes_detected BOOLEAN DEFAULT FALSE,
    changes_summary TEXT,
    pricing_changes TEXT,
    feature_changes TEXT,
    blog_updates TEXT,
    job_postings TEXT,
    
    -- Metadata
    report_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Table 6 — Agent Audit Log
-- Master audit trail for ALL agent actions
-- Used by feedback loop to improve agents
-- Critical for GDPR compliance in Germany
-- ============================================
CREATE TABLE IF NOT EXISTS agent_audit_log (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Request tracking
    request_id VARCHAR(20),
    
    -- Agent information
    agent_name VARCHAR(100),    -- lead_intelligence, email_triage etc
    action_type VARCHAR(100),   -- research, classify, summarise etc
    
    -- Input and output
    input_data JSONB,
    output_data JSONB,
    
    -- LLM information
    llm_provider VARCHAR(50),   -- groq, ollama
    llm_model VARCHAR(100),
    tokens_used INTEGER,
    duration_ms INTEGER,
    
    -- Human feedback
    -- This is what the feedback loop reads
    human_approved BOOLEAN,
    human_feedback TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- Indexes — Speed up common queries
-- At Siemens indexes are mandatory on
-- any column used in WHERE clauses
-- ============================================
CREATE INDEX IF NOT EXISTS idx_leads_score 
    ON leads(score);
CREATE INDEX IF NOT EXISTS idx_leads_created_at 
    ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_emails_classification 
    ON emails(classification);
CREATE INDEX IF NOT EXISTS idx_crm_alerts_deal_owner 
    ON crm_alerts(deal_owner);
CREATE INDEX IF NOT EXISTS idx_audit_log_agent_name 
    ON agent_audit_log(agent_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at 
    ON agent_audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_human_approved 
    ON agent_audit_log(human_approved);



-- ============================================
-- Table 7 — HR Onboarding
-- Stores onboarding requests and state
-- Allows /hr/provision to retrieve full state
-- using request_id after manager approves
-- ============================================
CREATE TABLE IF NOT EXISTS hr_onboarding (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Request tracking
    request_id VARCHAR(20) UNIQUE NOT NULL,
    
    -- Employee information
    employee_name VARCHAR(255),
    employee_email VARCHAR(255),
    role VARCHAR(100),
    department VARCHAR(100),
    start_date VARCHAR(100),
    manager_name VARCHAR(255),
    office_location VARCHAR(255),
    
    -- Provisioning plan
    systems_to_provision JSONB,
    slack_channels JSONB,
    drive_folder_path VARCHAR(500),
    requires_github BOOLEAN DEFAULT FALSE,
    requires_figma BOOLEAN DEFAULT FALSE,
    provisioning_plan_summary TEXT,
    
    -- Status
    approval_sent BOOLEAN DEFAULT FALSE,
    approved BOOLEAN DEFAULT FALSE,
    provisioning_complete BOOLEAN DEFAULT FALSE,
    
    -- Results
    drive_folder_created BOOLEAN DEFAULT FALSE,
    drive_folder_url VARCHAR(500),
    calendar_shared BOOLEAN DEFAULT FALSE,
    slack_invited BOOLEAN DEFAULT FALSE,
    welcome_email_sent BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hr_onboarding_request_id
    ON hr_onboarding(request_id);