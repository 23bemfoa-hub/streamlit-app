import streamlit as st
import os
import random
import string
from PIL import Image
from datetime import datetime

# Setup local storage directory for Teacher ID photos
UPLOAD_DIR = "teacher_photos"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Generate a unique 6-character Class Code for co-teachers
def generate_class_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- GLOBAL DATA STRUCTURES (Simulating a Shared Network Database) ---
if "teachers_db" not in st.session_state:
    st.session_state.teachers_db = {}  # {username: {name, role, school, photo_path}}

if "classes_db" not in st.session_state:
    st.session_state.classes_db = {
        "Y6MATH": {
            "class_name": "Set 1 Mathematics",
            "year_group": "Year 6",
            "teachers": [],
            "students": [
                {"name": "Oliver Smith", "points": 0, "sanctions": [], "attendance": "Not Marked"},
                {"name": "Amelie Jones", "points": 3, "sanctions": [], "attendance": "Not Marked"}
            ]
        }
    }

# Live Global Alert System { school_name: [ {teacher, room, reason, time, status} ] }
if "slt_alerts" not in st.session_state:
    st.session_state.slt_alerts = {}

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

st.title("🇬🇧 UK School Behavior, Attendance & Live SLT Hub")

# --- AUTHENTICATION ROUTING (PASSWORDLESS) ---
if st.session_state.logged_in_user is None:
    tab1, tab2 = st.tabs(["🔒 Staff Sign In (ID Only)", "📝 Create Staff Account"])
    
    with tab2:
        st.subheader("Register New Staff Member")
        reg_school = st.text_input("School Name (Must match your colleagues exactly, e.g., Oakwood Academy)").strip()
        reg_username = st.text_input("Choose a Unique Staff Username (e.g., jsmith1)", key="reg_user").strip().lower()
        reg_name = st.text_input("Full Name (e.g., Mr J. Smith / Miss A. Patel)", key="reg_name")
        reg_title = st.selectbox("Role / Job Title", ["Form Tutor", "Subject Teacher", "Head of Year", "Headteacher / SLT", "Deputy Head / SLT", "Teaching Assistant"])
        uploaded_photo = st.file_uploader("Upload Profile Photo for Staff ID Badge", type=["jpg", "jpeg", "png"])
        
        if st.button("Register Account"):
            if reg_school and reg_username and reg_name and uploaded_photo:
                if reg_username in st.session_state.teachers_db:
                    st.error("This Username is already registered.")
                else:
                    photo_path = os.path.join(UPLOAD_DIR, f"{reg_username}.png")
                    img = Image.open(uploaded_photo)
                    img.save(photo_path)
                    
                    st.session_state.teachers_db[reg_username] = {
                        "name": reg_name,
                        "role": reg_title,
                        "school": reg_school,
                        "photo_path": photo_path
                    }
                    st.success(f"Staff account created for {reg_school}! Log in using: **{reg_username}**")
            else:
                st.warning("Please complete all sections and upload a photo.")

    with tab1:
        st.subheader("Staff Sign In")
        login_username = st.text_input("Staff Username", key="log_user").strip().lower()
        
        if st.button("Sign In"):
            if login_username in st.session_state.teachers_db:
                st.session_state.logged_in_user = login_username
                st.rerun()
            else:
                st.error("Staff Username not found. Please verify spelling or create an account.")

