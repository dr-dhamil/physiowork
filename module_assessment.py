import datetime
import streamlit as st
from ai_assistant import generate_clinical_insights
from anatomy_3d import render_ecorche_3d_viewer

from db_manager import (
col_val,
get_branches_list,
get_clinic_settings,
get_therapists_list,
save_data,
)
BODY_REGIONS = [
&quot;Cervical Spine (Neck)&quot;,
&quot;Thoracic Spine (Upper Back)&quot;,
&quot;Lumbar Spine (Lower Back)&quot;,
&quot;Shoulder Complex&quot;,
&quot;Elbow&quot;,
&quot;Wrist &amp; Hand&quot;,
&quot;Hip &amp; Groin&quot;,
&quot;Knee Joint&quot;,
&quot;Ankle &amp; Foot&quot;,
&quot;TMJ / Jaw&quot;,
]
def render_assessment_page(active_clinic: str, patients_all, assessments_all, banner_fn):
pid_col = col_val(patients_all, [&quot;patient_id&quot;, &quot;Patient_ID&quot;])
name_col = col_val(patients_all, [&quot;name&quot;, &quot;Name&quot;])
branches = get_branches_list()
therapists = get_therapists_list()
cfg = get_clinic_settings()
if patients_all.empty or not pid_col:
st.warning(&quot;Register a patient first under **Patient Registration**.&quot;)
return
patient_ids = patients_all[pid_col].tolist()
def _fmt(pid):
if name_col:
match = patients_all[patients_all[pid_col] == pid]
if not match.empty:
return f&quot;{pid} • {match.iloc[0][name_col]}&quot;
return pid
selected_patient = st.selectbox(&quot;Select Patient&quot;, patient_ids, format_func=_fmt)
med_hist = banner_fn(patients_all, selected_patient)
sub_3d, sub_rom, sub_plan = st.tabs([&quot;3D Écorché&quot;, &quot;ROM &amp; Strength&quot;, &quot;Treatment Plan&quot;])
with sub_3d:
col_map, col_ai = st.columns([1.2, 1.0])
with col_map:
render_ecorche_3d_viewer(st.session_state.get(&quot;asm_body_parts&quot;, []))
body_parts = st.multiselect(&quot;Affected Body Region(s)*:&quot;, BODY_REGIONS, key=&quot;asm_body_parts&quot;)
pain_spot_notes = st.text_input(
&quot;Pinned Muscle / Joint Location Note&quot;,
placeholder=&quot;e.g., #1 Right Anterior Deltoid / Biceps Tendon&quot;,
key=&quot;asm_pain_spots&quot;,
)
p1, p2, p3 = st.columns(3)
with p1:
nprs_rest = st.slider(&quot;Rest NPRS&quot;, 0, 10, 0, key=&quot;nprs_rest_s&quot;)
with p2:
nprs_activity = st.slider(&quot;Activity NPRS*&quot;, 0, 10, 5, key=&quot;nprs_act_s&quot;)
with p3:
nprs_night = st.slider(&quot;Night NPRS&quot;, 0, 10, 2, key=&quot;nprs_night_s&quot;)

