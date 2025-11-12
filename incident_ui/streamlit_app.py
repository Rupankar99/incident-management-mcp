import streamlit as st
import sqlite3
import pandas as pd

# 🔧 CONFIG
DB_PATH = "/Users/rupankarchakroborty/Documents/incident-management-2/database/data/incident_iq.db"

# ✅ Helper: fetch table data as DataFrame
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM all_incidents", conn)
    conn.close()
    return df

# ✅ Page config
st.set_page_config(
    page_title="Incident Management Dashboard",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Incident Management Dashboard")
st.caption("Centralized view of all incidents across Jira, Slack, and PagerDuty")

# Load data
df = load_data()

if df.empty:
    st.warning("No incident data found in the database.")
    st.stop()

# Format timestamps (optional)
for col in ["created_at", "last_updated"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")

# Tabs for each section
tabs = st.tabs(["📋 Master View", "🧾 Jira Incidents", "💬 Slack Alerts", "🚨 PagerDuty Incidents"])

# 🎯 MASTER VIEW
with tabs[0]:
    st.subheader("📋 Master Incident View")
    st.dataframe(
        df[[
            "id", "source", "title", "description", "priority", "status",
            "created_at", "last_updated", "reporter", "assigned_to"
        ]],
        use_container_width=True,
        hide_index=True
    )

# 🧾 JIRA TAB
with tabs[1]:
    st.subheader("🧾 Jira Incidents")
    jira_df = df[df["source"] == "jira"]

    if not jira_df.empty:
        jira_cols = [
            "jira_ticket_id", "jira_project", "jira_issue_type", "jira_url",
            "priority", "title", "status", "reporter", "assigned_to", "created_at"
        ]
        jira_cols = [col for col in jira_cols if col in jira_df.columns]
        st.dataframe(jira_df[jira_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No Jira incidents found.")

# 💬 SLACK TAB
with tabs[2]:
    st.subheader("💬 Slack Alerts")
    slack_df = df[df["source"] == "slack"]

    if not slack_df.empty:
        slack_cols = [
            "slack_channel", "slack_thread_ts", "slack_user", "slack_permalink",
            "title", "priority", "status", "created_at"
        ]
        slack_cols = [col for col in slack_cols if col in slack_df.columns]
        st.dataframe(slack_df[slack_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No Slack alerts found.")

# 🚨 PAGERDUTY TAB
with tabs[3]:
    st.subheader("🚨 PagerDuty Incidents")
    pd_df = df[df["source"] == "pagerduty"]

    if not pd_df.empty:
        pd_cols = [
            "pd_incident_id", "pd_service_id", "pd_escalation_policy", "pd_html_url",
            "title", "priority", "status", "created_at"
        ]
        pd_cols = [col for col in pd_cols if col in pd_df.columns]
        st.dataframe(pd_df[pd_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No PagerDuty incidents found.")
