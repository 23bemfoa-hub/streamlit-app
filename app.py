import streamlit as st
import random
import string
import base64
from PIL import Image
from io import BytesIO
from datetime import datetime
from supabase import create_client, Client

# --- CONNECTED TO YOUR LIVE DATABASE ---
SUPABASE_URL = "https://mqowcdlsrclpkxmognqg.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xb3djZGxzcmNscGt4bW9nbnFnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzk1NTExNDYsImV4cCI6MjA5NTEyNzE0Nn0.kZPIPosl2Ko_Bjymbs6VTFr7j67DNYyUKfrGNrx8luc"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def generate_class_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

st.title("🇬🇧 UK School Behavior, Attendance & Live SLT Hub")

# --- AUTHENTICATION (PASSWORDLESS VIA CENTRAL DB) ---
if st.session_state.logged_in_user is None:
    tab1, tab2 = st.tabs(["🔒 Staff Sign In (ID Only)", "📝 Create Staff Account"])
    
    with tab2:
        st.subheader("Register New Staff Member")
        reg_school = st.text_input("School Name (e.g., Oakwood Academy)").strip()
        reg_username = st.text_input("Choose a Unique Staff Username", key="reg_user").strip().lower()
        reg_name = st.text_input("Full Name (e.g., Mr J. Smith / Miss A. Patel)", key="reg_name")
        reg_title = st.selectbox("Role / Job Title", ["Form Tutor", "Subject Teacher", "Head of Year", "Headteacher / SLT", "Deputy Head / SLT", "Teaching Assistant"])
        uploaded_photo = st.file_uploader("Upload Profile Photo for Staff ID Badge", type=["jpg", "jpeg", "png"])
        
        if st.button("Register Account"):
            if reg_school and reg_username and reg_name and uploaded_photo:
                # Check database if user exists
                existing = supabase.table("teachers").select("username").eq("username", reg_username).execute()
                if existing.data:
                    st.error("This Username is already registered on the network.")
                else:
                    # Convert image to Base64 so it securely syncs across all devices globally
                    img = Image.open(uploaded_photo)
                    img.thumbnail((300, 300)) # Compress slightly for fast network loading
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    # Insert record into central cloud database
                    supabase.table("teachers").insert({
                        "username": reg_username,
                        "name": reg_name,
                        "role": reg_title,
                        "school": reg_school,
                        "photo_url": img_str # Safe device-to-device image string
                    }).execute()
                    
                    st.success(f"Staff account created centrally! Log in using: **{reg_username}**")
            else:
                st.warning("Please complete all sections and upload a photo.")

    with tab1:
        st.subheader("Staff Sign In")
        login_username = st.text_input("Staff Username", key="log_user").strip().lower()
        
        if st.button("Sign In"):
            user_query = supabase.table("teachers").select("*").eq("username", login_username).execute()
            if user_query.data:
                st.session_state.logged_in_user = user_query.data[0]
                st.rerun()
            else:
                st.error("Staff Username not found on the database network.")

