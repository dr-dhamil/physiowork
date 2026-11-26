import datetime
import streamlit as st
from anatomy_3d import render_ecorche_3d_viewer
from db_manager import (
    col_val,
    get_branches_list,
    get_clinic_settings,
    get_therapists_list,
    save_data,
)

BODY_REGIONS = [
    "Cervical Spine (Neck)",
    "Thoracic Spine (Upper Back)",
    "Lumbar Spine (Lower Back)",
    "Shoulder Complex",
    "Elbow",
    "Wrist & Hand",
    "Hip & Groin",
    "Knee Joint",
    "Ankle & Foot",
    "TMJ / Jaw",
]


def render_assessment_page(active_clinic: str, patients_all, assessments_all, banner_fn):
    pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
    name_col = col_val(patients_all, ["name", "Name"])
    branches = get_branches_list()
    therapists = get_therapists_list()
    cfg = get_clinic_settings()

    if patients_all.empty or not pid_col:
        st.warning("Register a patient first under **Patient Registration**.")
        return

    patient_ids = patients_all[pid_col].tolist()

    def _fmt(pid):
        if name_col:
            match = patients_all[patients_all[pid_col] == pid]
            if not match.empty:
                return f"{pid} • {match.iloc[0][name_col]}"
        return pid

    selected_patient = st.selectbox("Select Patient", patient_ids, format_func=_fmt)
    banner_fn(patients_all, selected_patient)

    if not assessments_all.empty:
        asm_pid_col = col_val(assessments_all, ["patient_id", "Patient_ID"])
        if asm_pid_col:
            p_asm = assessments_all[assessments_all[asm_pid_col] == selected_patient]
            if not p_asm.empty:
                with st.expander(f"📂 Past Assessments for {selected_patient} ({len(p_asm)})"):
                    st.dataframe(p_asm, width="stretch", hide_index=True)

    st.markdown('<div class="ui-card"><div class="section-heading">1. 3D Musculoskeletal Ecorche Pain Map & Region Selection</div>', unsafe_allow_html=True)
    col_map, col_reg = st.columns([1.15, 1.15])

    with col_map:
        render_ecorche_3d_viewer(st.session_state.get("asm_body_parts", []))

    with col_reg:
        body_parts = st.multiselect("Affected Body Region(s)*:", BODY_REGIONS, key="asm_body_parts")
        pain_spot_notes = st.text_input(
            "Pinned Muscle / Joint Location Note",
            placeholder="e.g., #1 Right Anterior Deltoid / Biceps Long Head Tendon",
            key="asm_pain_spots",
        )

        st.markdown("**Pain Intensity & Irritability (NPRS 0–10)**")
        p1, p2, p3 = st.columns(3)
        with p1:
            nprs_rest = st.slider("Rest*", 0, 10, 0, key="nprs_rest_s")
        with p2:
            nprs_activity = st.slider("Activity*", 0, 10, 5, key="nprs_act_s")
        with p3:
            nprs_night = st.slider("Night", 0, 10, 2, key="nprs_night_s")

        irritability = st.selectbox(
            "Symptom Irritability*",
            [
                "Low (Settles quickly, tolerates moderate load)",
                "Moderate (Provoked by clear activity, settles within hours)",
                "High (Easily provoked, slow to settle, night/rest symptoms)",
            ],
            key="asm_irritability",
        )
        functional_goal = st.text_input("Functional Goal / Outcome Scale (NDI, ODI, KOOS, SPADI)", key="asm_goal")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ui-card"><div class="section-heading">2. Detailed Regional Examination, Special Tests & MMT</div>', unsafe_allow_html=True)
    assessment_details_dict = {}
    suggested_treatments = []
    bp_str = "".join(body_parts)

    if not body_parts:
        st.info("Select one or more body regions above to open region-specific ROM, neurological, and special test fields.")

    if "Cervical" in bp_str:
        st.markdown("#### 🔹 Cervical Spine / Neck")
        c1, c2 = st.columns(2)
        with c1:
            c_rom = st.text_input("Cervical ROM (Flexion 45°, Extension 45°, Lat Flexion 45°, Rotation 80°)", key="c_rom")
        with c2:
            c_neuro = st.text_input("Neurological Screen (C5–T1 Myotomes/Dermatomes/Reflexes)", key="c_neuro")
        c_tests = st.multiselect("Cervical Special Tests", ["Spurling’s Test", "Cervical Distraction Test", "Upper Limb Neurodynamic Tests (ULNT)", "Bakody Sign"], key="c_tests")
        assessment_details_dict["Cervical"] = {"ROM": c_rom, "Neurological": c_neuro, "Tests": c_tests}
        suggested_treatments.append("Cervical Traction + Deep Neck Flexor Endurance + Posture Correction")

    if "Thoracic" in bp_str:
        st.markdown("#### 🔹 Thoracic Spine / Upper Back")
        t1, t2 = st.columns(2)
        with t1:
            t_rom = st.text_input("Thoracic ROM (Flexion, Extension, Rotation, Side-Flexion)", key="t_rom")
        with t2:
            t_palp = st.text_input("Palpation / Costovertebral Mobility & Breathing", key="t_palp")
        assessment_details_dict["Thoracic"] = {"ROM": t_rom, "Palpation": t_palp}
        suggested_treatments.append("Thoracic Mobility + Scapular Stabilization + Breathing Re-education")

    if "Lumbar" in bp_str:
        st.markdown("#### 🔹 Lumbar Spine / Low Back")
        l1, l2 = st.columns(2)
        with l1:
            l_rom = st.text_input("Lumbar ROM (Flexion, Extension, Side-Glide, Rotation)", key="l_rom")
        with l2:
            l_neuro = st.text_input("Neurological Screen (L2–S1 Myotomes, Reflexes, Neural Tension)", key="l_neuro")
        l_tests = st.multiselect("Lumbar Special Tests", ["Straight Leg Raise (SLR)", "Crossed SLR", "Slump Test", "Femoral Nerve Stretch"], key="l_tests")
        assessment_details_dict["Lumbar"] = {"ROM": l_rom, "Neurological": l_neuro, "Tests": l_tests}
        suggested_treatments.append("Core Stabilization + Lumbar Traction + Centralization Mechanics")

    if "Shoulder" in bp_str:
        st.markdown("#### 🔹 Shoulder Complex")
        sh_rom = st.text_input("Shoulder ROM (Flexion 180°, Abduction 180°, ER/IR, Painful Arc)", key="sh_rom")
        sh_tests = st.multiselect("Shoulder Special Tests", ["Neer Test", "Hawkins-Kennedy Test", "Empty Can (Jobe)", "Speed's / Yergason's", "Apprehension / Relocation"], key="sh_tests")
        assessment_details_dict["Shoulder"] = {"ROM": sh_rom, "Tests": sh_tests}
        suggested_treatments.append("Rotator Cuff Strengthening + Scapular Retraction + Ultrasound")

    if "Elbow" in bp_str:
        st.markdown("#### 🔹 Elbow")
        el_rom = st.text_input("Elbow Flexion/Extension & Pronation/Supination", key="el_rom")
        el_tests = st.multiselect("Elbow Special Tests", ["Cozen's / Maudsley's Test", "Resisted Wrist Flexion", "Valgus/Varus Stress Test"], key="el_tests")
        assessment_details_dict["Elbow"] = {"ROM": el_rom, "Tests": el_tests}
        suggested_treatments.append("Eccentric Wrist Extension/Flexion + Soft Tissue Mobilization")

    if "Wrist" in bp_str:
        st.markdown("#### 🔹 Wrist & Hand")
        w_rom = st.text_input("Wrist Flexion/Extension, Radial/Ulnar Deviation, Pronation/Supination", key="w_rom")
        w_tests = st.multiselect("Wrist Special Tests", ["Phalen’s Test", "Tinel’s Sign", "Durkan's Test", "Finkelstein’s Test", "Scaphoid Shift Test"], key="w_tests")
        assessment_details_dict["Wrist"] = {"ROM": w_rom, "Tests": w_tests}
        suggested_treatments.append("Carpal Tunnel Glides + Splinting Advice + Ergonomic Correction")

    if "Hip" in bp_str:
        st.markdown("#### 🔹 Hip & Groin")
        h_rom = st.text_input("Hip ROM (Flexion, Extension, Abduction/Adduction, ER/IR)", key="h_rom")
        h_tests = st.multiselect("Hip Special Tests", ["FADIR Test", "FABER (Patrick's) Test", "Scour Test", "Trendelenburg Test"], key="h_tests")
        assessment_details_dict["Hip"] = {"ROM": h_rom, "Tests": h_tests}
        suggested_treatments.append("Hip Abductor Strengthening + Capsule Mobilization + Single-Leg Control")

    if "Knee" in bp_str:
        st.markdown("#### 🔹 Knee Joint")
        k_rom = st.text_input("Knee ROM (Flexion 140°, Extension 0°, Effusion/Sweep Test)", key="k_rom")
        k_tests = st.multiselect("Knee Special Tests", ["Lachman Test", "Anterior/Posterior Drawer", "McMurray Test", "Valgus/Varus Stress Test", "Patellar Apprehension"], key="k_tests")
        assessment_details_dict["Knee"] = {"ROM": k_rom, "Tests": k_tests}
        suggested_treatments.append("Quadriceps VMO Strengthening + Patellar Mobilization + Squat Mechanics")

    if "Ankle" in bp_str:
        st.markdown("#### 🔹 Ankle & Foot")
        a_rom = st.text_input("Ankle Dorsiflexion/Plantarflexion, Weight-Bearing Lunge Test", key="a_rom")
        a_tests = st.multiselect("Ankle Special Tests", ["Anterior Drawer (ATFL)", "Squeeze Test (Syndesmosis)", "Thompson Test (Achilles)"], key="a_tests")
        assessment_details_dict["Ankle"] = {"ROM": a_rom, "Tests": a_tests}
        suggested_treatments.append("Proprioceptive Balance Training + Calf Raises + Taping/Bracing")

    if "TMJ" in bp_str:
        st.markdown("#### 🔹 TMJ / Jaw")
        j_rom = st.text_input("Jaw Opening (mm), Lateral Excursion, Deviation/Deflection Path", key="j_rom")
        j_tests = st.multiselect("TMJ Screening", ["Joint Sounds / Clicking History", "Masticatory Muscle Palpation"], key="j_tests")
        assessment_details_dict["TMJ"] = {"ROM": j_rom, "Tests": j_tests}
        suggested_treatments.append("Cervicogenic Posture Correction + Jaw Relaxation Drills")

    st.markdown("---")
    mmt_grade = st.selectbox(
        "Overall Manual Muscle Testing (MMT)*",
        [
            "Grade 5 (Normal - Full ROM against max resistance)",
            "Grade 4 (Good - Full ROM against moderate resistance)",
            "Grade 3 (Fair - Full ROM against gravity only)",
            "Grade 2 (Poor - ROM with gravity eliminated)",
            "Grade 1 (Trace - Flicker of contraction)",
            "Grade 0 (Zero - No movement)",
        ],
        key="asm_mmt",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="ui-card"><div class="section-heading">3. Rehabilitation Plan & Sign-Off</div>', unsafe_allow_html=True)
    if not suggested_treatments:
        suggested_treatments.append("General Electrotherapy & Soft Tissue Mobilization")

    with st.form("assessment_save_form"):
        default_plan = " | ".join(suggested_treatments)
        treatment_plan_input = st.text_area("Final Treatment Plan & Suggested Modalities* (Editable)", value=default_plan, height=90)
        s1, s2 = st.columns(2)
        with s1:
            suggested_time = st.number_input("Suggested Total Sessions*", min_value=1, value=int(cfg.get("default_sessions", 10)))
        with s2:
            therapist = st.selectbox("Assigned Therapist*", therapists)

        if st.form_submit_button("Save Assessment & Protocol"):
            if not body_parts:
                st.error("Please select at least one Affected Body Region.")
            else:
                assessment_id = f"ASM-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                spot_note = f" | Pain Locations: {pain_spot_notes.strip()}" if pain_spot_notes.strip() else ""
                assessment_dict = {
                    "assessment_id": assessment_id,
                    "patient_id": selected_patient,
                    "clinic": branches[0] if active_clinic == "All Clinics" else active_clinic,
                    "body_parts": ", ".join(body_parts),
                    "vas_score": int(nprs_activity),
                    "assessment_details": (
                        f"NPRS[Rest:{nprs_rest}, Act:{nprs_activity}, Night:{nprs_night}] | "
                        f"Irritability: {irritability} | Goal: {functional_goal}{spot_note} | "
                        f"MMT: {mmt_grade} | Details: {str(assessment_details_dict)}"
                    ),
                    "suggested_treatment": treatment_plan_input.strip() or default_plan,
                    "suggested_duration": f"{suggested_time} Sessions",
                    "therapist": therapist,
                    "date": str(datetime.date.today()),
                }
                save_data("assessments", assessment_dict)
                st.success(f"Assessment saved under ID `{assessment_id}`.")
    st.markdown("</div>", unsafe_allow_html=True)