irritability = st.selectbox(
&quot;Symptom Irritability*&quot;,
[
&quot;Low (Settles quickly, tolerates moderate load)&quot;,
&quot;Moderate (Provoked by clear activity, settles within hours)&quot;,
&quot;High (Easily provoked, slow to settle, night/rest symptoms)&quot;,
],
key=&quot;asm_irritability&quot;,
)
with col_ai:
st.markdown(&#39;&lt;div class=&quot;ui-card&quot;&gt;&lt;div class=&quot;section-heading&quot;&gt;AI-Driven Insights (Gemini)&lt;/div&gt;&#39;,
unsafe_allow_html=True)
ai_state_key = f&quot;ai_insight_{selected_patient}&quot;
ctx_payload = {
&quot;patient_id&quot;: selected_patient,
&quot;clinic&quot;: active_clinic,
&quot;medical_history&quot;: med_hist or &quot;None noted&quot;,
&quot;affected_regions&quot;: body_parts or [&quot;General&quot;],
&quot;pain_pins&quot;: pain_spot_notes,
&quot;nprs_rest&quot;: nprs_rest,
&quot;nprs_activity&quot;: nprs_activity,
&quot;nprs_night&quot;: nprs_night,
&quot;irritability&quot;: irritability,
}
if st.button(&quot;Generate Detailed Plan&quot;, key=&quot;btn_gen_ai&quot;):
with st.spinner(&quot;Generating clinical insights...&quot;):
st.session_state[ai_state_key] = generate_clinical_insights(ctx_payload, detailed_plan=True)
if st.session_state.get(ai_state_key):
st.markdown(st.session_state[ai_state_key])
else:
st.info(&quot;Click **Generate Detailed Plan** to synthesize clinical insights and a structured rehab
protocol from the selected regions, NPRS, irritability, and safety notes.&quot;)
st.markdown(&quot;&lt;/div&gt;&quot;, unsafe_allow_html=True)
with sub_rom:
st.markdown(&#39;&lt;div class=&quot;ui-card&quot;&gt;&lt;div class=&quot;section-heading&quot;&gt;Regional Examination &amp; Strength (MMT)&lt;/div&gt;&#39;,
unsafe_allow_html=True)
assessment_details_dict = {}
suggested_treatments = []
bp_str = &quot;&quot;.join(body_parts) if body_parts else &quot;&quot;
if not body_parts:
st.info(&quot;Select one or more Affected Body Region(s) in the **3D Écorché** tab to view targeted ROM &amp;
special test inputs.&quot;)
if &quot;Cervical&quot; in bp_str:
c1, c2 = st.columns(2)
with c1:
c_rom = st.text_input(&quot;Cervical ROM (Flex 45 deg, Ext 45 deg, Lat Flex 45 deg, Rot 80 deg)&quot;,
key=&quot;c_rom&quot;)
with c2:
c_neuro = st.text_input(&quot;Cervical Neuro Screen (C5-T1 Myotomes/Dermatomes/Reflexes)&quot;, key=&quot;c_neuro&quot;)
c_tests = st.multiselect(&quot;Cervical Special Tests&quot;, [&quot;Spurling’s Test&quot;, &quot;Cervical Distraction Test&quot;, &quot;ULNT&quot;,
&quot;Bakody Sign&quot;], key=&quot;c_tests&quot;)
assessment_details_dict[&quot;Cervical&quot;] = {&quot;ROM&quot;: c_rom, &quot;Neuro&quot;: c_neuro, &quot;Tests&quot;: c_tests}
suggested_treatments.append(&quot;Cervical Traction + Deep Neck Flexor Endurance + Posture Correction&quot;)
if &quot;Lumbar&quot; in bp_str:
l1, l2 = st.columns(2)
with l1:
l_rom = st.text_input(&quot;Lumbar ROM (Flexion, Extension, Side-Glide, Rotation)&quot;, key=&quot;l_rom&quot;)
with l2:
l_neuro = st.text_input(&quot;Lumbar Neuro Screen (L2-S1 Myotomes/Reflexes)&quot;, key=&quot;l_neuro&quot;)

