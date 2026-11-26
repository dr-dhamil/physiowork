import datetime
import pandas as pd
import streamlit as st
from ai_assistant import get_gemini_api_key
from db_manager import (
authenticate_staff,
col_val,
db_connected,
filter_by_clinic,
get_branches_list,
get_clinic_settings,
get_data,
save_data,
)
from module_admin import render_admin_panel
from module_assessment import render_assessment_page
from module_frontdesk import render_frontdesk_page
from pdf_utils import create_assessment_pdf
st.set_page_config(
    page_title="Dr. Geetanjali's PhysioWorks",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)
# --- NAVY (#1B365D) &amp; ORANGE (#F47920) MODERN CLINIC THEME ---
st.markdown(
"""
&lt;style&gt;
:root {
--navy: #1B365D;
--navy-dark: #11223B;
--orange: #F47920;
--orange-hover: #D96412;
--bg-soft: #F3F6FA;
--card-bg: #FFFFFF;
--border-subtle: #DCE3EC;
--text-main: #1E293B;

}
.stApp { background-color: var(--bg-soft); color: var(--text-main); }
.block-container { padding-top: 1.25rem; padding-bottom: 2.2rem; }
[data-testid=";stSidebar";] {
background: linear-gradient(180deg, var(--navy) 0%, var(--navy-dark) 100%);
border-right: 3px solid var(--orange);
}
[data-testid=";stSidebar";] .stMarkdown,
[data-testid=";stSidebar";] label,
[data-testid=";stSidebar";] p,
[data-testid=";stSidebar";] span { color: #FFFFFF !important; }
[data-testid=";stSidebar";] .stSelectbox div[data-baseweb=";select";] &gt; div {
background-color: rgba(255, 255, 255, 0.12);
color: #FFFFFF !important;
border-color: rgba(255, 255, 255, 0.25);
}
.clinic-banner {
background: linear-gradient(135deg, var(--navy) 0%, #24477A 100%);
color: #FFFFFF; padding: 18px 24px; border-radius: 12px;
border-bottom: 4px solid var(--orange); margin-bottom: 16px;
box-shadow: 0 4px 12px rgba(27, 54, 93, 0.12);
}
.clinic-banner h1 { color: #FFFFFF !important; margin: 0 0 4px 0; font-size: 1.65rem; font-weight: 700; }
.clinic-tagline { color: #FDBA74; font-size: 0.92rem; margin: 0; }
.clinic-badge {
display: inline-block; background-color: var(--orange); color: #FFFFFF;
font-size: 0.76rem; font-weight: 700; padding: 4px 10px; border-radius: 999px;
margin-top: 8px; margin-right: 6px;
}
.clinic-pill-meta {
display: inline-block; background-color: rgba(255, 255, 255, 0.14); color: #FFFFFF;
font-size: 0.76rem; font-weight: 600; padding: 4px 10px; border-radius: 999px; margin-top: 8px;
}
.ui-card, .login-card {
background-color: var(--card-bg); border: 1px solid var(--border-subtle);
border-radius: 10px; padding: 18px 22px; margin-bottom: 16px;
box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
}
.login-card { border-top: 5px solid var(--orange); }
.patient-strip {
background-color: var(--card-bg); border-left: 5px solid var(--orange);
border-top: 1px solid var(--border-subtle); border-right: 1px solid var(--border-subtle);
border-bottom: 1px solid var(--border-subtle); border-radius: 8px;
padding: 12px 18px; margin-bottom: 14px;
}
.section-heading {
color: var(--navy) !important; font-size: 1.12rem; font-weight: 700;
margin: 0 0 12px 0; padding-bottom: 6px; border-bottom: 2px solid #F1F5F9;
}
h2, h3 { color: var(--navy) !important; }
.stButton &gt; button, .stFormSubmitButton &gt; button, .stDownloadButton &gt; button {
background-color: var(--orange) !important; color: #FFFFFF !important;
border: none !important; border-radius: 8px !important; font-weight: 600 !important;
padding: 0.5rem 1.1rem !important;
}
.stButton &gt; button:hover, .stFormSubmitButton &gt; button:hover, .stDownloadButton &gt; button:hover {
background-color: var(--orange-hover) !important; color: #FFFFFF !important;
}
[data-testid=";stMetric";] {
background-color: var(--card-bg); border: 1px solid var(--border-subtle);
border-top: 3px solid var(--navy); border-radius: 8px; padding: 12px 16px;
}
&lt;/style&gt;
""",
unsafe_allow_html=True,

)
ROLE_MENUS = {
";Admin / Clinic Owner";: [
";Front Desk &amp; Queue";,
";Clinical Assessment";,
";Patient Registration";,
";Daily Treatment Log";,
";Billing &amp; Reminders";,
";Progress &amp; Summary";,
";Admin Panel &amp; Settings";,
],
";Physiotherapist";: [
";Front Desk &amp; Queue";,
";Clinical Assessment";,
";Patient Registration";,
";Daily Treatment Log";,
";Progress &amp; Summary";,
],
";Front Desk";: [
";Front Desk &amp; Queue";,
";Patient Registration";,
";Billing &amp; Reminders";,
";Progress &amp; Summary";,
],
}
def render_patient_banner(patients_df: pd.DataFrame, selected_pid: str) -&gt; str:
pid_col = col_val(patients_df, [";patient_id";, ";Patient_ID";])
name_col = col_val(patients_df, [";name";, ";Name";])
phone_col = col_val(patients_df, [";phone";, ";Phone";])
gender_col = col_val(patients_df, [";gender";, ";Gender";])
hist_col = col_val(patients_df, [";medical_history";, ";Medical_History";])
clinic_col = col_val(patients_df, [";clinic";, ";Clinic";])
row = patients_df[patients_df[pid_col] == selected_pid]
if row.empty:
return ";";
r = row.iloc[0]
p_name = r.get(name_col, ";N/A";) if name_col else ";N/A";
p_phone = r.get(phone_col, ";N/A";) if phone_col else ";N/A";
p_gender = r.get(gender_col, ";N/A";) if gender_col else ";N/A";
p_clinic = r.get(clinic_col, ";A-3 Paschim Vihar";) if clinic_col else ";A-3 Paschim Vihar";
p_hist = str(r.get(hist_col, ";";) or ";";).strip()
st.markdown(
f"""
&lt;div class=";patient-strip";&gt;
&lt;strong&gt;Patient Assessment:&lt;/strong&gt; {p_name} &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;ID:&lt;/strong&gt; &lt;code&gt;{selected_pid}&lt;/code&gt; &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;Gender:&lt;/strong&gt; {p_gender} &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;Phone:&lt;/strong&gt; {p_phone} &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;Branch:&lt;/strong&gt; {p_clinic}
&lt;/div&gt;
""",
unsafe_allow_html=True,
)
if p_hist:
alert_keywords = [";diabet";, ";hypertens";, ";bp";, ";anticoagulant";, ";blood thinner";, ";pregnan";, ";osteopor";,
";cancer";, ";surger";, ";fracture";, ";pacemaker";]
if any(k in p_hist.lower() for k in alert_keywords):
st.warning(f";⚠️ **Medical Precaution Flags:** {p_hist}";)
else:
st.info(f";�� **Medical Notes:** {p_hist}";)

