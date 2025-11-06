import streamlit as st
import sqlite3

# --- DATABASE SETUP ---
conn = sqlite3.connect('fitness_centre.db')
c = conn.cursor()

# Create table if not exists
c.execute('''
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        membership_type TEXT
    )
''')
conn.commit()

# --- FUNCTIONS ---
def add_member(name, age, membership_type):
    c.execute('INSERT INTO members (name, age, membership_type) VALUES (?, ?, ?)', (name, age, membership_type))
    conn.commit()

def view_members():
    c.execute('SELECT * FROM members')
    return c.fetchall()

def delete_member(member_id):
    c.execute('DELETE FROM members WHERE id=?', (member_id,))
    conn.commit()

def update_member(member_id, name, age, membership_type):
    c.execute('UPDATE members SET name=?, age=?, membership_type=? WHERE id=?', (name, age, membership_type, member_id))
    conn.commit()

# --- STREAMLIT UI ---
st.title("🏋️‍♂️ Fitness Centre Database App")

menu = ["Add Member", "View Members", "Update Member", "Delete Member"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Add Member":
    st.subheader("Add New Member")
    name = st.text_input("Name")
    age = st.number_input("Age", min_value=0)
    membership_type = st.selectbox("Membership Type", ["Monthly", "Quarterly", "Yearly"])
    if st.button("Add Member"):
        add_member(name, age, membership_type)
        st.success(f"Member '{name}' added successfully!")

elif choice == "View Members":
    st.subheader("View All Members")
    members = view_members()
    for m in members:
        st.write(m)

elif choice == "Update Member":
    st.subheader("Update Member Details")
    members = view_members()
    member_ids = [m[0] for m in members]
    selected_id = st.selectbox("Select Member ID", member_ids)
    name = st.text_input("New Name")
    age = st.number_input("New Age", min_value=0)
    membership_type = st.selectbox("New Membership Type", ["Monthly", "Quarterly", "Yearly"])
    if st.button("Update"):
        update_member(selected_id, name, age, membership_type)
        st.success("Member updated successfully!")

elif choice == "Delete Member":
    st.subheader("Delete Member")
    members = view_members()
    member_ids = [m[0] for m in members]
    selected_id = st.selectbox("Select Member ID", member_ids)
    if st.button("Delete"):
        delete_member(selected_id)
        st.warning(f"Member with ID {selected_id} deleted.")
