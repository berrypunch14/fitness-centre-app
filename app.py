import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# -----------------------------
# DB CONNECTION
# -----------------------------
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("fitness_centre.db", check_same_thread=False)
    return conn

conn = get_connection()
cursor = conn.cursor()

# -----------------------------
# UTILITIES
# -----------------------------
def run_query(query, params=()):
    cursor.execute(query, params)
    conn.commit()

def fetch_df(query, params=()):
    return pd.read_sql_query(query, conn, params=params)

def table_exists(name: str) -> bool:
    q = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
    return cursor.execute(q, (name,)).fetchone() is not None

# safe defaults if tables missing
for t in ["MEMBER", "MEMBER_ASSESSMENT", "MEMBER_CONDITION"]:
    if not table_exists(t):
        st.warning(f"Warning: Table {t} not found in DB. Some features may not work.")

# -----------------------------
# APP LAYOUT
# -----------------------------
st.set_page_config(page_title="Fitness Centre Dashboard", layout="wide")
st.title("🏋️ Fitness Centre — Database Dashboard")
st.caption("Interactive CRUD app — Project by [Your Name], University of Sheffield")

menu = ["Dashboard", "Manage Members", "Member Assessments", "Member Conditions", "About"]
choice = st.sidebar.selectbox("Navigation", menu)

