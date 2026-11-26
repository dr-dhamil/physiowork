import datetime
from ai_assistant import generate_clinical_insights
from anatomy_3d import render_ecorche_3d_viewer
from db_manager import (
    col_val,
    get_branches_list,
    get_clinic_settings,
    get_therapists_list,
    save_data,
)
import streamlit as st

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


def render_assessment_page(
    active_clinic: str, patients_all, assessments_all, banner_fn
):
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

  selected_patient = st.selectbox(
      "Select Patient", patient_ids, format_func=_fmt
  )
  med_hist = banner_fn(patients_all, selected_patient)

  sub_3d, sub_rom, sub_plan = st.tabs(
      ["3D Écorché", "ROM & Strength", "Treatment Plan"]
  )

  with sub_3d:
    col_map, col_ai = st.columns([1.2, 1.0])
    with col_map:
      render_ecorche_3d_viewer(st.session_state.get("asm_body_parts", []))
      body_parts = st.multiselect(
          "Affected Body Region(s)*:", BODY_REGIONS, key="asm_body_parts"
      )
      pain_spot_notes = st.text_input(
          "Pinned Muscle / Joint Location Note",
          placeholder="e.g., #1 Right Anterior Deltoid / Biceps Tendon",
          key="asm_pain_spots",
      )
      p1, p2, p3 = st.columns(3)
      with p1:
        nprs_rest = st.slider("Rest NPRS", 0, 10, 0, key="nprs_rest_s")
      with p2:
        nprs_activity = st.slider("Activity NPRS*", 0, 10, 5, key="nprs_act_s")
      with p3:
        nprs_night = st.slider("Night NPRS", 0, 10, 2, key="nprs_night_s")

      irritability = st.selectbox(
          "Symptom Irritability*",
          [
              "Low (Settles quickly, tolerates moderate load)",
              "Moderate (Provoked by clear activity, settles within hours)",
              "High (Easily provoked, slow to settle, night/rest symptoms)",
          ],
          key="asm_irritability",
      )

    with col_ai:
      st.markdown(
          '<div class="ui-card"><div class="section-heading">AI-Driven'
          " Insights (Gemini)</div>",
          unsafe_allow_html=True,
      )
      ai_state_key = f"ai_insight_{selected_patient}"
      ctx_payload = {
          "patient_id": selected_patient,
          "clinic": active_clinic,
          "medical_history": med_hist or "None noted",
          "affected_regions": body_parts or ["General"],
          "pain_pins": pain_spot_notes,
          "nprs_rest": nprs_rest,
          "nprs_activity": nprs_activity,
          "nprs_night": nprs_night,
          "irritability": irritability,
      }
      if st.button("Generate Detailed Plan", key="btn_gen_ai"):
        with st.spinner("Generating clinical insights..."):
          st.session_state[ai_state_key] = generate_clinical_insights(
              ctx_payload, detailed_plan=True
          )

      if st.session_state.get(ai_state_key):
        st.markdown(st.session_state[ai_state_key])
      else:
        st.info(
            "Click **Generate Detailed Plan** to synthesize clinical insights"
            " and a structured rehab protocol from the selected regions,"
            " NPRS, irritability, and safety notes."
        )
      st.markdown("</div>", unsafe_allow_html=True)

  with sub_rom:
    st.markdown(
        '<div class="ui-card"><div class="section-heading">Regional'
        " Examination & Strength (MMT)</div>",
        unsafe_allow_html=True,
    )
    assessment_details_dict = {}
    suggested_treatments = []
    bp_str = "".join(body_parts) if body_parts else ""

    if not body_parts:
      st.info(
          "Select one or more Affected Body Region(s) in the **3D Écorché** tab"
          " to view targeted ROM & special test inputs."
      )

    if "Cervical" in bp_str:
      c1, c2 = st.columns(2)
      with c1:
        c_rom = st.text_input(
            "Cervical ROM (Flex 45 deg, Ext 45 deg, Lat Flex 45 deg, Rot 80"
            " deg)",
            key="c_rom",
        )
      with c2:
        c_neuro = st.text_input(
            "Cervical Neuro Screen (C5-T1 Myotomes/Dermatomes/Reflexes)",
            key="c_neuro",
        )
      c_tests = st.multiselect(
          "Cervical Special Tests",
          [
              "Spurling's Test",
              "Cervical Distraction Test",
              "ULNT",
              "Bakody Sign",
          ],
          key="c_tests",
      )
      assessment_details_dict["Cervical"] = {
          "ROM": c_rom,
          "Neuro": c_neuro,
          "Tests": c_tests,
      }
      suggested_treatments.append(
          "Cervical Traction + Deep Neck Flexor Endurance + Posture Correction"
      )

    if "Lumbar" in bp_str:
      l1, l2 = st.columns(2)
      with l1:
        l_rom = st.text_input(
            "Lumbar ROM (Flexion, Extension, Side-Glide, Rotation)", key="l_rom"
        )
      with l2:
        l_neuro = st.text_input(
            "Lumbar Neuro Screen (L2-S1 Myotomes/Reflexes)", key="l_neuro"
        )
      l_tests = st.multiselect(
          "Lumbar Special Tests",
          ["SLR", "Crossed SLR", "Slump Test", "Femoral Stretch"],
          key="l_tests",
      )
      assessment_details_dict["Lumbar"] = {
          "ROM": l_rom,
          "Neuro": l_neuro,
          "Tests": l_tests,
      }
      suggested_treatments.append(
          "Core Stabilization + Lumbar Traction + Centralization Mechanics"
      )

    if "Shoulder" in bp_str:
      sh_rom = st.text_input(
          "Shoulder ROM (Flexion 180 deg, Abduction 180 deg, ER/IR, Painful Arc)",
          key="sh_rom",
      )
      sh_tests = st.multiselect(
          "Shoulder Special Tests",
          [
              "Neer Test",
              "Hawkins-Kennedy",
              "Empty Can (Jobe)",
              "Speed's/Yergason's",
              "Apprehension/Relocation",
          ],
          key="sh_tests",
      )
      assessment_details_dict["Shoulder"] = {"ROM": sh_rom, "Tests": sh_tests}
      suggested_treatments.append(
          "Rotator Cuff Strengthening + Scapular Retraction + Ultrasound"
      )

    if "Knee" in bp_str:
      k_rom = st.text_input(
          "Knee ROM (Flexion 140 deg, Extension 0 deg, Effusion/Sweep)", key="k_rom"
      )
      k_tests = st.multiselect(
          "Knee Special Tests",
          [
              "Lachman",
              "Ant/Post Drawer",
              "McMurray",
              "Valgus/Varus",
              "Patellar Apprehension",
          ],
          key="k_tests",
      )
      assessment_details_dict["Knee"] = {"ROM": k_rom, "Tests": k_tests}
      suggested_treatments.append(
          "Quadriceps VMO Strengthening + Patellar Mobilization + Squat"
          " Mechanics"
      )

    for reg in body_parts:
      if reg not in assessment_details_dict:
        r_rom = st.text_input(f"{reg} — ROM / Palpation", key=f"rom_{reg}")
        r_note = st.text_input(
            f"{reg} — Special Tests / Notes", key=f"tst_{reg}"
        )
        assessment_details_dict[reg] = {"ROM": r_rom, "Tests": r_note}
        suggested_treatments.append(
            f"{reg} Mobility, Strengthening & Modality Plan"
        )

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
    functional_goal = st.text_input(
        "Functional Goal / Outcome Scale (NDI, ODI, KOOS, SPADI)", key="asm_goal"
    )
    st.markdown("</div>", unsafe_allow_html=True)

  with sub_plan:
    st.markdown(
        '<div class="ui-card"><div class="section-heading">Final'
        " Rehabilitation Plan & Sign-Off</div>",
        unsafe_allow_html=True,
    )
    if not suggested_treatments:
      suggested_treatments.append(
          "General Electrotherapy & Soft Tissue Mobilization"
      )
    default_plan = " | ".join(suggested_treatments)
    ai_text_cur = st.session_state.get(f"ai_insight_{selected_patient}", "")

    with st.form("assessment_save_form"):
      treatment_plan_input = st.text_area(
          "Final Treatment Plan & Modalities* (Editable)",
          value=default_plan,
          height=95,
      )
      attach_ai = st.checkbox(
          "Include AI Clinical Plan in Saved Record", value=bool(ai_text_cur)
      )
      s1, s2 = st.columns(2)
      with s1:
        suggested_time = st.number_input(
            "Suggested Total Sessions*",
            min_value=1,
            value=int(cfg.get("default_sessions", 10)),
        )
      with s2:
        therapist = st.selectbox("Assigned Therapist*", therapists)

      if st.form_submit_button("Save Assessment & Protocol"):
        if not body_parts:
          st.error(
              "Please select at least one Affected Body Region in the 3D"
              " Écorché tab."
          )
        else:
          assessment_id = (
              f"ASM-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
          )
          spot_note = (
              f" | Pain Locations: {pain_spot_notes.strip()}"
              if pain_spot_notes.strip()
              else ""
          )
          ai_suffix = (
              f" | AI Plan: {ai_text_cur}"
              if (attach_ai and ai_text_cur)
              else ""
          )
          save_data(
              "assessments",
              {
                  "assessment_id": assessment_id,
                  "patient_id": selected_patient,
                  "clinic": (
                      branches[0] if active_clinic == "All Clinics" else active_clinic
                  ),
                  "body_parts": ", ".join(body_parts),
                  "vas_score": int(nprs_activity),
                  "assessment_details": (
                      f"NPRS[Rest:{nprs_rest}, Act:{nprs_activity},"
                      f" Night:{nprs_night}] | Irritability: {irritability} |"
                      f" Goal: {functional_goal}{spot_note} | MMT: {mmt_grade} |"
                      f" Details: {str(assessment_details_dict)}{ai_suffix}"
                  ),
                  "suggested_treatment": treatment_plan_input.strip()
                  or default_plan,
                  "suggested_duration": f"{suggested_time} Sessions",
                  "therapist": therapist,
                  "date": str(datetime.date.today()),
              },
          )
          st.success(f"Assessment saved under ID `{assessment_id}`.")
    st.markdown("</div>", unsafe_allow_html=True)
