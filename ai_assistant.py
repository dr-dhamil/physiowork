import json
import os
import requests
import streamlit as st
try:
from google import genai
except Exception:
genai = None
EMBEDDED_GEMINI_API_KEY = "AQ.Ab8RN6JfoJBPrMm5AvpjzN0EcLDn1lcK0NBguCH3xmfM-lCF_A"
def get_gemini_api_key() -&gt; str:
try:
s_val = st.secrets.get(&quot;GEMINI_API_KEY&quot;)
if s_val and str(s_val).strip():
return str(s_val).strip()
except Exception:
pass
e_val = os.environ.get(&quot;GEMINI_API_KEY&quot;)
if e_val and e_val.strip():
return e_val.strip()
if EMBEDDED_GEMINI_API_KEY and EMBEDDED_GEMINI_API_KEY.strip():
return EMBEDDED_GEMINI_API_KEY.strip()
return &quot;&quot;
def generate_clinical_insights(context_payload: dict, detailed_plan: bool = False) -&gt; str:
api_key = get_gemini_api_key()
mode_instruction = (
&quot;Provide a detailed rehabilitation protocol with modalities, exercise dosage (sets/reps), &quot;
&quot;progression criteria, and home program.&quot;
if detailed_plan
else &quot;Provide concise clinical insights with likely tissue/movement pattern, safety notes, and focus.&quot;
)
prompt = (
&quot;You are a clinical physiotherapy decision-support assistant for Dr. Geetanjali&#39;s PhysioWorks.\n&quot;
&quot;Frame findings as clinical support (not a standalone medical diagnosis).\n&quot;
f&quot;{mode_instruction}\n\n&quot;
f&quot;Assessment Context:\n{json.dumps(context_payload, indent=2)}&quot;
)
models = [&quot;gemini-2.5-flash&quot;, &quot;gemini-2.5-flash-lite&quot;]
errors = []
if api_key:
if genai is not None:
try:
client = genai.Client(api_key=api_key)
for m in models:
try:
resp = client.models.generate_content(model=m, contents=prompt)
txt = getattr(resp, &quot;text&quot;, None)
if txt and txt.strip():
return txt.strip()
except Exception as ex:
errors.append(f&quot;SDK[{m}]: {ex}&quot;)

except Exception as ex:
errors.append(f&quot;SDK init: {ex}&quot;)
for m in models:
url = f&quot;https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent&quot;
try:
r = requests.post(
url,
params={&quot;key&quot;: api_key},
json={&quot;contents&quot;: [{&quot;parts&quot;: [{&quot;text&quot;: prompt}]}]},
timeout=30,
)
if r.status_code == 200:
data = r.json()
cands = data.get(&quot;candidates&quot;) or []
if cands:
parts = (cands[0].get(&quot;content&quot;) or {}).get(&quot;parts&quot;) or []
joined = &quot;&quot;.join(p.get(&quot;text&quot;, &quot;&quot;) for p in parts if p.get(&quot;text&quot;))
if joined.strip():
return joined.strip()
else:
errors.append(f&quot;REST[{m}] HTTP {r.status_code}&quot;)
except Exception as ex:
errors.append(f&quot;REST[{m}]: {ex}&quot;)
regions = &quot;, &quot;.join(context_payload.get(&quot;affected_regions&quot;) or [&quot;General Musculoskeletal&quot;])
nprs_act = context_payload.get(&quot;nprs_activity&quot;, &quot;N/A&quot;)
irr = context_payload.get(&quot;irritability&quot;, &quot;Moderate&quot;)
flags = context_payload.get(&quot;medical_history&quot;, &quot;None noted&quot;)
err_summary = &quot;; &quot;.join(errors[-2:]) if errors else &quot;No GEMINI_API_KEY configured&quot;
status_note = f&quot;*(Structured Clinical Fallback — {err_summary})*&quot;
if not detailed_plan:
return (
f&quot;{status_note}\n\n&quot;
f&quot;- **Primary Regions:** {regions}\n&quot;
f&quot;- **Activity NPRS &amp; Irritability:** {nprs_act}/10 | {irr}\n&quot;
f&quot;- **Precautions:** {flags}\n&quot;
f&quot;- **Focus:** Pain modulation, graded mobility, and neuromuscular control.&quot;
)
return (
f&quot;{status_note}\n\n&quot;
f&quot;### Detailed Rehabilitation Protocol ({regions})\n&quot;
f&quot;1. **Safety &amp; Irritability:** Respect **{irr}** and history (**{flags}**); keep pain &lt;= 3/10 during
drills.\n&quot;
f&quot;2. **Phase 1 (Sessions 1-4):** Modalities + gentle mobility/soft-tissue work (2 sets x 8-10 reps).\n&quot;
f&quot;3. **Phase 2 (Sessions 5-10):** Progressive isometric/isotonic strength &amp; motor control (3 sets x 10-12
reps).\n&quot;
f&quot;4. **Reassessment:** Track NPRS, ROM, MMT grade, and functional milestones at follow-up.&quot;
)