# --- MAIN APP INTERFACE (LOGGED IN TO GLOBAL DB) ---
else:
    teacher_info = st.session_state.logged_in_user
    current_user = teacher_info["username"]
    my_school = teacher_info["school"]
    is_slt = "SLT" in teacher_info["role"] or "Headteacher" in teacher_info["role"]
    
    # Initialize school alert queue if empty
    try:
        supabase.table("slt_alerts").select("id").limit(1).execute()
    except Exception:
        pass # Handled by table existence

    # Sidebar Badge Display
    with st.sidebar:
        st.subheader("🪪 School ID Badge")
        if teacher_info.get("photo_url"):
            try:
                # Render central base64 image onto the badge natively
                img_data = base64.b64decode(teacher_info["photo_url"])
                st.image(img_data, width=150)
            except Exception:
                st.caption("📷 Image format error")
        st.markdown(f"### **{teacher_info['name']}**")
        st.markdown(f"*{teacher_info['role']}*")
        st.caption(f"🏫 {my_school}")
        
        st.divider()
        if st.button("🚪 Log Out"):
            st.session_state.logged_in_user = None
            st.rerun()

    # --- REALTIME SLT ALERTS NETWORK QUERY ---
    alerts_query = supabase.table("slt_alerts").select("*").eq("school", my_school).eq("status", "⚠️ Active").execute()
    active_school_alerts = alerts_query.data
    
    if active_school_alerts:
        if is_slt:
            st.error(f"🚨 **CRITICAL ALERT: {len(active_school_alerts)} Active SLT Callout(s) Requested!**")
            for alert in active_school_alerts:
                with st.expander(f"🔴 CALLOUT: Room {alert['room']} ({alert['time']})", expanded=True):
                    st.write(f"**Staff Member:** {alert['sender']}")
                    st.write(f"**Situation:** {alert['reason']}")
                    if st.button("✅ Clear Callout", key=f"clear_{alert['id']}"):
                        supabase.table("slt_alerts").update({"status": "Resolved"}).eq("id", alert["id"]).execute()
                        st.rerun()
        else:
            st.warning(f"⚠️ Active emergency SLT assistance has been requested to Room {active_school_alerts[0]['room']}.")

    # Fetch all classes belonging to this specific school where current user is listed as a teacher
    classes_query = supabase.table("classes").select("*").eq("school", my_school).execute()
    my_classes = [c for c in classes_query.data if current_user in c["teachers"]]

    tab_classes, tab_register, tab_sanctions, tab_callout = st.tabs([
        "🏫 Class Setup", 
        "📝 Class Registers & Attendance", 
        "⚖️ Merits & Sanctions",
        "🚨 Emergency SLT Callout"
    ])

    # TAB 1: CLASS CONFIGURATION
    with tab_classes:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Set Up a New Class/Form")
            with st.form("create_class_form", clear_on_submit=True):
                new_class_name = st.text_input("Class Name (e.g., 9B/Ma1)")
                year_group = st.selectbox("Year Group", [f"Year {i}" for i in range(1, 14)] + ["Reception"])
                create_btn = st.form_submit_button("Create Class")
                
                if create_btn and new_class_name:
                    code = generate_class_code()
                    supabase.table("classes").insert({
                        "class_code": code,
                        "class_name": new_class_name,
                        "year_group": year_group,
                        "school": my_school,
                        "teachers": [current_user],
                        "students": []
                    }).execute()
                    st.success(f"Class saved globally! Roster Code: **{code}**")
                    st.rerun()
        
        with col2:
            st.subheader("Link to Existing Class Code")
            with st.form("join_class_form", clear_on_submit=True):
                join_code = st.text_input("Class Code").upper().strip()
                join_btn = st.form_submit_button("Link To Class")
                
                if join_btn and join_code:
                    class_data = supabase.table("classes").select("*").eq("class_code", join_code).execute()
                    if class_data.data:
                        target = class_data.data[0]
                        if current_user not in target["teachers"]:
                            updated_teachers = target["teachers"] + [current_user]
                            supabase.table("classes").update({"teachers": updated_teachers}).eq("class_code", join_code).execute()
                            st.success("Successfully linked as co-teacher!")
                            st.rerun()
                        else:
                            st.warning("You are already linked to this class setup.")
                    else:
                        st.error("Roster Code not found.")

        st.divider()
        st.subheader("Your Active Classes")
        for c in my_classes:
            st.markdown(f"- **{c['year_group']} - {c['class_name']}** (Code Shared: `{c['class_code']}` | Pupils: {len(c['students'])})")

    # TAB 2: BULK REGISTERS & ATTENDANCE 
    with tab_register:
        st.subheader("Class Registers")
        if not my_classes:
            st.info("No active classes linked to your profile.")
        else:
            class_options = {c["class_code"]: f"{c['year_group']} - {c['class_name']}" for c in my_classes}
            selected_code = st.selectbox("Select Class to Register", list(class_options.keys()), format_func=lambda x: class_options[x], key="reg_select")
            
            # Fetch fresh row status from DB
            selected_class = supabase.table("classes").select("*").eq("class_code", selected_code).execute().data[0]
            pupils = selected_class["students"]
            
            with st.expander("📥 Bulk Paste New Pupils to Roll"):
                with st.form("bulk_add", clear_on_submit=True):
                    raw_names = st.text_area("Paste name listing (One per line)")
                    add_btn = st.form_submit_button("Import")
                    if add_btn and raw_names:
                        for line in raw_names.split("\n"):
                            if line.strip():
                                pupils.append({"name": line.strip(), "points": 0, "sanctions": [], "attendance": "Present ( / )"})
                        supabase.table("classes").update({"students": pupils}).eq("class_code", selected_code).execute()
                        st.success("Roster expanded!")
                        st.rerun()

            if not pupils:
                st.info("No pupils on roll for this selection.")
            else:
                st.write("#### Attendance Configuration Grid")
                st.caption("Changes are synced immediately to the database network.")
                changed = False
                for idx, p in enumerate(pupils):
                    c1, c2 = st.columns([2, 2])
                    c1.write(f"**{p['name']}**")
                    possible_marks = ["Present ( / )", "Absent ( N )", "Late ( L )", "Medical ( M )"]
                    cur_att = p.get("attendance", "Present ( / )")
                    att_idx = possible_marks.index(cur_att) if cur_att in possible_marks else 0
                    
                    status = c2.selectbox(f"Mark {p['name']}", possible_marks, index=att_idx, key=f"p_att_{idx}", label_visibility="collapsed")
                    if status != cur_att:
                        p["attendance"] = status
                        changed = True
                
                if changed:
                    supabase.table("classes").update({"students": pupils}).eq("class_code", selected_code).execute()
                    st.toast("Attendance synchronization updated live!", icon="💾")

    # TAB 3: MERITS & SANCTIONS MATRIX
    with tab_sanctions:
        st.subheader("Log Actions")
        if not my_classes:
            st.info("Create or join a class to manage metrics.")
        else:
            class_options = {c["class_code"]: f"{c['year_group']} - {c['class_name']}" for c in my_classes}
            s_code = st.selectbox("Select Target Class", list(class_options.keys()), format_func=lambda x: class_options[x])
            
            selected_class = supabase.table("classes").select("*").eq("class_code", s_code).execute().data[0]
            pupils = selected_class["students"]
            
            if not pupils:
                st.info("Roster empty.")
            else:
                p_names = [p["name"] for p in pupils]
                selected_p = st.selectbox("Select Pupil", p_names)
                p_idx = p_names.index(selected_p)
                pupil = pupils[p_idx]
                
                category = st.selectbox("Action Tiers", ["🌟 Positive: Merit / House Point", "🌟 Positive: Headteacher's Award", "⚠️ Sanction: C1 (First Warning)", "⚠️ Sanction: C2 (Break/Lunch Detention)", "⚠️ Sanction: C3 (After-School Detention / SLT Escalation)"])
                reason = st.text_input("Incident / Commendation Entry Details")
                
                if st.button("Publish Log to Cloud Record"):
                    if reason:
                        val = 1 if "Merit" in category else (3 if "Headteacher" in category else (0 if "C1" in category else (-1 if "C2" in category else -3)))
                        pupil["points"] = pupil.get("points", 0) + val
                        if "sanctions" not in pupil: pupil["sanctions"] = []
                        pupil["sanctions"].append(f"{category}: {reason} ({'+' if val>=0 else ''}{val} pts) — By {teacher_info['name']}")
                        
                        supabase.table("classes").update({"students": pupils}).eq("class_code", s_code).execute()
                        st.success("Central records successfully updated!")
                        st.rerun()
                
                st.divider()
                st.subheader("Historical Log Listing")
                for log in reversed(pupil.get("sanctions", [])):
                    st.caption(log)

    # TAB 4: 🚨 LIVE REALTIME CALLOUT ENGINE
    with tab_callout:
        st.subheader("🚨 Trigger Live School SLT Emergency Intervention")
        with st.form("emergency_dispatch", clear_on_submit=True):
            room = st.text_input("Target Classroom / Room Identifier (e.g., Block B - Room 102)")
            details = st.text_area("Critical Incident Description")
            dispatch_btn = st.form_submit_button("🔴 SEND CENTRAL SLT DISPATCH ALERT")
            
            if dispatch_btn and room and details:
                supabase.table("slt_alerts").insert({
                    "school": my_school,
                    "sender": f"{teacher_info['name']} ({teacher_info['role']})",
                    "room": room,
                    "reason": details,
                    "time": datetime.now().strftime("%H:%M:%S")
                }).execute()
                st.error("Central Alert Broadcasted! Every active SLT dashboard viewport in your school is now pinging.")