l_tests = st.multiselect(&quot;Lumbar Special Tests&quot;, [&quot;SLR&quot;, &quot;Crossed SLR&quot;, &quot;Slump Test&quot;, &quot;Femoral Stretch&quot;],
key=&quot;l_tests&quot;)
assessment_details_dict[&quot;Lumbar&quot;] = {&quot;ROM&quot;: l_rom, &quot;Neuro&quot;: l_neuro, &quot;Tests&quot;: l_tests}
suggested_treatments.append(&quot;Core Stabilization + Lumbar Traction + Centralization Mechanics&quot;)
if &quot;Shoulder&quot; in bp_str:
sh_rom = st.text_input(&quot;Shoulder ROM (Flexion 180 deg, Abduction 180 deg, ER/IR, Painful Arc)&quot;,
key=&quot;sh_rom&quot;)
sh_tests = st.multiselect(&quot;Shoulder Special Tests&quot;, [&quot;Neer Test&quot;, &quot;Hawkins-Kennedy&quot;, &quot;Empty Can (Jobe)&quot;,
&quot;Speed&#39;s/Yergason&#39;s&quot;, &quot;Apprehension/Relocation&quot;], key=&quot;sh_tests&quot;)
assessment_details_dict[&quot;Shoulder&quot;] = {&quot;ROM&quot;: sh_rom, &quot;Tests&quot;: sh_tests}
suggested_treatments.append(&quot;Rotator Cuff Strengthening + Scapular Retraction + Ultrasound&quot;)
if &quot;Knee&quot; in bp_str:
k_rom = st.text_input(&quot;Knee ROM (Flexion 140 deg, Extension 0 deg, Effusion/Sweep)&quot;, key=&quot;k_rom&quot;)
k_tests = st.multiselect(&quot;Knee Special Tests&quot;, [&quot;Lachman&quot;, &quot;Ant/Post Drawer&quot;, &quot;McMurray&quot;, &quot;Valgus/Varus&quot;,
&quot;Patellar Apprehension&quot;], key=&quot;k_tests&quot;)
assessment_details_dict[&quot;Knee&quot;] = {&quot;ROM&quot;: k_rom, &quot;Tests&quot;: k_tests}
suggested_treatments.append(&quot;Quadriceps VMO Strengthening + Patellar Mobilization + Squat Mechanics&quot;)
for reg in body_parts:
if reg not in assessment_details_dict:
r_rom = st.text_input(f&quot;{reg} — ROM / Palpation&quot;, key=f&quot;rom_{reg}&quot;)
r_note = st.text_input(f&quot;{reg} — Special Tests / Notes&quot;, key=f&quot;tst_{reg}&quot;)
assessment_details_dict[reg] = {&quot;ROM&quot;: r_rom, &quot;Tests&quot;: r_note}
suggested_treatments.append(f&quot;{reg} Mobility, Strengthening &amp; Modality Plan&quot;)
mmt_grade = st.selectbox(
&quot;Overall Manual Muscle Testing (MMT)*&quot;,
[
&quot;Grade 5 (Normal - Full ROM against max resistance)&quot;,
&quot;Grade 4 (Good - Full ROM against moderate resistance)&quot;,
&quot;Grade 3 (Fair - Full ROM against gravity only)&quot;,
&quot;Grade 2 (Poor - ROM with gravity eliminated)&quot;,
&quot;Grade 1 (Trace - Flicker of contraction)&quot;,
&quot;Grade 0 (Zero - No movement)&quot;,
],
key=&quot;asm_mmt&quot;,
)
functional_goal = st.text_input(&quot;Functional Goal / Outcome Scale (NDI, ODI, KOOS, SPADI)&quot;, key=&quot;asm_goal&quot;)
st.markdown(&quot;&lt;/div&gt;&quot;, unsafe_allow_html=True)
with sub_plan:
st.markdown(&#39;&lt;div class=&quot;ui-card&quot;&gt;&lt;div class=&quot;section-heading&quot;&gt;Final Rehabilitation Plan &amp; Sign-Off&lt;/div&gt;&#39;,
unsafe_allow_html=True)
if not suggested_treatments:
suggested_treatments.append(&quot;General Electrotherapy &amp; Soft Tissue Mobilization&quot;)
default_plan = &quot; | &quot;.join(suggested_treatments)
ai_text_cur = st.session_state.get(f&quot;ai_insight_{selected_patient}&quot;, &quot;&quot;)
with st.form(&quot;assessment_save_form&quot;):
treatment_plan_input = st.text_area(&quot;Final Treatment Plan &amp; Modalities* (Editable)&quot;, value=default_plan,
height=95)
attach_ai = st.checkbox(&quot;Include AI Clinical Plan in Saved Record&quot;, value=bool(ai_text_cur))
s1, s2 = st.columns(2)
with s1:
suggested_time = st.number_input(&quot;Suggested Total Sessions*&quot;, min_value=1,
value=int(cfg.get(&quot;default_sessions&quot;, 10)))
with s2:
therapist = st.selectbox(&quot;Assigned Therapist*&quot;, therapists)
if st.form_submit_button(&quot;Save Assessment &amp; Protocol&quot;):
if not body_parts:
st.error(&quot;Please select at least one Affected Body Region in the 3D Écorché tab.&quot;)
else:

assessment_id = f&quot;ASM-{datetime.datetime.now().strftime(&#39;%Y%m%d%H%M%S&#39;)}&quot;
spot_note = f&quot; | Pain Locations: {pain_spot_notes.strip()}&quot; if pain_spot_notes.strip() else &quot;&quot;
ai_suffix = f&quot; | AI Plan: {ai_text_cur}&quot; if (attach_ai and ai_text_cur) else &quot;&quot;
save_data(&quot;assessments&quot;, {
&quot;assessment_id&quot;: assessment_id,
&quot;patient_id&quot;: selected_patient,
&quot;clinic&quot;: branches[0] if active_clinic == &quot;All Clinics&quot; else active_clinic,
&quot;body_parts&quot;: &quot;, &quot;.join(body_parts),
&quot;vas_score&quot;: int(nprs_activity),
&quot;assessment_details&quot;: (
f&quot;NPRS[Rest:{nprs_rest}, Act:{nprs_activity}, Night:{nprs_night}] | &quot;
f&quot;Irritability: {irritability} | Goal: {functional_goal}{spot_note} | &quot;
f&quot;MMT: {mmt_grade} | Details: {str(assessment_details_dict)}{ai_suffix}&quot;
),
&quot;suggested_treatment&quot;: treatment_plan_input.strip() or default_plan,
&quot;suggested_duration&quot;: f&quot;{suggested_time} Sessions&quot;,
&quot;therapist&quot;: therapist,
&quot;date&quot;: str(datetime.date.today()),
})
st.success(f&quot;Assessment saved under ID `{assessment_id}`.&quot;)
st.markdown(&quot;&lt;/div&gt;&quot;, unsafe_allow_html=True)
