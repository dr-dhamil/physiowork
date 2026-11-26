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
[data-testid=&quot;stSidebar&quot;] {
background: linear-gradient(180deg, var(--navy) 0%, var(--navy-dark) 100%);
border-right: 3px solid var(--orange);
}
[data-testid=&quot;stSidebar&quot;] .stMarkdown,
[data-testid=&quot;stSidebar&quot;] label,
[data-testid=&quot;stSidebar&quot;] p,
[data-testid=&quot;stSidebar&quot;] span { color: #FFFFFF !important; }
[data-testid=&quot;stSidebar&quot;] .stSelectbox div[data-baseweb=&quot;select&quot;] &gt; div {
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
[data-testid=&quot;stMetric&quot;] {
background-color: var(--card-bg); border: 1px solid var(--border-subtle);
border-top: 3px solid var(--navy); border-radius: 8px; padding: 12px 16px;
}
&lt;/style&gt;
&quot;&quot;&quot;,
unsafe_allow_html=True,

)
ROLE_MENUS = {
&quot;Admin / Clinic Owner&quot;: [
&quot;Front Desk &amp; Queue&quot;,
&quot;Clinical Assessment&quot;,
&quot;Patient Registration&quot;,
&quot;Daily Treatment Log&quot;,
&quot;Billing &amp; Reminders&quot;,
&quot;Progress &amp; Summary&quot;,
&quot;Admin Panel &amp; Settings&quot;,
],
&quot;Physiotherapist&quot;: [
&quot;Front Desk &amp; Queue&quot;,
&quot;Clinical Assessment&quot;,
&quot;Patient Registration&quot;,
&quot;Daily Treatment Log&quot;,
&quot;Progress &amp; Summary&quot;,
],
&quot;Front Desk&quot;: [
&quot;Front Desk &amp; Queue&quot;,
&quot;Patient Registration&quot;,
&quot;Billing &amp; Reminders&quot;,
&quot;Progress &amp; Summary&quot;,
],
}
def render_patient_banner(patients_df: pd.DataFrame, selected_pid: str) -&gt; str:
pid_col = col_val(patients_df, [&quot;patient_id&quot;, &quot;Patient_ID&quot;])
name_col = col_val(patients_df, [&quot;name&quot;, &quot;Name&quot;])
phone_col = col_val(patients_df, [&quot;phone&quot;, &quot;Phone&quot;])
gender_col = col_val(patients_df, [&quot;gender&quot;, &quot;Gender&quot;])
hist_col = col_val(patients_df, [&quot;medical_history&quot;, &quot;Medical_History&quot;])
clinic_col = col_val(patients_df, [&quot;clinic&quot;, &quot;Clinic&quot;])
row = patients_df[patients_df[pid_col] == selected_pid]
if row.empty:
return &quot;&quot;
r = row.iloc[0]
p_name = r.get(name_col, &quot;N/A&quot;) if name_col else &quot;N/A&quot;
p_phone = r.get(phone_col, &quot;N/A&quot;) if phone_col else &quot;N/A&quot;
p_gender = r.get(gender_col, &quot;N/A&quot;) if gender_col else &quot;N/A&quot;
p_clinic = r.get(clinic_col, &quot;A-3 Paschim Vihar&quot;) if clinic_col else &quot;A-3 Paschim Vihar&quot;
p_hist = str(r.get(hist_col, &quot;&quot;) or &quot;&quot;).strip()
st.markdown(
f&quot;&quot;&quot;
&lt;div class=&quot;patient-strip&quot;&gt;
&lt;strong&gt;Patient Assessment:&lt;/strong&gt; {p_name} &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;ID:&lt;/strong&gt; &lt;code&gt;{selected_pid}&lt;/code&gt; &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;Gender:&lt;/strong&gt; {p_gender} &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;Phone:&lt;/strong&gt; {p_phone} &amp;nbsp;•&amp;nbsp;
&lt;strong&gt;Branch:&lt;/strong&gt; {p_clinic}
&lt;/div&gt;
&quot;&quot;&quot;,
unsafe_allow_html=True,
)
if p_hist:
alert_keywords = [&quot;diabet&quot;, &quot;hypertens&quot;, &quot;bp&quot;, &quot;anticoagulant&quot;, &quot;blood thinner&quot;, &quot;pregnan&quot;, &quot;osteopor&quot;,
&quot;cancer&quot;, &quot;surger&quot;, &quot;fracture&quot;, &quot;pacemaker&quot;]
if any(k in p_hist.lower() for k in alert_keywords):
st.warning(f&quot;⚠️ **Medical Precaution Flags:** {p_hist}&quot;)
else:
st.info(f&quot;�� **Medical Notes:** {p_hist}&quot;)

return p_hist
cfg = get_clinic_settings()
branches = get_branches_list()
if &quot;auth_user&quot; not in st.session_state:
st.session_state[&quot;auth_user&quot;] = None
if st.session_state[&quot;auth_user&quot;] is None:
st.markdown(
f&quot;&quot;&quot;
&lt;div class=&quot;clinic-banner&quot;&gt;
&lt;h1&gt;�� {cfg.get(&#39;clinic_title&#39;)}&lt;/h1&gt;
&lt;p class=&quot;clinic-tagline&quot;&gt;{cfg.get(&#39;clinic_tagline&#39;)}&lt;/p&gt;
&lt;span class=&quot;clinic-badge&quot;&gt;{cfg.get(&#39;clinic_badge&#39;)}&lt;/span&gt;
&lt;/div&gt;
&quot;&quot;&quot;,
unsafe_allow_html=True,
)
_, col_mid, _ = st.columns([1, 1.35, 1])
with col_mid:
st.markdown(&#39;&lt;div class=&quot;login-card&quot;&gt;&#39;, unsafe_allow_html=True)
try:
st.image(cfg.get(&quot;logo_path&quot;, &quot;image_500b64.jpg&quot;), width=180)
except Exception:
pass
st.markdown(&quot;### �� Staff &amp; Clinician Sign-In&quot;)
with st.form(&quot;staff_login_form&quot;):
login_email = st.text_input(&quot;Staff Email or ID&quot;, value=&quot;dr.geetanjali@physioworks.in&quot;)
login_pass = st.text_input(&quot;Password / Clinic PIN&quot;, type=&quot;password&quot;, placeholder=&quot;Enter password&quot;)
login_branch = st.selectbox(&quot;Select Active Clinic Branch&quot;, branches + [&quot;All Clinics&quot;])
if st.form_submit_button(&quot;Sign In to Clinic Workspace&quot;):
user_rec = authenticate_staff(login_email, login_pass)
if user_rec:
if user_rec.get(&quot;role&quot;) != &quot;Admin / Clinic Owner&quot; and login_branch == &quot;All Clinics&quot;:
login_branch = user_rec.get(&quot;assigned_clinic&quot;) or branches[0]
st.session_state[&quot;auth_user&quot;] = user_rec
st.session_state[&quot;active_clinic&quot;] = login_branch
st.rerun()
else:
st.error(&quot;Invalid staff credentials.&quot;)
with st.expander(&quot;ℹ️ Default Clinic Login Credentials&quot;):
st.markdown(
&quot;&quot;&quot;
- **Admin / Clinic Owner:** `dr.geetanjali@physioworks.in` / `admin123`
- **Physiotherapist:** `physio@physioworks.in` / `physio123`
- **Front Desk:** `desk@physioworks.in` / `desk123`
&quot;&quot;&quot;
)
st.markdown(&quot;&lt;/div&gt;&quot;, unsafe_allow_html=True)
st.stop()
current_user = st.session_state[&quot;auth_user&quot;]
active_role = current_user.get(&quot;role&quot;, &quot;Physiotherapist&quot;)
allowed_menus = ROLE_MENUS.get(active_role, ROLE_MENUS[&quot;Physiotherapist&quot;])
with st.sidebar:
try:
st.sidebar.image(cfg.get(&quot;logo_path&quot;, &quot;image_500b64.jpg&quot;), width=210)
except Exception:
st.sidebar.markdown(f&quot;### �� {cfg.get(&#39;clinic_title&#39;)}&quot;)
st.markdown(&quot;---&quot;)
st.markdown(f&quot;**�� {current_user.get(&#39;full_name&#39;, &#39;Staff&#39;)}**&quot;)

st.caption(f&quot;Role: {active_role}&quot;)
branch_choices = branches + [&quot;All Clinics&quot;] if active_role == &quot;Admin / Clinic Owner&quot; else branches
default_branch = st.session_state.get(&quot;active_clinic&quot;, branches[0])
if default_branch not in branch_choices:
default_branch = branch_choices[0]
active_clinic = st.selectbox(&quot;Active Clinic&quot;, branch_choices, index=branch_choices.index(default_branch))
st.session_state[&quot;active_clinic&quot;] = active_clinic
menu = st.selectbox(&quot;Clinic Workspace&quot;, allowed_menus)
st.markdown(&quot;---&quot;)
if get_gemini_api_key():
st.success(&quot;● Gemini AI: Key Configured&quot;)
else:
st.info(&quot;● Gemini AI: Fallback Mode&quot;)
if db_connected:
st.success(&quot;● Supabase Cloud Sync: Active&quot;)
else:
st.info(&quot;● Storage Mode: Session Memory&quot;)
if st.button(&quot;�� Sign Out&quot;):
st.session_state[&quot;auth_user&quot;] = None
st.rerun()
patients_all = filter_by_clinic(get_data(&quot;patients&quot;), active_clinic)
assessments_all = filter_by_clinic(get_data(&quot;assessments&quot;), active_clinic)
logs_all = filter_by_clinic(get_data(&quot;daily_logs&quot;), active_clinic)
appointments_all = filter_by_clinic(get_data(&quot;appointments&quot;), active_clinic)
billing_all = filter_by_clinic(get_data(&quot;billing&quot;), active_clinic)
st.markdown(
f&quot;&quot;&quot;
&lt;div class=&quot;clinic-banner&quot;&gt;
&lt;h1&gt;�� {cfg.get(&#39;clinic_title&#39;)}&lt;/h1&gt;
&lt;p class=&quot;clinic-tagline&quot;&gt;{cfg.get(&#39;clinic_tagline&#39;)}&lt;/p&gt;
&lt;span class=&quot;clinic-badge&quot;&gt;{cfg.get(&#39;clinic_badge&#39;)}&lt;/span&gt;
&lt;span class=&quot;clinic-pill-meta&quot;&gt;�� {active_clinic} &amp;nbsp;|&amp;nbsp; �� {current_user.get(&#39;full_name&#39;
({active_role})&lt;/span&gt;
&lt;/div&gt;
&quot;&quot;&quot;,
unsafe_allow_html=True,
)
k1, k2, k3, k4 = st.columns(4)
k1.metric(&quot;Patients&quot;, len(patients_all))
k2.metric(&quot;Queue Appointments&quot;, len(appointments_all))
k3.metric(&quot;Assessments&quot;, len(assessments_all))
k4.metric(&quot;Sessions Logged&quot;, len(logs_all))
if menu == &quot;Front Desk &amp; Queue&quot;:
render_frontdesk_page(active_clinic, patients_all)
elif menu == &quot;Clinical Assessment&quot;:
render_assessment_page(active_clinic, patients_all, assessments_all, render_patient_banner)
elif menu == &quot;Patient Registration&quot;:
st.markdown(&#39;&lt;div class=&quot;ui-card&quot;&gt;&lt;div class=&quot;section-heading&quot;&gt;New Patient Intake Form&lt;/div&gt;&#39;,
unsafe_allow_html=True)
with st.form(&quot;reg_form&quot;):
c1, c2 = st.columns(2)
with c1:
name = st.text_input(&quot;Patient Full Name*&quot;)
email = st.text_input(&quot;Email Address&quot;)
gender = st.selectbox(&quot;Gender&quot;, [&quot;Female&quot;, &quot;Male&quot;, &quot;Other&quot;])
age_occ = st.text_input(&quot;Age / Occupation &amp; Activity Demands&quot;)

with c2:
phone = st.text_input(&quot;Phone Number*&quot;)
dominant_side = st.selectbox(&quot;Dominant Side&quot;, [&quot;Right&quot;, &quot;Left&quot;, &quot;Bilateral / Mixed&quot;])
referral = st.text_input(&quot;Referral Source&quot;)
med_history = st.text_area(&quot;Medical History &amp; Safety Flags&quot;)
reg_clinic = st.selectbox(&quot;Home Clinic Branch*&quot;, branches, index=0 if active_clinic == &quot;All Clinics&quot; else
branches.index(active_clinic))
if st.form_submit_button(&quot;Register &amp; Generate Patient ID&quot;):
if name and phone:
all_p = get_data(&quot;patients&quot;)
counter = len(all_p) + 1 if not all_p.empty else 1
patient_id = f&quot;PW{datetime.datetime.now().strftime(&#39;%m%y&#39;)}{counter:03d}&quot;
meta = [x for x in [
f&quot;Profile: {age_occ.strip()}&quot; if age_occ.strip() else &quot;&quot;,
f&quot;Dominant: {dominant_side}&quot; if dominant_side else &quot;&quot;,
f&quot;Ref: {referral.strip()}&quot; if referral.strip() else &quot;&quot;,
] if x]
combined_hist = f&quot;{med_history.strip()} | {&#39; ; &#39;.join(meta)}&quot;.strip(&quot; |&quot;) if meta else
med_history.strip()
save_data(&quot;patients&quot;, {
&quot;patient_id&quot;: patient_id,
&quot;name&quot;: name.strip(),
&quot;email&quot;: email.strip(),
&quot;gender&quot;: gender,
&quot;phone&quot;: phone.strip(),
&quot;clinic&quot;: reg_clinic,
&quot;medical_history&quot;: combined_hist,
&quot;registration_date&quot;: str(datetime.date.today()),
})
st.success(f&quot;Patient registered! Generated ID: **{patient_id}**&quot;)
st.rerun()
else:
st.error(&quot;Please enter both Patient Full Name and Phone Number.&quot;)
st.markdown(&quot;&lt;/div&gt;&quot;, unsafe_allow_html=True)
if not patients_all.empty:
st.markdown(&#39;&lt;div class=&quot;ui-card&quot;&gt;&lt;div class=&quot;section-heading&quot;&gt;Patient Directory&lt;/div&gt;&#39;,
unsafe_allow_html=True)
st.dataframe(patients_all, width=&quot;stretch&quot;, hide_index=True)
st.markdown(&quot;&lt;/div&gt;&quot;, unsafe_allow_html=True)
elif menu == &quot;Daily Treatment Log&quot;:
pid_col = col_val(patients_all, [&quot;patient_id&quot;, &quot;Patient_ID&quot;])
if patients_all.empty or not pid_col:
st.warning(&quot;Register a patient first under **Patient Registration**.&quot;)
else:
log_patient = st.selectbox(&quot;Select Patient&quot;, patients_all[pid_col].tolist())
render_patient_banner(patients_all, log_patient)
with st.form(&quot;daily_log_form&quot;):
c1, c2 = st.columns(2)
with c1:
log_date = st.date_input(&quot;Session Date*&quot;, datetime.date.today())
with c2:
current_vas = st.slider(&quot;Current Session NPRS (0–10)*&quot;, 0, 10, 3)
treatment_given = st.text_area(&quot;Treatment Provided*&quot;)
notes = st.text_area(&quot;Progress &amp; Next-Session Notes&quot;)
if st.form_submit_button(&quot;Save Daily Log&quot;):
save_data(&quot;daily_logs&quot;, {
&quot;patient_id&quot;: log_patient,
&quot;clinic&quot;: branches[0] if active_clinic == &quot;All Clinics&quot; else active_clinic,
&quot;session_date&quot;: str(log_date),
&quot;treatment_given&quot;: treatment_given,
&quot;current_vas&quot;: int(current_vas),
&quot;notes&quot;: notes.strip(),
})
st.success(&quot;Daily treatment log saved.&quot;)
st.rerun()

elif menu == &quot;Billing &amp; Reminders&quot;:
pid_col = col_val(patients_all, [&quot;patient_id&quot;, &quot;Patient_ID&quot;])
if patients_all.empty or not pid_col:
st.warning(&quot;Register a patient first under **Patient Registration**.&quot;)
else:
with st.form(&quot;billing_entry_form&quot;):
c1, c2, c3 = st.columns(3)
with c1:
b_pid = st.selectbox(&quot;Patient*&quot;, patients_all[pid_col].tolist())
b_pkg = st.selectbox(&quot;Plan / Package*&quot;, [&quot;Single Session&quot;, &quot;5-Session Rehab Pack&quot;, &quot;10-Session Recovery
Pack&quot;, &quot;Assessment + Initial Therapy&quot;])
with c2:
b_amt = st.number_input(&quot;Amount (₹)*&quot;, min_value=0, value=int(cfg.get(&quot;default_fee_inr&quot;, 800)),
step=100)
b_mode = st.selectbox(&quot;Payment Mode*&quot;, [&quot;UPI&quot;, &quot;Cash&quot;, &quot;Card&quot;, &quot;Pending&quot;])
with c3:
b_status = st.selectbox(&quot;Payment Status*&quot;, [&quot;Paid&quot;, &quot;Partial&quot;, &quot;Pending&quot;])
b_followup = st.date_input(&quot;Next Follow-Up Date&quot;, datetime.date.today() + datetime.timedelta(days=2))
if st.form_submit_button(&quot;Record Billing &amp; Follow-Up&quot;):
inv_id = f&quot;INV-{datetime.datetime.now().strftime(&#39;%Y%m%d%H%M%S&#39;)}&quot;
save_data(&quot;billing&quot;, {
&quot;invoice_id&quot;: inv_id,
&quot;patient_id&quot;: b_pid,
&quot;clinic&quot;: branches[0] if active_clinic == &quot;All Clinics&quot; else active_clinic,
&quot;package_name&quot;: b_pkg,
&quot;amount_inr&quot;: int(b_amt),
&quot;payment_mode&quot;: b_mode,
&quot;payment_status&quot;: b_status,
&quot;next_followup&quot;: str(b_followup),
&quot;date&quot;: str(datetime.date.today()),
})
st.success(f&quot;Saved billing entry `{inv_id}`.&quot;)
st.rerun()
if not billing_all.empty:
st.dataframe(billing_all, width=&quot;stretch&quot;, hide_index=True)
elif menu == &quot;Progress &amp; Summary&quot;:
pid_col = col_val(patients_all, [&quot;patient_id&quot;, &quot;Patient_ID&quot;])
if patients_all.empty or not pid_col:
st.warning(&quot;No patient records available.&quot;)
else:
dash_patient = st.selectbox(&quot;Select Patient&quot;, patients_all[pid_col].tolist())
render_patient_banner(patients_all, dash_patient)
p_asm = assessments_all[assessments_all[&quot;patient_id&quot;] == dash_patient] if (not assessments_all.empty and
&quot;patient_id&quot; in assessments_all.columns) else pd.DataFrame()
p_row = patients_all[patients_all[pid_col] == dash_patient].iloc[0].to_dict()
latest_asm = p_asm.iloc[-1].to_dict() if not p_asm.empty else None
pdf_bytes = create_assessment_pdf(p_row, asm_row=latest_asm, clinic_title=cfg.get(&quot;clinic_title&quot;),
logo_path=cfg.get(&quot;logo_path&quot;, &quot;image_500b64.jpg&quot;))
st.download_button(&quot;�� Download Patient Assessment PDF&quot;, data=pdf_bytes
file_name=f&quot;{dash_patient}_assessment.pdf&quot;, mime=&quot;application/pdf&quot;)
elif menu == &quot;Admin Panel &amp; Settings&quot;:
render_admin_panel()
