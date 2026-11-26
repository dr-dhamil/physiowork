import streamlit as st
from db_manager import (
    get_branches_list,
    get_clinic_settings,
    get_staff_directory,
    hash_password,
    save_clinic_settings,
    save_data,
)


def render_admin_panel():
    tab_settings, tab_users = st.tabs(["🏥 Clinic Headers, Branches & Settings", "👥 Staff & Role Management"])

    with tab_settings:
        st.markdown('<div class="ui-card"><div class="section-heading">Modify Application Headers, Branding & Clinic Defaults</div>', unsafe_allow_html=True)
        cfg = get_clinic_settings()

        with st.form("admin_settings_form"):
            c1, c2 = st.columns(2)
            with c1:
                clinic_title = st.text_input("Main Clinic Header Title*", value=cfg.get("clinic_title", "Dr. Geetanjali’s PhysioWorks"))
                clinic_tagline = st.text_input("Sub-Header Tagline*", value=cfg.get("clinic_tagline", ""))
                clinic_badge = st.text_input("Banner Badge Text", value=cfg.get("clinic_badge", "GET THE CARE YOU DESERVE"))
                logo_path = st.text_input("Logo Asset Filename", value=cfg.get("logo_path", "image_500b64.jpg"))
            with c2:
                branches_str = st.text_area(
                    "Clinic Branches (comma-separated)*",
                    value=cfg.get("branches", "A-3 Paschim Vihar, A-4 Paschim Vihar"),
                    height=80,
                )
                therapists_str = st.text_area(
                    "Therapist Roster (comma-separated)*",
                    value=cfg.get("therapists", "Dr. Geetanjali, Dr. Rohan, Dr. Senior Consultant"),
                    height=80,
                )
                s1, s2 = st.columns(2)
                with s1:
                    default_sessions = st.number_input("Default Plan Sessions", min_value=1, value=int(cfg.get("default_sessions", 10)))
                with s2:
                    default_fee_inr = st.number_input("Default Session Fee (INR)", min_value=0, value=int(cfg.get("default_fee_inr", 800)), step=100)

            if st.form_submit_button("Save & Apply Clinic Settings"):
                new_cfg = {
                    "clinic_title": clinic_title.strip(),
                    "clinic_tagline": clinic_tagline.strip(),
                    "clinic_badge": clinic_badge.strip(),
                    "branches": branches_str.strip(),
                    "therapists": therapists_str.strip(),
                    "default_sessions": int(default_sessions),
                    "default_fee_inr": int(default_fee_inr),
                    "logo_path": logo_path.strip() or "image_500b64.jpg",
                }
                save_clinic_settings(new_cfg)
                st.success("Clinic headers and global settings updated! Reloading...")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_users:
        st.markdown('<div class="ui-card"><div class="section-heading">Create New Staff Account & Assign Role</div>', unsafe_allow_html=True)
        branches = get_branches_list()
        with st.form("admin_create_user_form"):
            u1, u2, u3 = st.columns(3)
            with u1:
                s_name = st.text_input("Staff Full Name*")
                s_email = st.text_input("Login Email / Staff ID*")
            with u2:
                s_role = st.selectbox("Access Role*", ["Admin / Clinic Owner", "Physiotherapist", "Front Desk"])
                s_clinic = st.selectbox("Assigned Clinic*", branches + ["All Clinics"])
            with u3:
                s_pass = st.text_input("Password / PIN*", type="password")
                s_active = st.checkbox("Account Active", value=True)

            if st.form_submit_button("Create Staff User"):
                if s_name and s_email and s_pass:
                    cur_df = get_staff_directory()
                    new_sid = f"STF-{len(cur_df) + 1:03d}"
                    save_data(
                        "staff_users",
                        {
                            "staff_id": new_sid,
                            "email": s_email.strip().lower(),
                            "password_hash": hash_password(s_pass),
                            "full_name": s_name.strip(),
                            "role": s_role,
                            "assigned_clinic": s_clinic,
                            "active": s_active,
                        },
                    )
                    st.success(f"User **{s_name}** (`{new_sid}`) created under **{s_role}**.")
                    st.rerun()
                else:
                    st.error("Please fill in Full Name, Login Email/ID, and Password.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="ui-card"><div class="section-heading">Registered Clinic Users</div>', unsafe_allow_html=True)
        s_disp = get_staff_directory().copy()
        if "password_hash" in s_disp.columns:
            s_disp = s_disp.drop(columns=["password_hash"])
        st.dataframe(s_disp, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