return p_hist
cfg = get_clinic_settings()
branches = get_branches_list()
if ";auth_user"; not in st.session_state:
st.session_state[";auth_user";] = None
if st.session_state[";auth_user";] is None:
st.markdown(
f"""
&lt;div class=";clinic-banner";&gt;
&lt;h1&gt;�� {cfg.get(&#39;clinic_title&#39;)}&lt;/h1&gt;
&lt;p class=";clinic-tagline";&gt;{cfg.get(&#39;clinic_tagline&#39;)}&lt;/p&gt;
&lt;span class=";clinic-badge";&gt;{cfg.get(&#39;clinic_badge&#39;)}&lt;/span&gt;
&lt;/div&gt;
""",
unsafe_allow_html=True,
)
_, col_mid, _ = st.columns([1, 1.35, 1])
with col_mid:
st.markdown(&#39;&lt;div class=";login-card";&gt;&#39;, unsafe_allow_html=True)
try:
st.image(cfg.get(";logo_path";, ";image_500b64.jpg";), width=180)
except Exception:
pass
st.markdown(";### �� Staff &amp; Clinician Sign-In";)
with st.form(";staff_login_form";):
login_email = st.text_input(";Staff Email or ID";, value=";dr.geetanjali@physioworks.in";)
login_pass = st.text_input(";Password / Clinic PIN";, type=";password";, placeholder=";Enter password";)
login_branch = st.selectbox(";Select Active Clinic Branch";, branches + [";All Clinics";])
if st.form_submit_button(";Sign In to Clinic Workspace";):
user_rec = authenticate_staff(login_email, login_pass)
if user_rec:
if user_rec.get(";role";) != ";Admin / Clinic Owner"; and login_branch == ";All Clinics";:
login_branch = user_rec.get(";assigned_clinic";) or branches[0]
st.session_state[";auth_user";] = user_rec
st.session_state[";active_clinic";] = login_branch
st.rerun()
else:
st.error(";Invalid staff credentials.";)
with st.expander(";ℹ️ Default Clinic Login Credentials";):
st.markdown(
";";";
- **Admin / Clinic Owner:** `dr.geetanjali@physioworks.in` / `admin123`
- **Physiotherapist:** `physio@physioworks.in` / `physio123`
- **Front Desk:** `desk@physioworks.in` / `desk123`
";";";
)
st.markdown(";&lt;/div&gt;";, unsafe_allow_html=True)
st.stop()
current_user = st.session_state[";auth_user";]
active_role = current_user.get(";role";, ";Physiotherapist";)
allowed_menus = ROLE_MENUS.get(active_role, ROLE_MENUS[";Physiotherapist";])
with st.sidebar:
try:
st.sidebar.image(cfg.get(";logo_path";, ";image_500b64.jpg";), width=210)
except Exception:
st.sidebar.markdown(f";### �� {cfg.get(&#39;clinic_title&#39;)}";)
st.markdown(";---";)
st.markdown(f";**�� {current_user.get(&#39;full_name&#39;, &#39;Staff&#39;)}**";)

st.caption(f";Role: {active_role}";)
branch_choices = branches + [";All Clinics";] if active_role == ";Admin / Clinic Owner"; else branches
default_branch = st.session_state.get(";active_clinic";, branches[0])
if default_branch not in branch_choices:
default_branch = branch_choices[0]
active_clinic = st.selectbox(";Active Clinic";, branch_choices, index=branch_choices.index(default_branch))
st.session_state[";active_clinic";] = active_clinic
menu = st.selectbox(";Clinic Workspace";, allowed_menus)
st.markdown(";---";)
if get_gemini_api_key():
st.success(";● Gemini AI: Key Configured";)
else:
st.info(";● Gemini AI: Fallback Mode";)
if db_connected:
st.success(";● Supabase Cloud Sync: Active";)
else:
st.info(";● Storage Mode: Session Memory";)
if st.button(";�� Sign Out";):
st.session_state[";auth_user";] = None
st.rerun()
patients_all = filter_by_clinic(get_data(";patients";), active_clinic)
assessments_all = filter_by_clinic(get_data(";assessments";), active_clinic)
logs_all = filter_by_clinic(get_data(";daily_logs";), active_clinic)
appointments_all = filter_by_clinic(get_data(";appointments";), active_clinic)
billing_all = filter_by_clinic(get_data(";billing";), active_clinic)
st.markdown(
f";";";
&lt;div class=";clinic-banner";&gt;
&lt;h1&gt;�� {cfg.get(&#39;clinic_title&#39;)}&lt;/h1&gt;
&lt;p class=";clinic-tagline";&gt;{cfg.get(&#39;clinic_tagline&#39;)}&lt;/p&gt;
&lt;span class=";clinic-badge";&gt;{cfg.get(&#39;clinic_badge&#39;)}&lt;/span&gt;
&lt;span class=";clinic-pill-meta";&gt;�� {active_clinic} &amp;nbsp;|&amp;nbsp; �� {current_user.get(&#39;full_name&#39;
({active_role})&lt;/span&gt;
&lt;/div&gt;
";";";,
unsafe_allow_html=True,
)
k1, k2, k3, k4 = st.columns(4)
k1.metric(";Patients";, len(patients_all))
k2.metric(";Queue Appointments";, len(appointments_all))
k3.metric(";Assessments";, len(assessments_all))
k4.metric(";Sessions Logged";, len(logs_all))
if menu == ";Front Desk &amp; Queue";:
render_frontdesk_page(active_clinic, patients_all)
elif menu == ";Clinical Assessment";:
render_assessment_page(active_clinic, patients_all, assessments_all, render_patient_banner)
elif menu == ";Patient Registration";:
st.markdown(&#39;&lt;div class=";ui-card";&gt;&lt;div class=";section-heading";&gt;New Patient Intake Form&lt;/div&gt;&#39;,
unsafe_allow_html=True)
with st.form(";reg_form";):
c1, c2 = st.columns(2)
with c1:
name = st.text_input(";Patient Full Name*";)
email = st.text_input(";Email Address";)
gender = st.selectbox(";Gender";, [";Female";, ";Male";, ";Other";])
age_occ = st.text_input(";Age / Occupation &amp; Activity Demands";)

with c2:
phone = st.text_input(";Phone Number*";)
dominant_side = st.selectbox(";Dominant Side";, [";Right";, ";Left";, ";Bilateral / Mixed";])
referral = st.text_input(";Referral Source";)
med_history = st.text_area(";Medical History &amp; Safety Flags";)
reg_clinic = st.selectbox(";Home Clinic Branch*";, branches, index=0 if active_clinic == ";All Clinics"; else
branches.index(active_clinic))
if st.form_submit_button(";Register &amp; Generate Patient ID";):
if name and phone:
all_p = get_data(";patients";)
counter = len(all_p) + 1 if not all_p.empty else 1
patient_id = f";PW{datetime.datetime.now().strftime(&#39;%m%y&#39;)}{counter:03d}";
meta = [x for x in [
f";Profile: {age_occ.strip()}"; if age_occ.strip() else ";";,
f";Dominant: {dominant_side}"; if dominant_side else ";";,
f";Ref: {referral.strip()}"; if referral.strip() else ";";,
] if x]
combined_hist = f";{med_history.strip()} | {&#39; ; &#39;.join(meta)}";.strip("; |";) if meta else
med_history.strip()
save_data(";patients";, {
";patient_id";: patient_id,
";name";: name.strip(),
";email";: email.strip(),
";gender";: gender,
";phone";: phone.strip(),
";clinic";: reg_clinic,
";medical_history";: combined_hist,
";registration_date";: str(datetime.date.today()),
})
st.success(f";Patient registered! Generated ID: **{patient_id}**";)
st.rerun()
else:
st.error(";Please enter both Patient Full Name and Phone Number.";)
st.markdown(";&lt;/div&gt;";, unsafe_allow_html=True)
if not patients_all.empty:
st.markdown(&#39;&lt;div class=";ui-card";&gt;&lt;div class=";section-heading";&gt;Patient Directory&lt;/div&gt;&#39;,
unsafe_allow_html=True)
st.dataframe(patients_all, width=";stretch";, hide_index=True)
st.markdown(";&lt;/div&gt;";, unsafe_allow_html=True)
elif menu == ";Daily Treatment Log";:
pid_col = col_val(patients_all, [";patient_id";, ";Patient_ID";])
if patients_all.empty or not pid_col:
st.warning(";Register a patient first under **Patient Registration**.";)
else:
log_patient = st.selectbox(";Select Patient";, patients_all[pid_col].tolist())
render_patient_banner(patients_all, log_patient)
with st.form(";daily_log_form";):
c1, c2 = st.columns(2)
with c1:
log_date = st.date_input(";Session Date*";, datetime.date.today())
with c2:
current_vas = st.slider(";Current Session NPRS (0–10)*";, 0, 10, 3)
treatment_given = st.text_area(";Treatment Provided*";)
notes = st.text_area(";Progress &amp; Next-Session Notes";)
if st.form_submit_button(";Save Daily Log";):
save_data(";daily_logs";, {
";patient_id";: log_patient,
";clinic";: branches[0] if active_clinic == ";All Clinics"; else active_clinic,
";session_date";: str(log_date),
";treatment_given";: treatment_given,
";current_vas";: int(current_vas),
";notes";: notes.strip(),
})
st.success(";Daily treatment log saved.";)
st.rerun()

elif menu == ";Billing &amp; Reminders";:
pid_col = col_val(patients_all, [";patient_id";, ";Patient_ID";])
if patients_all.empty or not pid_col:
st.warning(";Register a patient first under **Patient Registration**.";)
else:
with st.form(";billing_entry_form";):
c1, c2, c3 = st.columns(3)
with c1:
b_pid = st.selectbox(";Patient*";, patients_all[pid_col].tolist())
b_pkg = st.selectbox(";Plan / Package*";, [";Single Session";, ";5-Session Rehab Pack";, ";10-Session Recovery
Pack";, ";Assessment + Initial Therapy";])
with c2:
b_amt = st.number_input(";Amount (₹)*";, min_value=0, value=int(cfg.get(";default_fee_inr";, 800)),
step=100)
b_mode = st.selectbox(";Payment Mode*";, [";UPI";, ";Cash";, ";Card";, ";Pending";])
with c3:
b_status = st.selectbox(";Payment Status*";, [";Paid";, ";Partial";, ";Pending";])
b_followup = st.date_input(";Next Follow-Up Date";, datetime.date.today() + datetime.timedelta(days=2))
if st.form_submit_button(";Record Billing &amp; Follow-Up";):
inv_id = f";INV-{datetime.datetime.now().strftime(&#39;%Y%m%d%H%M%S&#39;)}";
save_data(";billing";, {
";invoice_id";: inv_id,
";patient_id";: b_pid,
";clinic";: branches[0] if active_clinic == ";All Clinics"; else active_clinic,
";package_name";: b_pkg,
";amount_inr";: int(b_amt),
";payment_mode";: b_mode,
";payment_status";: b_status,
";next_followup";: str(b_followup),
";date";: str(datetime.date.today()),
})
st.success(f";Saved billing entry `{inv_id}`.";)
st.rerun()
if not billing_all.empty:
st.dataframe(billing_all, width=";stretch";, hide_index=True)
elif menu == ";Progress &amp; Summary";:
pid_col = col_val(patients_all, [";patient_id";, ";Patient_ID";])
if patients_all.empty or not pid_col:
st.warning(";No patient records available.";)
else:
dash_patient = st.selectbox(";Select Patient";, patients_all[pid_col].tolist())
render_patient_banner(patients_all, dash_patient)
p_asm = assessments_all[assessments_all[";patient_id";] == dash_patient] if (not assessments_all.empty and
";patient_id"; in assessments_all.columns) else pd.DataFrame()
p_row = patients_all[patients_all[pid_col] == dash_patient].iloc[0].to_dict()
latest_asm = p_asm.iloc[-1].to_dict() if not p_asm.empty else None
pdf_bytes = create_assessment_pdf(p_row, asm_row=latest_asm, clinic_title=cfg.get(";clinic_title";),
logo_path=cfg.get(";logo_path";, ";image_500b64.jpg";))
st.download_button(";�� Download Patient Assessment PDF";, data=pdf_bytes
file_name=f";{dash_patient}_assessment.pdf";, mime=";application/pdf";)
elif menu == ";Admin Panel &amp; Settings";:
render_admin_panel()