# --- MAIN APP INTERFACE (LOGGED IN) ---
else:
    current_user = st.session_state.logged_in_user
    teacher_info = st.session_state.teachers_db[current_user]
    my_school = teacher_info["school"]
    is_slt = "SLT" in teacher_info["role"] or "Headteacher" in teacher_info["role"]
    
    # Initialize school alert queue if empty
    if my_school not in st.session_state.slt_alerts:
        st.session_state.slt_alerts[my_school] = []

    # Sidebar: UK Staff ID Badge
    with st.sidebar:
        st.subheader("🪪 School ID Badge")
        if os.path.exists(teacher_info["photo_path"]):
            st.image(teacher_info["photo_path"], width=150)
        st.markdown(f"### **{teacher_info['name']}**")
        st.markdown(f"*{teacher_info['role']}*")
        st.caption(f"🏫 {my_school}")
        st.caption(f"Staff Ref: {current_user}")
        
        st.divider()
        if st.button("🚪 Log Out"):
            st.session_state.logged_in_user = None
            st.rerun()

    # --- 🚨 LIVE SLT CALLOUT PANEL (BANNER SYSTEM) ---
    active_school_alerts = [a for a in st.session_state.slt_alerts[my_school] if a["status"] == "⚠️ Active"]
    
    if active_school_alerts:
        if is_slt:
            st.error(f"🚨 **CRITICAL ALERT: {len(active_school_alerts)} Active SLT Callout(s) Requested!**")
            for idx, alert in enumerate(active_school_alerts):
                with st.expander(f"🔴 CALLOUT: Room {alert['room']} ({alert['time']})", expanded=True):
                    st.write(f"**Staff Member:** {alert['sender']}")
                    st.write(f"**Situation/Reason:** {alert['reason']}")
                    if st.button("✅ Accept & Clear Callout", key=f"clear_{idx}"):
                        alert["status"] = "Resolved"
                        st.success("Callout cleared.")
                        st.rerun()
        else:
            st.warning(f"⚠️ An SLT callout is currently active in your school building (Room {active_school_alerts[0]['room']}).")

    # Get classes linked to this teacher
    my_classes = {
        ccode: cdata for ccode, cdata in st.session_state.classes_db.items() 
        if current_user in cdata["teachers"]
    }

    tab_classes, tab_register, tab_sanctions, tab_callout = st.tabs([
        "🏫 Class Setup", 
        "📝 Class Registers & Attendance", 
        "⚖️ Merits & Sanctions",
        "🚨 Emergency SLT Callout"
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
                        st.error("Invalid Class Code.")

        st.divider()
        st.subheader("Your Assigned Classes")
        if not my_classes:
            st.info("You are not assigned to any classes yet.")
        else:
            for ccode, cdata in my_classes.items():
                with st.expander(f"📚 {cdata['year_group']} - {cdata['class_name']} (Code: {ccode})"):
                    st.write(f"**Pupils on Roll:** {len(cdata['students'])}")

    # TAB 2: REGISTER & ATTENDANCE SYSTEM
    with tab_register:
        st.subheader("Take Class Register")
        if not my_classes:
            st.warning("Please set up or link to a class before checking attendance.")
        else:
            class_options = {ccode: f"{cdata['year_group']} - {cdata['class_name']}" for ccode, cdata in my_classes.items()}
            selected_code = st.selectbox("Select Class to Register", list(class_options.keys()), format_func=lambda x: class_options[x], key="reg_class_select")
            
            # Form to bulk add pupils
            with st.expander("📥 Bulk Import Roster From List"):
                with st.form("bulk_pupil_form", clear_on_submit=True):
                    raw_paste_data = st.text_area("Paste pupil names here (one per line)...", height=100)
                    bulk_import_btn = st.form_submit_button("Extract and Add Pupils")
                    if bulk_import_btn and raw_paste_data:
                        for line in raw_paste_data.split("\n"):
                            if line.strip():
                                st.session_state.classes_db[selected_code]["students"].append({
                                    "name": line.strip(), "points": 0, "sanctions": [], "attendance": "Not Marked"
                                })
                        st.success("Pupils extracted!")
                        st.rerun()

            # Main Register Interface
            pupils = st.session_state.classes_db[selected_code]["students"]
            if not pupils:
                st.info("No pupils registered in this class yet.")
            else:
                st.write("#### Live Attendance Grid")
                st.caption("Select the status for each student on roll:")
                
                # Update status interactively
                for idx, p in enumerate(pupils):
                    col_name, col_status = st.columns([2, 2])
                    with col_name:
                        st.write(f"**{p['name']}**")
                    with col_status:
                        # UK Standard codes: Present (/), Absent (N), Late (L), Medical (M)
                        current_idx = ["Present ( / )", "Absent ( N )", "Late ( L )", "Medical ( M )"].index(
                            f"{p['attendance']}" if p['attendance'] in ["Present ( / )", "Absent ( N )", "Late ( L )", "Medical ( M )"] else "Present ( / )"
                        )
                        status = col_status.selectbox(f"Status for {p['name']}", ["Present ( / )", "Absent ( N )", "Late ( L )", "Medical ( M )"], index=current_idx, label_visibility="collapsed", key=f"att_{idx}")
                        p["attendance"] = status

                st.success("Register configurations automatically saved in session memory!")

    # TAB 3: UK SANCTIONS & MERITS
    with tab_sanctions:
        st.subheader("Log Behavior Incidents & Rewards")
        if not my_classes:
            st.warning("You must be linked to a class to issue points.")
        else:
            class_options = {ccode: f"{cdata['year_group']} - {cdata['class_name']}" for ccode, cdata in my_classes.items()}
            s_code = st.selectbox("Select Class", list(class_options.keys()), format_func=lambda x: class_options[x], key="sanc_class_select")
            
            pupil_list = st.session_state.classes_db[s_code]["students"]
            if not pupil_list:
                st.info("No pupils registered in this class.")
            else:
                pupil_names = [p["name"] for p in pupil_list]
                selected_pupil_name = st.selectbox("Select Pupil", pupil_names)
                pupil = pupil_list[pupil_names.index(selected_pupil_name)]
                
                category = st.selectbox("Action Category", ["🌟 Positive: Merit / House Point", "🌟 Positive: Headteacher's Award", "⚠️ Sanction: C1 (First Warning)", "⚠️ Sanction: C2 (Break/Lunch Detention)", "⚠️ Sanction: C3 (After-School Detention / SLT Escalation)"])
                reason = st.text_input("Details / Reason")
                
                if st.button("Log to Behavior Record"):
                    if reason:
                        val = 1 if "Merit" in category else (3 if "Headteacher" in category else (0 if "C1" in category else (-1 if "C2" in category else -3)))
                        pupil["points"] += val
                        pupil["sanctions"].append(f"{category}: {reason} ({'+' if val>=0 else ''}{val} pts) — By {teacher_info['name']}")
                        st.success("Record updated!")
                    else:
                        st.error("Please insert a description.")

    # TAB 4: 🚨 LIVE SLT EMERGENCY CALLOUT
    with tab_callout:
        st.subheader("🚨 Request Direct SLT Intervention")
        st.write("Use this *only* if immediate assistance is required in your classroom for safety or severe behavioral crises.")
        
        with st.form("slt_callout_form", clear_on_submit=True):
            room_number = st.text_input("Your Current Room Number / Location (e.g., Room 14 / Science Lab 2)")
            incident_details = st.text_area("Brief nature of crisis (e.g., Severe safety risk, Refusal to leave room on C3 exit)")
            submit_callout = st.form_submit_button("🔴 TRIGGER EMERGENCY SLT CALLOUT")
            
            if submit_callout:
                if room_number and incident_details:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    new_alert = {
                        "sender": f"{teacher_info['name']} ({teacher_info['role']})",
                        "room": room_number,
                        "reason": incident_details,
                        "time": timestamp,
                        "status": "⚠️ Active"
                    }
                    st.session_state.slt_alerts[my_school].append(new_alert)
                    st.error(f"Emergency callout issued at {timestamp}. All SLT members at {my_school} have been alerted.")
                else:
                    st.warning("Please specify your location and reason for callout.")
