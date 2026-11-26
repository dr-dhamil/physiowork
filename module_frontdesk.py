import datetime
import streamlit as st
from db_manager import (
    col_val,
    filter_by_clinic,
    get_branches_list,
    get_data,
    get_therapists_list,
    save_data,
    update_appointment_status,
)


def render_frontdesk_page(active_clinic: str, patients_all):
    st.markdown('<div class="ui-card"><div class="section-heading">Book Appointment & Check-In</div>', unsafe_allow_html=True)
    pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
    name_col = col_val(patients_all, ["name", "Name"])
    branches = get_branches_list()
    therapists = get_therapists_list()

    if patients_all.empty or not pid_col:
        st.warning("Register a patient first under **Patient Registration** to add to the queue.")
    else:
        patient_ids = patients_all[pid_col].tolist()

        def _fmt(pid):
            if name_col:
                match = patients_all[patients_all[pid_col] == pid]
                if not match.empty:
                    return f"{pid} • {match.iloc[0][name_col]}"
            return pid

        with st.form("queue_booking_form"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                q_pid = st.selectbox("Patient*", patient_ids, format_func=_fmt, key="q_pid")
                q_date = st.date_input("Date*", datetime.date.today(), key="q_date_input")
            with c2:
                q_slot = st.selectbox(
                    "Time Slot*",
                    [
                        "09:00 AM", "09:45 AM", "10:30 AM", "11:15 AM", "12:00 PM",
                        "04:00 PM", "04:45 PM", "05:30 PM", "06:15 PM", "07:00 PM",
                    ],
                )
                q_type = st.selectbox(
                    "Visit Type*",
                    ["Initial Assessment", "Follow-Up Therapy", "Reassessment", "Home Program Review"],
                )
            with c3:
                q_therapist = st.selectbox("Assigned Therapist*", therapists, key="q_therapist")
                q_clinic = branches[0] if active_clinic == "All Clinics" else active_clinic
                st.text_input("Clinic Location", value=q_clinic, disabled=True)
            with c4:
                q_status = st.selectbox("Queue Status*", ["Scheduled", "Checked-In", "In-Session", "Completed"])
                q_note = st.text_input("Front-Desk Note", placeholder="e.g., Walk-in / Package #3")

            if st.form_submit_button("Add to Front-Desk Board"):
                appt_id = f"APT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                p_match = patients_all[patients_all[pid_col] == q_pid]
                p_label = f"{q_pid} - {p_match.iloc[0][name_col]}" if (name_col and not p_match.empty) else q_pid
                save_data(
                    "appointments",
                    {
                        "appointment_id": appt_id,
                        "patient_id": q_pid,
                        "patient_name": p_label,
                        "clinic": q_clinic,
                        "appointment_date": str(q_date),
                        "time_slot": q_slot,
                        "visit_type": q_type,
                        "therapist": q_therapist,
                        "status": q_status,
                        "note": q_note.strip(),
                    },
                )
                st.success(f"Added `{appt_id}` ({p_label}) to queue.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ui-card"><div class="section-heading">Live Front-Desk Queue Board</div>', unsafe_allow_html=True)
    raw_appts = filter_by_clinic(get_data("appointments"), active_clinic)
    if raw_appts.empty:
        st.info("No appointments in the queue yet.")
    else:
        f1, f2 = st.columns(2)
        with f1:
            view_date = st.date_input("Filter by Date", datetime.date.today(), key="board_date")
        with f2:
            status_filter = st.multiselect(
                "Filter by Status",
                ["Scheduled", "Checked-In", "In-Session", "Completed"],
                default=["Scheduled", "Checked-In", "In-Session", "Completed"],
            )

        d_col = col_val(raw_appts, ["appointment_date", "Appointment_Date"])
        s_col = col_val(raw_appts, ["status", "Status"])
        id_col = col_val(raw_appts, ["appointment_id", "Appointment_ID"])

        filtered_appts = raw_appts.copy()
        if d_col:
            filtered_appts = filtered_appts[filtered_appts[d_col] == str(view_date)]
        if s_col and status_filter:
            filtered_appts = filtered_appts[filtered_appts[s_col].isin(status_filter)]

        st.dataframe(filtered_appts, width="stretch", hide_index=True)

        if id_col and s_col and not filtered_appts.empty:
            st.markdown("**Quick Queue Status Update**")
            u1, u2, u3 = st.columns([2, 2, 1])
            with u1:
                sel_appt_id = st.selectbox("Select Appointment ID", filtered_appts[id_col].tolist())
            with u2:
                next_status = st.selectbox(
                    "Update Status To",
                    ["Scheduled", "Checked-In", "In-Session", "Completed"],
                    key="upd_status_sel",
                )
            with u3:
                st.write("")
                st.write("")
                if st.button("Update"):
                    update_appointment_status(sel_appt_id, next_status)
                    st.success(f"Updated `{sel_appt_id}` -> **{next_status}**")
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