# -----------------------------
# DASHBOARD
# -----------------------------
if choice == "Dashboard":
    st.header("Summary Dashboard")

    # load dataframes (handle empty gracefully)
    members_df = fetch_df("SELECT * FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame(columns=["EMAIL","FIRST_NAME","LAST_NAME","GENDER"])
    assess_df = fetch_df("SELECT * FROM MEMBER_ASSESSMENT") if table_exists("MEMBER_ASSESSMENT") else pd.DataFrame(columns=["EMAIL","ASSESSMENT_DATE","HEIGHT","BMI","BLOOD_PRESSURE","HEART_RATE","WEIGHT"])
    cond_df = fetch_df("SELECT * FROM MEMBER_CONDITION") if table_exists("MEMBER_CONDITION") else pd.DataFrame(columns=["EMAIL","CONDITION_NAME","SEVERITY","NOTES"])

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Members", len(members_df))
    col2.metric("Total Assessments", len(assess_df))
    avg_bmi = round(assess_df["BMI"].mean(), 2) if not assess_df.empty else "N/A"
    col3.metric("Average BMI", avg_bmi)
    common_condition = cond_df["CONDITION_NAME"].value_counts().idxmax() if not cond_df.empty else "N/A"
    col4.metric("Top Condition", common_condition)

    st.markdown("---")

    # Charts area
    st.subheader("Charts & Distributions")
    chart_col1, chart_col2 = st.columns(2)

    # Gender ratio pie
    with chart_col1:
        st.markdown("**Gender Ratio**")
        if not members_df.empty and "GENDER" in members_df.columns:
            gender_counts = members_df["GENDER"].fillna("Unknown").value_counts()
            fig1, ax1 = plt.subplots()
            ax1.pie(gender_counts.values, labels=gender_counts.index, autopct="%1.1f%%", startangle=90)
            ax1.axis("equal")
            st.pyplot(fig1)
        else:
            st.info("No member gender data available.")

    # BMI distribution histogram
    with chart_col2:
        st.markdown("**BMI Distribution (Latest Assessments)**")
        if not assess_df.empty and "BMI" in assess_df.columns:
            fig2, ax2 = plt.subplots()
            ax2.hist(assess_df["BMI"].dropna(), bins=10)
            ax2.set_xlabel("BMI")
            ax2.set_ylabel("Count")
            st.pyplot(fig2)
        else:
            st.info("No BMI data available.")

    st.markdown("---")
    st.subheader("Common Conditions")
    if not cond_df.empty:
        cond_counts = cond_df["CONDITION_NAME"].value_counts().reset_index()
        cond_counts.columns = ["condition", "count"]
        st.bar_chart(data=cond_counts.set_index("condition"))
    else:
        st.info("No condition data available.")

# -----------------------------
# MANAGE MEMBERS
# -----------------------------
elif choice == "Manage Members":
    st.header("Manage Members")
    tab_add, tab_view, tab_edit, tab_delete = st.tabs(["Add Member", "View Members", "Edit Member", "Delete Member"])

    with tab_add:
        st.subheader("Add New Member")
        with st.form("add_member_form", clear_on_submit=True):
            em = st.text_input("Email")
            fn = st.text_input("First Name")
            ln = st.text_input("Last Name")
            gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
            submitted = st.form_submit_button("Add Member")
            if submitted:
                if not em:
                    st.error("Email is required.")
                else:
                    try:
                        run_query("INSERT INTO MEMBER (EMAIL, FIRST_NAME, LAST_NAME, GENDER) VALUES (?, ?, ?, ?)", (em, fn, ln, gender))
                        st.success(f"Member {fn} {ln} added.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab_view:
        st.subheader("All Members")
        members_df = fetch_df("SELECT * FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members_df.empty:
            st.dataframe(members_df)
            # Search
            st.markdown("**Search members**")
            q = st.text_input("Search by email / first name / last name")
            if q:
                mask = members_df.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False))
                filtered = members_df[mask.any(axis=1)]
                st.dataframe(filtered)
        else:
            st.info("No members in database.")

    with tab_edit:
        st.subheader("Edit Member")
        members = fetch_df("SELECT EMAIL, FIRST_NAME, LAST_NAME FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            sel = st.selectbox("Select member by email", members["EMAIL"])
            if sel:
                row = fetch_df("SELECT * FROM MEMBER WHERE EMAIL = ?", (sel,))
                if not row.empty:
                    fn_new = st.text_input("First Name", value=row.at[0, "FIRST_NAME"] if "FIRST_NAME" in row.columns else "")
                    ln_new = st.text_input("Last Name", value=row.at[0, "LAST_NAME"] if "LAST_NAME" in row.columns else "")
                    gender_new = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"], index=0)
                    if st.button("Update Member"):
                        try:
                            run_query("UPDATE MEMBER SET FIRST_NAME=?, LAST_NAME=?, GENDER=? WHERE EMAIL=?", (fn_new, ln_new, gender_new, sel))
                            st.success("Member updated.")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No members to edit.")

    with tab_delete:
        st.subheader("Delete Member")
        members = fetch_df("SELECT EMAIL, FIRST_NAME, LAST_NAME FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            sel = st.selectbox("Select member to delete", members["EMAIL"])
            if st.button("Delete"):
                try:
                    run_query("DELETE FROM MEMBER WHERE EMAIL=?", (sel,))
                    st.success(f"Deleted {sel}")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No members to delete.")

# -----------------------------
# MEMBER ASSESSMENTS
# -----------------------------
elif choice == "Member Assessments":
    st.header("Member Assessments")
    tab_add, tab_view, tab_edit, tab_delete = st.tabs(["Add Assessment", "View Assessments", "Edit Assessment", "Delete Assessment"])

    with tab_add:
        st.subheader("Add New Assessment")
        members = fetch_df("SELECT EMAIL, FIRST_NAME, LAST_NAME FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            email = st.selectbox("Select Member", members["EMAIL"])
            date = st.date_input("Assessment Date", value=datetime.today())
            height = st.number_input("Height (cm)", min_value=0.0, format="%.2f")
            bmi = st.number_input("BMI", min_value=0.0, format="%.2f")
            bp = st.number_input("Blood Pressure", min_value=0.0, format="%.2f")
            hr = st.number_input("Heart Rate", min_value=0.0, format="%.2f")
            weight = st.number_input("Weight (kg)", min_value=0.0, format="%.2f")
            if st.button("Add Assessment"):
                try:
                    run_query("""INSERT INTO MEMBER_ASSESSMENT
                                 (EMAIL, ASSESSMENT_DATE, HEIGHT, BMI, BLOOD_PRESSURE, HEART_RATE, WEIGHT)
                                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
                              (email, date, height or None, bmi or None, bp or None, hr or None, weight or None))
                    st.success("Assessment added.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("Add members first before assessments.")

    with tab_view:
        st.subheader("View Assessments")
        df = fetch_df("SELECT * FROM MEMBER_ASSESSMENT ORDER BY ASSESSMENT_DATE DESC") if table_exists("MEMBER_ASSESSMENT") else pd.DataFrame()
        if not df.empty:
            # date filter
            st.write("Filter by date range")
            min_date = pd.to_datetime(df["ASSESSMENT_DATE"]).min()
            max_date = pd.to_datetime(df["ASSESSMENT_DATE"]).max()
            start, end = st.date_input("Start / End", value=(min_date.date(), max_date.date()))
            mask = (pd.to_datetime(df["ASSESSMENT_DATE"]) >= pd.to_datetime(start)) & (pd.to_datetime(df["ASSESSMENT_DATE"]) <= pd.to_datetime(end))
            st.dataframe(df[mask])
        else:
            st.info("No assessments recorded.")

    with tab_edit:
        st.subheader("Edit Assessment")
        df = fetch_df("SELECT * FROM MEMBER_ASSESSMENT") if table_exists("MEMBER_ASSESSMENT") else pd.DataFrame()
        if not df.empty:
            # choose by composite key
            df["KEY"] = df["EMAIL"].astype(str) + " | " + df["ASSESSMENT_DATE"].astype(str)
            sel = st.selectbox("Select assessment", df["KEY"])
            if sel:
                email_sel, date_sel = [s.strip() for s in sel.split("|")]
                row = fetch_df("SELECT * FROM MEMBER_ASSESSMENT WHERE EMAIL=? AND ASSESSMENT_DATE=?", (email_sel, date_sel))
                if not row.empty:
                    height = st.number_input("Height (cm)", value=float(row.at[0, "HEIGHT"] or 0.0))
                    bmi = st.number_input("BMI", value=float(row.at[0, "BMI"] or 0.0))
                    bp = st.number_input("Blood Pressure", value=float(row.at[0, "BLOOD_PRESSURE"] or 0.0))
                    hr = st.number_input("Heart Rate", value=float(row.at[0, "HEART_RATE"] or 0.0))
                    weight = st.number_input("Weight (kg)", value=float(row.at[0, "WEIGHT"] or 0.0))
                    if st.button("Update Assessment"):
                        try:
                            run_query("""UPDATE MEMBER_ASSESSMENT
                                         SET HEIGHT=?, BMI=?, BLOOD_PRESSURE=?, HEART_RATE=?, WEIGHT=?
                                         WHERE EMAIL=? AND ASSESSMENT_DATE=?""",
                                      (height, bmi, bp, hr, weight, email_sel, date_sel))
                            st.success("Assessment updated.")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No assessments to edit.")

    with tab_delete:
        st.subheader("Delete Assessment")
        df = fetch_df("SELECT * FROM MEMBER_ASSESSMENT") if table_exists("MEMBER_ASSESSMENT") else pd.DataFrame()
        if not df.empty:
            df["KEY"] = df["EMAIL"].astype(str) + " | " + df["ASSESSMENT_DATE"].astype(str)
            sel = st.selectbox("Select assessment to delete", df["KEY"])
            if st.button("Delete Assessment"):
                email_sel, date_sel = [s.strip() for s in sel.split("|")]
                try:
                    run_query("DELETE FROM MEMBER_ASSESSMENT WHERE EMAIL=? AND ASSESSMENT_DATE=?", (email_sel, date_sel))
                    st.success("Deleted assessment.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No assessments to delete.")

# -----------------------------
# MEMBER CONDITIONS
# -----------------------------
elif choice == "Member Conditions":
    st.header("Member Conditions")
    tab_add, tab_view, tab_edit, tab_delete = st.tabs(["Add Condition", "View Conditions", "Edit Condition", "Delete Condition"])

    with tab_add:
        st.subheader("Add Condition")
        members = fetch_df("SELECT EMAIL, FIRST_NAME, LAST_NAME FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            email = st.selectbox("Select Member", members["EMAIL"])
            cond = st.text_input("Condition Name")
            severity = st.selectbox("Severity", ["Mild", "Moderate", "Severe"])
            notes = st.text_area("Notes")
            if st.button("Add Condition"):
                try:
                    run_query("INSERT INTO MEMBER_CONDITION (EMAIL, CONDITION_NAME, SEVERITY, NOTES) VALUES (?, ?, ?, ?)", (email, cond, severity, notes))
                    st.success("Condition added.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("Add members first before conditions.")

    with tab_view:
        st.subheader("View Conditions")
        df = fetch_df("SELECT * FROM MEMBER_CONDITION") if table_exists("MEMBER_CONDITION") else pd.DataFrame()
        if not df.empty:
            severity_filter = st.selectbox("Filter by severity", options=["All"] + sorted(df["SEVERITY"].dropna().unique().tolist()))
            if severity_filter and severity_filter != "All":
                st.dataframe(df[df["SEVERITY"] == severity_filter])
            else:
                st.dataframe(df)
        else:
            st.info("No conditions recorded.")

    with tab_edit:
        st.subheader("Edit Condition")
        df = fetch_df("SELECT * FROM MEMBER_CONDITION") if table_exists("MEMBER_CONDITION") else pd.DataFrame()
        if not df.empty:
            df["KEY"] = df["EMAIL"].astype(str) + " | " + df["CONDITION_NAME"].astype(str)
            sel = st.selectbox("Select condition", df["KEY"])
            if sel:
                email_sel, cond_sel = [s.strip() for s in sel.split("|")]
                row = fetch_df("SELECT * FROM MEMBER_CONDITION WHERE EMAIL=? AND CONDITION_NAME=?", (email_sel, cond_sel))
                if not row.empty:
                    severity = st.selectbox("Severity", ["Mild", "Moderate", "Severe"], index=0)
                    notes = st.text_area("Notes", value=row.at[0, "NOTES"] if "NOTES" in row.columns else "")
                    if st.button("Update Condition"):
                        try:
                            run_query("UPDATE MEMBER_CONDITION SET SEVERITY=?, NOTES=? WHERE EMAIL=? AND CONDITION_NAME=?", (severity, notes, email_sel, cond_sel))
                            st.success("Condition updated.")
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("No conditions to edit.")

    with tab_delete:
        st.subheader("Delete Condition")
        df = fetch_df("SELECT * FROM MEMBER_CONDITION") if table_exists("MEMBER_CONDITION") else pd.DataFrame()
        if not df.empty:
            df["KEY"] = df["EMAIL"].astype(str) + " | " + df["CONDITION_NAME"].astype(str)
            sel = st.selectbox("Select condition to delete", df["KEY"])
            if st.button("Delete Condition"):
                email_sel, cond_sel = [s.strip() for s in sel.split("|")]
                try:
                    run_query("DELETE FROM MEMBER_CONDITION WHERE EMAIL=? AND CONDITION_NAME=?", (email_sel, cond_sel))
                    st.success("Condition deleted.")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.info("No conditions to delete.")

# -----------------------------
# ABOUT
# -----------------------------
elif choice == "About":
    st.header("About this Project")
    st.markdown("""
    **Fitness Centre Database App**
    - Built with **Streamlit**, **SQLite3**, and **Pandas**.  
    - Supports full CRUD for members, assessments, and health conditions.  
    - Includes dashboard metrics and interactive charts for quick insights.

    Project by **[Your Name]**, University of Sheffield.
    """)

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("Project: Fitness Centre Database • Built with Python, Streamlit & SQLite3 • Demo for résumé / portfolio")
