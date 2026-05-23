import streamlit as st
import os
import random
import string
from PIL import Image

# Setup local storage directory for Teacher ID photos
UPLOAD_DIR = "teacher_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Generate a unique 6-character Class Code for co-teachers
def generate_class_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Initialize data stores in session state
if "teachers_db" not in st.session_state:
    st.session_state.teachers_db = {}  # {username: {password, name, job_title, photo_path}}

if "classes_db" not in st.session_state:
    # { class_code: { class_name: str, year_group: str, teachers: [username], students: [] } }
    st.session_state.classes_db = {
        "Y6MATH": {
            "class_name": "Set 1 Mathematics",
            "year_group": "Year 6",
            "teachers": [],
            "students": [
                {"name": "Oliver Smith", "points": 0, "sanctions": []},
                {"name": "Amelie Jones", "points": 3, "sanctions": ["🌟 Merit: Excellent contribution to group work (+1)"]}
            ]
        }
    }

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

st.title("🇬🇧 UK School Behavior & Class Portal")

# --- AUTHENTICATION ROUTING ---
if st.session_state.logged_in_user is None:
    tab1, tab2 = st.tabs(["🔒 Staff Login", "📝 Create Staff Account"])
    
    with tab2:
        st.subheader("Register New Staff Member")
        reg_username = st.text_input("Choose Username / Email", key="reg_user")
        reg_password = st.text_input("Choose Password", type="password", key="reg_pass")
        reg_name = st.text_input("Full Name (e.g., Mr J. Smith / Miss A. Patel)", key="reg_name")
        reg_title = st.selectbox("Role / Job Title", ["Form Tutor", "Subject Teacher", "Head of Year", "Headteacher / SLT", "Teaching Assistant"])
        uploaded_photo = st.file_uploader("Upload Profile Photo for Staff ID Badge", type=["jpg", "jpeg", "png"])
        
        if st.button("Register Account"):
            if reg_username and reg_password and reg_name and uploaded_photo:
                if reg_username in st.session_state.teachers_db:
                    st.error("Username already registered.")
                else:
                    photo_path = os.path.join(UPLOAD_DIR, f"{reg_username}.png")
                    img = Image.open(uploaded_photo)
                    img.save(photo_path)
                    
                    st.session_state.teachers_db[reg_username] = {
                        "password": reg_password,
                        "name": reg_name,
                        "role": reg_title,
                        "photo_path": photo_path
                    }
                    st.success("Staff account created. Please now log in.")
            else:
                st.warning("Please complete all sections and upload a photo.")

    with tab1:
        st.subheader("Staff Sign In")
        login_username = st.text_input("Username", key="log_user")
        login_password = st.text_input("Password", type="password", key="log_pass")
        
        if st.button("Log In"):
            if login_username in st.session_state.teachers_db:
                user_data = st.session_state.teachers_db[login_username]
                if user_data["password"] == login_password:
                    st.session_state.logged_in_user = login_username
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("Staff record not found.")

