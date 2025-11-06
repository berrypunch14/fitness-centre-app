import streamlit as st
import sqlite3
import pandas as pd

# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_connection():
    conn = sqlite3.connect('fitness_centre.db', check_same_thread=False)
    return conn

conn = get_connection()
cursor = conn.cursor()

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def view_table(table_name):
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    return df

def execute_query(query, params=()):
    cursor.execute(query, params)
    conn.commit()

# -----------------------------
# APP UI
# -----------------------------
st.set_page_config(page_title="Fitness Centre Database", layout="wide")
st.title("🏋️‍♀️ Fitness Centre Database Management")

menu = ["Home", "Manage Members", "Member Assessments", "Member Conditions"]
choice = st.sidebar.selectbox("Navigation", menu)

# -----------------------------
# HOME
# -----------------------------
if choice == "Home":
    st.write("""
    ### Welcome to the Fitness Centre Database App
    Use the sidebar to navigate between different sections:
    - **Manage Members**: Add, update, or delete member profiles  
    - **Member Assessments**: Record physical assessments  
    - **Member Conditions**: Track health conditions
    """)

# -----------------------------
# MANAGE MEMBERS
# -----------------------------
elif choice == "Manage Members":
    st.subheader("👥 Manage Members")

    tab1, tab2, tab3 = st.tabs(["Add Member", "View / Edit Members", "Delete Member"])

    with tab1:
        st.write("### Add New Member")
        email = st.text_input("Email")
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        gender = st.selectbox("Gender", ["Male", "Female", "Other"])

        if st.button("Add Member"):
            try:
                execute_query("INSERT INTO MEMBER (EMAIL, FIRST_NAME, LAST_NAME, GENDER) VALUES (?, ?, ?, ?)",
                              (email, first_name, last_name, gender))
                st.success(f"Member {first_name} {last_name} added successfully!")
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.write("### View / Edit Members")
        df = view_table("MEMBER")
        st.dataframe(df)

    with tab3:
        st.write("### Delete Member")
        members = [row[0] for row in cursor.execute("SELECT EMAIL FROM MEMBER").fetchall()]
        selected_email = st.selectbox("Select Member Email", members)
        if st.button("Delete Member"):
            execute_query("DELETE FROM MEMBER WHERE EMAIL = ?", (selected_email,))
            st.success(f"Member with email {selected_email} deleted successfully!")

# -----------------------------
# MEMBER ASSESSMENTS
# -----------------------------
elif choice == "Member Assessments":
    st.subheader("📊 Member Assessments")

    tab1, tab2 = st.tabs(["Add Assessment", "View Assessments"])

    with tab1:
        st.write("### Add New Assessment")
        members = [row[0] for row in cursor.execute("SELECT EMAIL FROM MEMBER").fetchall()]
        email = st.selectbox("Select Member Email", members)
        date = st.date_input("Assessment Date")
        height = st.number_input("Height (cm)", min_value=0.0)
        bmi = st.number_input("BMI", min_value=0.0)
        bp = st.number_input("Blood Pressure", min_value=0.0)
        hr = st.number_input("Heart Rate", min_value=0.0)
        weight = st.number_input("Weight (kg)", min_value=0.0)

        if st.button("Add Assessment"):
            try:
                execute_query("""
                    INSERT INTO MEMBER_ASSESSMENT (EMAIL, ASSESSMENT_DATE, HEIGHT, BMI, BLOOD_PRESSURE, HEART_RATE, WEIGHT)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (email, date, height, bmi, bp, hr, weight))
                st.success(f"Assessment added for {email} on {date}")
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.write("### View Assessments")
        df = view_table("MEMBER_ASSESSMENT")
        st.dataframe(df)

# -----------------------------
# MEMBER CONDITIONS
# -----------------------------
elif choice == "Member Conditions":
    st.subheader("⚕️ Member Conditions")

    tab1, tab2 = st.tabs(["Add Condition", "View Conditions"])

    with tab1:
        st.write("### Add New Condition")
        members = [row[0] for row in cursor.execute("SELECT EMAIL FROM MEMBER").fetchall()]
        email = st.selectbox("Select Member Email", members)
        condition = st.text_input("Condition Name")
        severity = st.selectbox("Severity", ["Mild", "Moderate", "Severe"])
        notes = st.text_area("Notes")

        if st.button("Add Condition"):
            try:
                execute_query("""
                    INSERT INTO MEMBER_CONDITION (EMAIL, CONDITION_NAME, SEVERITY, NOTES)
                    VALUES (?, ?, ?, ?)
                """, (email, condition, severity, notes))
                st.success(f"Condition '{condition}' added for {email}")
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.write("### View Member Conditions")
        df = view_table("MEMBER_CONDITION")
        st.dataframe(df)
