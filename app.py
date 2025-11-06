import streamlit as st
import sqlite3
import pandas as pd
import altair as alt  # <-- Replaced matplotlib
from datetime import datetime

# -----------------------------
# DB CONNECTION
# -----------------------------
@st.cache_resource
def get_connection():
    conn = sqlite3.connect("fitness_centre.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Optional: Allows accessing columns by name
    return conn

conn = get_connection()
# --- Global cursor removed ---

# -----------------------------
# UTILITIES
# -----------------------------
def run_query(query, params=()):
    # FIX: Create a new cursor for each operation
    with conn.cursor() as c:
        c.execute(query, params)
        conn.commit()

def fetch_df(query, params=()):
    # pd.read_sql_query handles its own connection management
    return pd.read_sql_query(query, conn, params=params)

def table_exists(name: str) -> bool:
    # FIX: Create a new cursor
    with conn.cursor() as c:
        q = "SELECT name FROM sqlite_master WHERE type='table' AND name=?;"
        return c.execute(q, (name,)).fetchone() is not None

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

    # FIX: Gender ratio pie (using Altair)
    with chart_col1:
        st.markdown("**Gender Ratio**")
        if not members_df.empty and "GENDER" in members_df.columns:
            gender_counts = members_df["GENDER"].fillna("Unknown").value_counts().reset_index()
            gender_counts.columns = ["gender", "count"]
            
            base = alt.Chart(gender_counts).encode(
               theta=alt.Theta("count", stack=True)
            )
            pie = base.mark_arc(outerRadius=120).encode(
                color=alt.Color("gender"),
                order=alt.Order("count", sort="descending"),
                tooltip=["gender", "count"]
            )
            text = base.mark_text(radius=140).encode(
                text=alt.Text("count"),
                order=alt.Order("count", sort="descending"),
                color=alt.value("black")
            )
            chart = pie + text
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No member gender data available.")

    # FIX: BMI distribution histogram (using Altair)
    with chart_col2:
        st.markdown("**BMI Distribution**")
        if not assess_df.empty and "BMI" in assess_df.columns:
            chart = alt.Chart(assess_df).mark_bar().encode(
                x=alt.X("BMI", bin=True, title="BMI"),
                y=alt.Y('count()', title="Count"),
                tooltip=[alt.Tooltip("BMI", bin=True), 'count()']
            ).interactive()
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No BMI data available.")

    st.markdown("---")
    st.subheader("Common Conditions")
    if not cond_df.empty:
        cond_counts = cond_df["CONDITION_NAME"].value_counts().reset_index()
        cond_counts.columns = ["condition", "count"]
        # Use native st.bar_chart (which is also great!)
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
                        st.rerun() # FIX: Refresh app state
                    except Exception as e:
                        st.error(f"Error: {e}")

    with tab_view:
        st.subheader("All Members")
        
        # FIX: Efficient SQL-based search
        st.markdown("**Search members**")
        q = st.text_input("Search by email / first name / last name")
        
        if q:
            search_param = f"%{q}%"
            query = "SELECT * FROM MEMBER WHERE EMAIL LIKE ? OR FIRST_NAME LIKE ? OR LAST_NAME LIKE ?"
            members_df = fetch_df(query, (search_param, search_param, search_param))
        else:
            members_df = fetch_df("SELECT * FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()

        if not members_df.empty:
            st.dataframe(members_df)
        else:
            st.info("No members found." if q else "No members in database.")

    with tab_edit:
        st.subheader("Edit Member")
        members = fetch_df("SELECT EMAIL, FIRST_NAME, LAST_NAME FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            sel = st.selectbox("Select member by email", members["EMAIL"])
            if sel:
                row = fetch_df("SELECT * FROM MEMBER WHERE EMAIL = ?", (sel,))
                if not row.empty:
                    current = row.iloc[0]
                    with st.form("edit_member_form"):
                        fn_new = st.text_input("First Name", value=current["FIRST_NAME"])
                        ln_new = st.text_input("Last Name", value=current["LAST_NAME"])
                        
                        gender_options = ["Male", "Female", "Other", "Prefer not to say"]
                        try:
                            default_index = gender_options.index(current["GENDER"])
                        except ValueError:
                            default_index = 0
                        
                        gender_new = st.selectbox("Gender", gender_options, index=default_index)
                        
                        if st.form_submit_button("Update Member"):
                            try:
                                run_query("UPDATE MEMBER SET FIRST_NAME=?, LAST_NAME=?, GENDER=? WHERE EMAIL=?", (fn_new, ln_new, gender_new, sel))
                                st.success("Member updated.")
                                st.rerun() # FIX: Refresh app state
                            except Exception as e:
                                st.error(f"Error: {e}")
        else:
            st.info("No members to edit.")

    with tab_delete:
        st.subheader("Delete Member")
        members = fetch_df("SELECT EMAIL FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            sel = st.selectbox("Select member to delete", members["EMAIL"])
            if st.button("Delete Member", type="primary"):
                try:
                    # FIX: App-level cascade delete
                    run_query("DELETE FROM MEMBER_ASSESSMENT WHERE EMAIL=?", (sel,))
                    run_query("DELETE FROM MEMBER_CONDITION WHERE EMAIL=?", (sel,))
                    run_query("DELETE FROM MEMBER WHERE EMAIL=?", (sel,))
                    st.success(f"Deleted {sel} and all associated data.")
                    st.rerun() # FIX: Refresh app state
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
        members = fetch_df("SELECT EMAIL FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            with st.form("add_assessment_form", clear_on_submit=True):
                email = st.selectbox("Select Member", members["EMAIL"])
                date = st.date_input("Assessment Date", value=datetime.today())
                height = st.number_input("Height (cm)", min_value=0.0, format="%.2f")
                bmi = st.number_input("BMI", min_value=0.0, format="%.2f")
                bp = st.number_input("Blood Pressure", min_value=0.0, format="%.2f")
                hr = st.number_input("Heart Rate", min_value=0.0, format="%.2f")
                weight = st.number_input("Weight (kg)", min_value=0.0, format="%.2f")
                
                if st.form_submit_button("Add Assessment"):
                    try:
                        run_query("""INSERT INTO MEMBER_ASSESSMENT
                                    (EMAIL, ASSESSMENT_DATE, HEIGHT, BMI, BLOOD_PRESSURE, HEART_RATE, WEIGHT)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                    (email, date.isoformat(), height or None, bmi or None, bp or None, hr or None, weight or None))
                        st.success("Assessment added.")
                        st.rerun() # FIX: Refresh app state
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("Add members first before assessments.")

    with tab_view:
        st.subheader("View Assessments")
        df = fetch_df("SELECT * FROM MEMBER_ASSESSMENT ORDER BY ASSESSMENT_DATE DESC") if table_exists("MEMBER_ASSESSMENT") else pd.DataFrame()
        if not df.empty:
            # date filter
            df["ASSESSMENT_DATE"] = pd.to_datetime(df["ASSESSMENT_DATE"])
            min_date = df["ASSESSMENT_DATE"].min().date()
            max_date = df["ASSESSMENT_DATE"].max().date()
            
            start, end = st.date_input("Filter by date range:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            
            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)
            
            mask = (df["ASSESSMENT_DATE"] >= start_dt) & (df["ASSESSMENT_DATE"] <= end_dt)
            st.dataframe(df[mask])
        else:
            st.info("No assessments recorded.")

    with tab_edit:
        st.subheader("Edit Assessment")
        df = fetch_df("SELECT * FROM MEMBER_ASSESSMENT") if table_exists("MEMBER_ASSESSMENT") else pd.DataFrame()
        if not df.empty:
            df["KEY"] = df["EMAIL"].astype(str) + " | " + df["ASSESSMENT_DATE"].astype(str)
            sel = st.selectbox("Select assessment", df["KEY"])
            if sel:
                email_sel, date_sel = [s.strip() for s in sel.split("|")]
                row = fetch_df("SELECT * FROM MEMBER_ASSESSMENT WHERE EMAIL=? AND ASSESSMENT_DATE=?", (email_sel, date_sel))
                if not row.empty:
                    current = row.iloc[0]
                    with st.form("edit_assessment_form"):
                        height = st.number_input("Height (cm)", value=float(current["HEIGHT"] or 0.0))
                        bmi = st.number_input("BMI", value=float(current["BMI"] or 0.0))
                        bp = st.number_input("Blood Pressure", value=float(current["BLOOD_PRESSURE"] or 0.0))
                        hr = st.number_input("Heart Rate", value=float(current["HEART_RATE"] or 0.0))
                        weight = st.number_input("Weight (kg)", value=float(current["WEIGHT"] or 0.0))
                        
                        if st.form_submit_button("Update Assessment"):
                            try:
                                run_query("""UPDATE MEMBER_ASSESSMENT
                                            SET HEIGHT=?, BMI=?, BLOOD_PRESSURE=?, HEART_RATE=?, WEIGHT=?
                                            WHERE EMAIL=? AND ASSESSMENT_DATE=?""",
                                            (height, bmi, bp, hr, weight, email_sel, date_sel))
                                st.success("Assessment updated.")
                                st.rerun() # FIX: Refresh app state
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
            if st.button("Delete Assessment", type="primary"):
                email_sel, date_sel = [s.strip() for s in sel.split("|")]
                try:
                    run_query("DELETE FROM MEMBER_ASSESSMENT WHERE EMAIL=? AND ASSESSMENT_DATE=?", (email_sel, date_sel))
                    st.success("Deleted assessment.")
                    st.rerun() # FIX: Refresh app state
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
        members = fetch_df("SELECT EMAIL FROM MEMBER") if table_exists("MEMBER") else pd.DataFrame()
        if not members.empty:
            with st.form("add_condition_form", clear_on_submit=True):
                email = st.selectbox("Select Member", members["EMAIL"])
                cond = st.text_input("Condition Name")
                severity = st.selectbox("Severity", ["Mild", "Moderate", "Severe"])
                notes = st.text_area("Notes")
                if st.form_submit_button("Add Condition"):
                    if not cond:
                        st.error("Condition Name is required.")
                    else:
                        try:
                            run_query("INSERT INTO MEMBER_CONDITION (EMAIL, CONDITION_NAME, SEVERITY, NOTES) VALUES (?, ?, ?, ?)", (email, cond, severity, notes))
                            st.success("Condition added.")
                            st.rerun() # FIX: Refresh app state
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            st.info("Add members first before conditions.")

    with tab_view:
        st.subheader("View Conditions")
        df = fetch_df("SELECT * FROM MEMBER_CONDITION") if table_exists("MEMBER_CONDITION") else pd.DataFrame()
        if not df.empty:
            options = ["All"] + sorted(df["SEVERITY"].dropna().unique().tolist())
            severity_filter = st.selectbox("Filter by severity", options=options)
            
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
                    current = row.iloc[0]
                    with st.form("edit_condition_form"):
                        options = ["Mild", "Moderate", "Severe"]
                        try:
                            default_index = options.index(current["SEVERITY"])
                        except ValueError:
                            default_index = 0
                        
                        severity = st.selectbox("Severity", options, index=default_index)
                        notes = st.text_area("Notes", value=current["NOTES"])
                        
                        if st.form_submit_button("Update Condition"):
                            try:
                                run_query("UPDATE MEMBER_CONDITION SET SEVERITY=?, NOTES=? WHERE EMAIL=? AND CONDITION_NAME=?", (severity, notes, email_sel, cond_sel))
                                st.success("Condition updated.")
                                st.rerun() # FIX: Refresh app state
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
            if st.button("Delete Condition", type="primary"):
                email_sel, cond_sel = [s.strip() for s in sel.split("|")]
                try:
                    run_query("DELETE FROM MEMBER_CONDITION WHERE EMAIL=? AND CONDITION_NAME=?", (email_sel, cond_sel))
                    st.success("Condition deleted.")
                    st.rerun() # FIX: Refresh app state
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
    - Built with **Streamlit**, **SQLite3**, **Pandas**, and **Altair**.
    - Supports full CRUD for members, assessments, and health conditions.
    - Includes dashboard metrics and interactive charts for quick insights.

    Project by Muhammad Aiman, University of Sheffield.
    """)

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.caption("Project: Fitness Centre Database")