# --- MAIN APP INTERFACE (LOGGED IN) ---
else:
    current_user = st.session_state.logged_in_user
    teacher_info = st.session_state.teachers_db[current_user]
    
    # Sidebar: UK Staff ID Badge
    with st.sidebar:
        st.subheader("🪪 School ID Badge")
        if os.path.exists(teacher_info["photo_path"]):
            st.image(teacher_info["photo_path"], width=150)
        st.markdown(f"### **{teacher_info['name']}**")
        st.markdown(f"*{teacher_info['role']}*")
        st.caption(f"Staff Ref: {current_user}")
        
        st.divider()
        if st.button("🚪 Log Out"):
            st.session_state.logged_in_user = None
            st.rerun()

    # Get classes linked to this teacher
    my_classes = {
        ccode: cdata for ccode, cdata in st.session_state.classes_db.items() 
        if current_user in cdata["teachers"]
    }

    tab_classes, tab_students, tab_sanctions = st.tabs([
        "🏫 Class Setup & Subject Teachers", 
        "📋 Class Registers", 
        "⚖️ Merits & Sanctions"
    ])

    # TAB 1: UK CLASS MANAGEMENT & JOINT TEACHING
    with tab_classes:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Set Up a New Class/Form")
            with st.form("create_class_form", clear_on_submit=True):
                new_class_name = st.text_input("Class Name (e.g., 9B/Ma1, Red House Form)")
                year_group = st.selectbox("Year Group", [f"Year {i}" for i in range(1, 14)] + ["Reception"])
                create_btn = st.form_submit_button("Create Class")
                
                if create_btn and new_class_name:
                    code = generate_class_code()
                    st.session_state.classes_db[code] = {
                        "class_name": new_class_name,
                        "year_group": year_group,
                        "teachers": [current_user],
                        "students": []
                    }
                    st.success(f"Class created! Share this Code with Subject Teachers: **{code}**")
                    st.rerun()
        
        with col2:
            st.subheader("Join Class as a Subject Teacher")
            st.caption("Enter the shared 6-digit Class Code provided by the Form Tutor or Lead Teacher.")
            with st.form("join_class_form", clear_on_submit=True):
                join_code = st.text_input("Class Code").upper().strip()
                join_btn = st.form_submit_button("Link to Class")
                
                if join_btn and join_code:
                    if join_code in st.session_state.classes_db:
                        if current_user in st.session_state.classes_db[join_code]["teachers"]:
                            st.warning("You are already linked to this class roster.")
                        else:
                            st.session_state.classes_db[join_code]["teachers"].append(current_user)
                            st.success(f"Linked successfully to {st.session_state.classes_db[join_code]['class_name']}!")
                            st.rerun()
                    else:
                        st.error("Invalid Class Code. Please check with the class creator.")

        st.divider()
        st.subheader("Your Assigned Classes")
        if not my_classes:
            st.info("You are not assigned to any classes yet. Create one or join using a code.")
        else:
            for ccode, cdata in my_classes.items():
                staff_list = []
                for username in cdata["teachers"]:
                    t_details = st.session_state.teachers_db.get(username, {})
                    staff_list.append(f"{t_details.get('name', username)} ({t_details.get('role', 'Teacher')})")
                
                with st.expander(f"📚 {cdata['year_group']} - {cdata['class_name']} (Code: {ccode})"):
                    st.write(f"**Associated Staff:** {', '.join(staff_list)}")
                    st.write(f"**Pupils on Roll:** {len(cdata['students'])}")

    # TAB 2: REGISTER / PUPIL MANAGEMENT
    with tab_students:
        st.subheader("Manage Pupil Lists")
        if not my_classes:
            st.warning("Please set up or link to a class before adding pupils.")
        else:
            class_options = {ccode: f"{cdata['year_group']} - {cdata['class_name']}" for ccode, cdata in my_classes.items()}
            selected_code = st.selectbox("Select Class to View", list(class_options.keys()), format_func=lambda x: class_options[x], key="pupil_class_select")
            
            with st.form("add_pupil_form", clear_on_submit=True):
                pupil_name = st.text_input("Pupil Full Name")
                add_pupil_btn = st.form_submit_button("Add Pupil to Roll")
                
                if add_pupil_btn and pupil_name:
                    st.session_state.classes_db[selected_code]["students"].append({
                        "name": pupil_name,
                        "points": 0,
                        "sanctions": []
                    })
                    st.success(f"Added {pupil_name} to the roster.")
            
            st.write("### Class Register")
            current_pupils = st.session_state.classes_db[selected_code]["students"]
            if not current_pupils:
                st.info("No pupils registered in this class yet.")
            else:
                for p in current_pupils:
                    st.write(f"- **{p['name']}** (Net House Points / Behavior Score: {p['points']} pts)")

    # TAB 3: UK SANCTIONS & MERITS
    with tab_sanctions:
        st.subheader("Log Behavior Incidents & Rewards")
        if not my_classes:
            st.warning("You must be linked to a class to issue points or sanctions.")
        else:
            class_options = {ccode: f"{cdata['year_group']} - {cdata['class_name']}" for ccode, cdata in my_classes.items()}
            s_code = st.selectbox("Select Class", list(class_options.keys()), format_func=lambda x: class_options[x], key="sanc_class_select")
            
            pupil_list = st.session_state.classes_db[s_code]["students"]
            
            if not pupil_list:
                st.info("No pupils registered in this class.")
            else:
                pupil_names = [p["name"] for p in pupil_list]
                selected_pupil_name = st.selectbox("Select Pupil", pupil_names)
                
                pupil_idx = pupil_names.index(selected_pupil_name)
                pupil = pupil_list[pupil_idx]
                
                category = st.selectbox("Action Category", [
                    "🌟 Positive: Merit / House Point", 
                    "🌟 Positive: Headteacher's Award",
                    "⚠️ Sanction: C1 (First Warning)", 
                    "⚠️ Sanction: C2 (Break/Lunch Detention)", 
                    "⚠️ Sanction: C3 (After-School Detention / SLT Escalation)"
                ])
                
                reason = st.text_input("Details / Reason (e.g., Outstanding homework, Disruption during reading session)")
                
                if st.button("Log to Behavior Record"):
                    if reason:
                        if "Merit" in category:
                            val = 1
                            label = "🌟 Merit"
                        elif "Headteacher" in category:
                            val = 3
                            label = "👑 Headteacher Award"
                        elif "C1" in category:
                            val = 0
                            label = "🔸 C1 Warning"
                        elif "C2" in category:
                            val = -1
                            label = "🔻 C2 Detention"
                        else:
                            val = -3
                            label = "🚨 C3 Serious Sanction"
                            
                        pupil["points"] += val
                        log_text = f"{label}: {reason} ({'+' if val>=0 else ''}{val} pts) — Issued by {teacher_info['name']} ({teacher_info['role']})"
                        pupil["sanctions"].append(log_text)
                        
                        st.success(f"Record updated for {selected_pupil_name}. Total Score: {pupil['points']}.")
                    else:
                        st.error("Please insert a brief description for the school record.")
                
                st.divider()
                st.subheader(f"School Behavior History: {selected_pupil_name}")
                if not pupil["sanctions"]:
                    st.info("Clean record. No logged incidents or awards.")
                else:
                    for log in reversed(pupil["sanctions"]):
                        st.write(log)
