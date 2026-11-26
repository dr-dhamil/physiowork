import datetime
import hashlib
import json
import os
import urllib.parse
from fpdf import FPDF
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

st.set_page_config(
    page_title="Dr. Geetanjali’s PhysioWorks",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- BRANDING & MODERN CLINIC UI THEME (#1B365D Navy & #F47920 Orange) ---
st.markdown(
    """
    <style>
    :root {
        --navy: #1B365D;
        --navy-dark: #122542;
        --orange: #F47920;
        --orange-hover: #D96412;
        --bg-soft: #F4F6F9;
        --card-bg: #FFFFFF;
        --border-subtle: #E2E8F0;
        --text-main: #1E293B;
    }

    .stApp {
        background-color: var(--bg-soft);
        color: var(--text-main);
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--navy) 0%, var(--navy-dark) 100%);
        border-right: 3px solid var(--orange);
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span {
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.12);
        color: #FFFFFF !important;
        border-color: rgba(255, 255, 255, 0.25);
    }

    .clinic-banner {
        background: linear-gradient(135deg, var(--navy) 0%, #24477A 100%);
        color: #FFFFFF;
        padding: 20px 26px;
        border-radius: 12px;
        border-bottom: 4px solid var(--orange);
        margin-bottom: 18px;
        box-shadow: 0 4px 12px rgba(27, 54, 93, 0.12);
    }
    .clinic-banner h1 {
        color: #FFFFFF !important;
        margin: 0 0 4px 0;
        font-size: 1.75rem;
        font-weight: 700;
    }
    .clinic-tagline {
        color: #FDBA74;
        font-size: 0.95rem;
        font-weight: 500;
        margin: 0;
    }
    .clinic-badge {
        display: inline-block;
        background-color: var(--orange);
        color: #FFFFFF;
        font-size: 0.78rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 999px;
        letter-spacing: 0.4px;
        margin-top: 8px;
        margin-right: 6px;
    }
    .clinic-pill-meta {
        display: inline-block;
        background-color: rgba(255, 255, 255, 0.14);
        color: #FFFFFF;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 999px;
        margin-top: 8px;
    }

    .ui-card {
        background-color: var(--card-bg);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    .login-card {
        background-color: var(--card-bg);
        border-top: 5px solid var(--orange);
        border-left: 1px solid var(--border-subtle);
        border-right: 1px solid var(--border-subtle);
        border-bottom: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 24px 28px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
    }
    .patient-strip {
        background-color: var(--card-bg);
        border-left: 5px solid var(--orange);
        border-top: 1px solid var(--border-subtle);
        border-right: 1px solid var(--border-subtle);
        border-bottom: 1px solid var(--border-subtle);
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    .section-heading {
        color: var(--navy) !important;
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0 0 12px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #F1F5F9;
    }

    h2, h3 {
        color: var(--navy) !important;
    }

    .stButton > button,
    .stFormSubmitButton > button,
    .stDownloadButton > button {
        background-color: var(--orange) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.1rem !important;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover,
    .stDownloadButton > button:hover {
        background-color: var(--orange-hover) !important;
        color: #FFFFFF !important;
    }

    [data-testid="stMetric"] {
        background-color: var(--card-bg);
        border: 1px solid var(--border-subtle);
        border-top: 3px solid var(--navy);
        border-radius: 8px;
        padding: 12px 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
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

CLINIC_BRANCHES = [
    "A-3 Paschim Vihar",
    "A-4 Paschim Vihar",
]

ROLE_OPTIONS = [
    "Admin / Clinic Owner",
    "Physiotherapist",
    "Front Desk",
]

ROLE_MENUS = {
    "Admin / Clinic Owner": [
        "Front Desk & Queue",
        "Clinical Assessment",
        "Patient Registration",
        "Daily Treatment Log",
        "Billing & Reminders",
        "Progress & Summary",
        "Staff & Clinic Management",
    ],
    "Physiotherapist": [
        "Front Desk & Queue",
        "Clinical Assessment",
        "Patient Registration",
        "Daily Treatment Log",
        "Progress & Summary",
    ],
    "Front Desk": [
        "Front Desk & Queue",
        "Patient Registration",
        "Billing & Reminders",
        "Progress & Summary",
    ],
}

# --- SUPABASE CONNECTION SETUP ---
try:
  SUPABASE_URL = st.secrets["https://cavsikyqrvguuocegsmv.supabase.co"]
  SUPABASE_KEY = st.secrets["sb_publishable_9EmHVLBa0f9wSDv69MD2Mw_aruWo_fh"]
except Exception:
  SUPABASE_URL = "https://cavsikyqrvguuocegsmv.supabase.co"
  SUPABASE_KEY = "sb_publishable_9EmHVLBa0f9wSDv69MD2Mw_aruWo_fh"

supabase = None
db_connected = False
try:
  if (
      SUPABASE_URL != "https://cavsikyqrvguuocegsmv.supabase.co"
      and SUPABASE_KEY != "sb_publishable_9EmHVLBa0f9wSDv69MD2Mw_aruWo_fh"
  ):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    db_connected = True
except Exception as e:
  st.sidebar.error(f"Supabase connection error: {e}")


def hash_password(raw_pw):
  return hashlib.sha256(str(raw_pw).strip().encode("utf-8")).hexdigest()


# Default built-in clinic accounts (used if staff_users table is empty/offline)
DEFAULT_STAFF_ACCOUNTS = [
    {
        "staff_id": "STF-001",
        "email": "dr.geetanjali@physioworks.in",
        "password_hash": hash_password("admin123"),
        "full_name": "Dr. Geetanjali",
        "role": "Admin / Clinic Owner",
        "assigned_clinic": "All Clinics",
        "active": True,
    },
    {
        "staff_id": "STF-002",
        "email": "physio@physioworks.in",
        "password_hash": hash_password("physio123"),
        "full_name": "Dr. Rohan",
        "role": "Physiotherapist",
        "assigned_clinic": "A-3 Paschim Vihar",
        "active": True,
    },
    {
        "staff_id": "STF-003",
        "email": "desk@physioworks.in",
        "password_hash": hash_password("desk123"),
        "full_name": "Front Desk Reception",
        "role": "Front Desk",
        "assigned_clinic": "A-4 Paschim Vihar",
        "active": True,
    },
]


def get_data(table_name):
  if supabase:
    try:
      response = supabase.table(table_name).select("*").execute()
      if response.data is not None:
        return pd.DataFrame(response.data)
    except Exception:
      pass
  if table_name not in st.session_state:
    st.session_state[table_name] = pd.DataFrame()
  return st.session_state[table_name]


def save_data(table_name, row_dict):
  if supabase:
    try:
      supabase.table(table_name).insert(row_dict).execute()
    except Exception as e:
      st.error(f"Error saving to Supabase: {e}")
      return
  if table_name not in st.session_state:
    st.session_state[table_name] = pd.DataFrame()
  new_df = pd.DataFrame([row_dict])
  st.session_state[table_name] = pd.concat(
      [st.session_state[table_name], new_df], ignore_index=True
  )


def get_staff_directory():
  df = get_data("staff_users")
  if df.empty:
    return pd.DataFrame(DEFAULT_STAFF_ACCOUNTS)
  return df


def authenticate_staff(login_id, raw_password):
  staff_df = get_staff_directory()
  pw_hash = hash_password(raw_password)
  clean_id = str(login_id).strip().lower()

  for _, row in staff_df.iterrows():
    email_val = str(row.get("email", "")).strip().lower()
    sid_val = str(row.get("staff_id", "")).strip().lower()
    stored_hash = str(row.get("password_hash", "")).strip()
    is_active = row.get("active", True)
    if is_active is False:
      continue
    if clean_id in (email_val, sid_val) and (
        pw_hash == stored_hash or str(raw_password).strip() == stored_hash
    ):
      return dict(row)
  return None


def update_appointment_status(appt_id, new_status):
  if supabase:
    try:
      supabase.table("appointments").update({"status": new_status}).eq(
          "appointment_id", appt_id
      ).execute()
    except Exception:
      pass
  if (
      "appointments" in st.session_state
      and not st.session_state["appointments"].empty
  ):
    df = st.session_state["appointments"].copy()
    id_col = col_val(df, ["appointment_id", "Appointment_ID"])
    st_col = col_val(df, ["status", "Status"])
    if id_col and st_col:
      df.loc[df[id_col] == appt_id, st_col] = new_status
      st.session_state["appointments"] = df


def filter_by_clinic(df, selected_clinic):
  if df.empty or selected_clinic == "All Clinics":
    return df
  clinic_col = col_val(df, ["clinic", "Clinic", "clinic_id"])
  if not clinic_col:
    return df
  return df[df[clinic_col] == selected_clinic]


def col_val(df, col_options, default=""):
  for c in col_options:
    if c in df.columns:
      return c
  return default


def format_patient_selector(patients_df, pid_col, name_col):
  patient_ids = patients_df[pid_col].tolist()

  def _fmt(pid):
    if name_col:
      match = patients_df[patients_df[pid_col] == pid]
      if not match.empty:
        return f"{pid} • {match.iloc[0][name_col]}"
    return pid

  return patient_ids, _fmt


def render_patient_banner(patients_df, selected_pid):
  pid_col = col_val(patients_df, ["patient_id", "Patient_ID"])
  name_col = col_val(patients_df, ["name", "Name"])
  phone_col = col_val(patients_df, ["phone", "Phone"])
  gender_col = col_val(patients_df, ["gender", "Gender"])
  hist_col = col_val(patients_df, ["medical_history", "Medical_History"])
  clinic_col = col_val(patients_df, ["clinic", "Clinic"])

  row = patients_df[patients_df[pid_col] == selected_pid]
  if row.empty:
    return ""

  r = row.iloc[0]
  p_name = r.get(name_col, "N/A") if name_col else "N/A"
  p_phone = r.get(phone_col, "N/A") if phone_col else "N/A"
  p_gender = r.get(gender_col, "N/A") if gender_col else "N/A"
  p_clinic = (
      r.get(clinic_col, "A-3 Paschim Vihar")
      if clinic_col
      else "A-3 Paschim Vihar"
  )
  p_hist = str(r.get(hist_col, "") or "").strip()

  st.markdown(
      f"""
      <div class="patient-strip">
          <strong>Active Patient:</strong> {p_name} &nbsp;•&nbsp;
          <strong>ID:</strong> <code>{selected_pid}</code> &nbsp;•&nbsp;
          <strong>Gender:</strong> {p_gender} &nbsp;•&nbsp;
          <strong>Phone:</strong> {p_phone} &nbsp;•&nbsp;
          <strong>Clinic:</strong> {p_clinic}
      </div>
      """,
      unsafe_allow_html=True,
  )

  if p_hist:
    alert_keywords = [
        "diabet",
        "hypertens",
        "bp",
        "anticoagulant",
        "blood thinner",
        "pregnan",
        "osteopor",
        "cancer",
        "surger",
        "fracture",
        "pacemaker",
    ]
    if any(k in p_hist.lower() for k in alert_keywords):
      st.warning(f"⚠️ **Medical Precaution Flags:** {p_hist}")
    else:
      st.info(f"📋 **Medical Notes:** {p_hist}")
  return p_hist


def render_true_3d_human_model(selected_regions):
  """True 3D WebGL Human Anatomy Model with live model switcher, camera presets & surface pain pins."""
  active_json = json.dumps(selected_regions)
  html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{
          margin: 0; background: #0B1324;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: #F8FAFC;
        }}
        #wrap {{
          position: relative; width: 100%; height: 500px;
          border-radius: 12px; overflow: hidden; border: 1px solid #334155;
          background: radial-gradient(circle at 50% 38%, #1E293B 0%, #0B1324 100%);
        }}
        .top-hud {{
          position: absolute; top: 10px; left: 10px; right: 10px;
          display: flex; justify-content: space-between; align-items: center;
          gap: 6px; z-index: 20; flex-wrap: wrap;
        }}
        .btn-row {{ display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }}
        .vbtn, select.vbtn {{
          background: rgba(27, 54, 93, 0.94); color: #F8FAFC;
          border: 1px solid #475569; padding: 5px 9px; border-radius: 6px;
          font-size: 11px; font-weight: 600; cursor: pointer;
        }}
        .vbtn:hover, select.vbtn:hover {{ background: #F47920; border-color: #F47920; }}
        .vbtn.clear {{ background: rgba(153, 27, 27, 0.92); border-color: #DC2626; }}
        #badge {{
          background: rgba(244, 121, 32, 0.95); color: #FFFFFF;
          padding: 5px 11px; border-radius: 999px; font-size: 11px; font-weight: 700;
        }}
        .bottom-hud {{
          position: absolute; bottom: 10px; left: 10px; right: 10px;
          background: rgba(15, 23, 42, 0.88); border: 1px solid #334155;
          border-radius: 8px; padding: 7px 12px; font-size: 11px; color: #CBD5E1;
          display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap;
        }}
        #pin-readout {{ color: #FDBA74; font-weight: 600; }}
      </style>
    </head>
    <body>
      <div id="wrap">
        <div class="top-hud">
          <div class="btn-row">
            <select id="model-switcher" class="vbtn" onchange="switchModel(this.value)">
              <option value="https://threejs.org/examples/models/gltf/Soldier.glb">Model: Soldier</option>
              <option value="https://threejs.org/examples/models/gltf/Xbot.glb">Model: Xbot</option>
              <option value="https://threejs.org/examples/models/gltf/Ybot.glb">Model: Ybot</option>
              <option value="https://threejs.org/examples/models/gltf/Michelle.glb">Model: Michelle</option>
              <option value="./anatomy_body.glb">Model: Custom (./anatomy_body.glb)</option>
            </select>
            <button class="vbtn" onclick="setAngle(0)">Front</button>
            <button class="vbtn" onclick="setAngle(Math.PI)">Back</button>
            <button class="vbtn" onclick="setAngle(Math.PI/2)">Left</button>
            <button class="vbtn" onclick="setAngle(-Math.PI/2)">Right</button>
            <button class="vbtn clear" onclick="clearPins()">Clear Pins</button>
          </div>
          <span id="badge">Loading 3D Soldier...</span>
        </div>
        <div class="bottom-hud">
          <span>360° Drag to Rotate • Scroll to Zoom • Click 3D body to place pain pin</span>
          <span id="pin-readout">Pain pins: 0</span>
        </div>
      </div>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
      <script>
        const activeRegions = new Set({active_json});
        const container = document.getElementById('wrap');
        const badgeEl = document.getElementById('badge');
        const pinReadoutEl = document.getElementById('pin-readout');

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(36, container.clientWidth / container.clientHeight, 0.05, 100);
        camera.position.set(0, 0.95, 3.35);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.outputEncoding = THREE.sRGBEncoding;
        container.appendChild(renderer.domElement);

        scene.add(new THREE.AmbientLight(0xE2E8F0, 0.65));
        const keyLight = new THREE.DirectionalLight(0xFFF7ED, 0.95);
        keyLight.position.set(2.5, 4.5, 3.5);
        scene.add(keyLight);
        const rimLight = new THREE.DirectionalLight(0x93C5FD, 0.55);
        rimLight.position.set(-2.5, 2.5, -3.5);
        scene.add(rimLight);
        const fillLight = new THREE.DirectionalLight(0xCBD5E1, 0.4);
        fillLight.position.set(0, -2.0, 2.5);
        scene.add(fillLight);

        const gridHelper = new THREE.PolarGridHelper(0.65, 16, 4, 48, 0x334155, 0x1E293B);
        gridHelper.position.y = 0.0;
        scene.add(gridHelper);

        const rootGroup = new THREE.Group();
        scene.add(rootGroup);

        const modelHolder = new THREE.Group();
        rootGroup.add(modelHolder);

        const glowHolder = new THREE.Group();
        rootGroup.add(glowHolder);

        const painPinsGroup = new THREE.Group();
        rootGroup.add(painPinsGroup);

        let clickableMeshes = [];
        const markedPins = [];

        const regionZones = [
          {{ label: "TMJ / Jaw", pos: new THREE.Vector3(0, 1.56, 0.08) }},
          {{ label: "Cervical Spine (Neck)", pos: new THREE.Vector3(0, 1.46, -0.02) }},
          {{ label: "Thoracic Spine (Upper Back)", pos: new THREE.Vector3(0, 1.24, -0.09) }},
          {{ label: "Lumbar Spine (Lower Back)", pos: new THREE.Vector3(0, 0.98, -0.08) }},
          {{ label: "Shoulder Complex", pos: new THREE.Vector3(-0.22, 1.36, 0) }},
          {{ label: "Shoulder Complex", pos: new THREE.Vector3( 0.22, 1.36, 0) }},
          {{ label: "Elbow", pos: new THREE.Vector3(-0.28, 1.10, -0.02) }},
          {{ label: "Elbow", pos: new THREE.Vector3( 0.28, 1.10, -0.02) }},
          {{ label: "Wrist & Hand", pos: new THREE.Vector3(-0.33, 0.84, 0.02) }},
          {{ label: "Wrist & Hand", pos: new THREE.Vector3( 0.33, 0.84, 0.02) }},
          {{ label: "Hip & Groin", pos: new THREE.Vector3(-0.11, 0.86, 0) }},
          {{ label: "Hip & Groin", pos: new THREE.Vector3( 0.11, 0.86, 0) }},
          {{ label: "Knee Joint", pos: new THREE.Vector3(-0.10, 0.48, 0.03) }},
          {{ label: "Knee Joint", pos: new THREE.Vector3( 0.10, 0.48, 0.03) }},
          {{ label: "Ankle & Foot", pos: new THREE.Vector3(-0.10, 0.08, 0.04) }},
          {{ label: "Ankle & Foot", pos: new THREE.Vector3( 0.10, 0.08, 0.04) }},
        ];

        function refreshRegionGlows() {{
          while (glowHolder.children.length > 0) {{
            glowHolder.remove(glowHolder.children[0]);
          }}
          regionZones.forEach(z => {{
            if (activeRegions.has(z.label)) {{
              const halo = new THREE.Mesh(
                new THREE.SphereGeometry(0.055, 16, 16),
                new THREE.MeshBasicMaterial({{ color: 0xF47920, transparent: true, opacity: 0.48 }})
              );
              halo.position.copy(z.pos);
              glowHolder.add(halo);
            }}
          }});
        }}

        function clearCurrentModel() {{
          while (modelHolder.children.length > 0) {{
            modelHolder.remove(modelHolder.children[0]);
          }}
          clickableMeshes = [];
        }}

        function buildProceduralFallback() {{
          clearCurrentModel();
          const skinMat = new THREE.MeshStandardMaterial({{
            color: 0xD6B098, roughness: 0.46, metalness: 0.04
          }});
          function lathe(pts, x, y, z, sx=1, sy=1, sz=1, rz=0) {{
            const g = new THREE.LatheGeometry(pts.map(p => new THREE.Vector2(p[0], p[1])), 28);
            const m = new THREE.Mesh(g, skinMat);
            m.position.set(x, y, z); m.scale.set(sx, sy, sz); m.rotation.z = rz;
            modelHolder.add(m); clickableMeshes.push(m);
          }}
          function sphere(r, x, y, z, sx=1, sy=1, sz=1) {{
            const m = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 20), skinMat);
            m.position.set(x, y, z); m.scale.set(sx, sy, sz);
            modelHolder.add(m); clickableMeshes.push(m);
          }}
          sphere(0.115, 0, 1.66, 0, 0.9, 1.15, 1.0);
          sphere(0.085, 0, 1.56, 0.03, 0.85, 0.85, 0.9);
          lathe([[0.058,0],[0.054,0.08],[0.062,0.16]], 0, 1.40, 0);
          lathe([[0.12,0],[0.16,0.12],[0.135,0.28],[0.175,0.48],[0.185,0.58],[0.12,0.65]], 0, 0.78, 0, 1.08, 1, 0.65);
          [-1,1].forEach(s => {{
            sphere(0.068, s*0.21, 1.36, 0);
            lathe([[0.04,0],[0.052,0.25]], s*0.25, 1.11, 0, 1,1,1, -s*0.12);
            lathe([[0.028,0],[0.04,0.24]], s*0.30, 0.86, 0.02, 1,1,1, -s*0.10);
            lathe([[0.05,0],[0.082,0.38]], s*0.095, 0.47, 0);
            lathe([[0.036,0],[0.052,0.38]], s*0.095, 0.08, -0.01);
            sphere(0.04, s*0.095, 0.03, 0.045, 0.9, 0.5, 1.8);
          }});
          badgeEl.textContent = "Fallback 3D Model • Click skin to mark pain";
        }}

        const loader = new THREE.GLTFLoader();

        window.switchModel = function(url, isRetryFallback = false) {{
          badgeEl.textContent = "Loading 3D model...";
          loader.load(
            url,
            function(gltf) {{
              clearCurrentModel();
              const model = gltf.scene;
              const box = new THREE.Box3().setFromObject(model);
              const size = new THREE.Vector3();
              box.getSize(size);
              const scaleFactor = 1.76 / (size.y || 1);
              model.scale.setScalar(scaleFactor);

              const scaledBox = new THREE.Box3().setFromObject(model);
              const center = new THREE.Vector3();
              scaledBox.getCenter(center);
              model.position.x = -center.x;
              model.position.z = -center.z;
              model.position.y = -scaledBox.min.y;

              const clinicalMat = new THREE.MeshStandardMaterial({{
                color: 0xCBD5E1,
                roughness: 0.45,
                metalness: 0.08
              }});

              model.traverse(child => {{
                if (child.isMesh) {{
                  child.material = clinicalMat;
                  clickableMeshes.push(child);
                }}
              }});

              modelHolder.add(model);
              const labelName = url.split('/').pop().replace('.glb', '');
              badgeEl.textContent = `3D: ${{labelName}} • Click body to mark pain`;
            }},
            undefined,
            function() {{
              if (!isRetryFallback && url !== "https://threejs.org/examples/models/gltf/Soldier.glb") {{
                document.getElementById('model-switcher').value = "https://threejs.org/examples/models/gltf/Soldier.glb";
                window.switchModel("https://threejs.org/examples/models/gltf/Soldier.glb", true);
              }} else {{
                buildProceduralFallback();
              }}
            }}
          );
        }};

        function classifyPoint(pt) {{
          let best = regionZones[0].label;
          let minD = Infinity;
          regionZones.forEach(z => {{
            const d = pt.distanceTo(z.pos);
            if (d < minD) {{ minD = d; best = z.label; }}
          }});
          const lr = pt.x < -0.035 ? "Left " : (pt.x > 0.035 ? "Right " : "Central ");
          const ap = pt.z < -0.025 ? "Posterior " : (pt.z > 0.025 ? "Anterior " : "");
          return `${{lr}}${{ap}}${{best}}`;
        }}

        function dropPainPin(localPt) {{
          const num = markedPins.length + 1;
          const pinCore = new THREE.Mesh(
            new THREE.SphereGeometry(0.024, 16, 16),
            new THREE.MeshStandardMaterial({{ color: 0xEF4444, emissive: 0xB91C1C, roughness: 0.2 }})
          );
          pinCore.position.copy(localPt);

          const pinRing = new THREE.Mesh(
            new THREE.SphereGeometry(0.044, 16, 16),
            new THREE.MeshBasicMaterial({{ color: 0xF47920, transparent: true, opacity: 0.45 }})
          );
          pinRing.position.copy(localPt);

          painPinsGroup.add(pinCore);
          painPinsGroup.add(pinRing);

          const desc = `#${{num}} ${{classifyPoint(localPt)}}`;
          markedPins.push(desc);
          badgeEl.textContent = "Marked: " + desc;
          pinReadoutEl.textContent = "Pain pins (" + markedPins.length + "): " + markedPins.slice(-2).join(" | ");
        }}

        window.clearPins = function() {{
          while (painPinsGroup.children.length > 0) {{
            painPinsGroup.remove(painPinsGroup.children[0]);
          }}
          markedPins.length = 0;
          badgeEl.textContent = "Pain pins cleared";
          pinReadoutEl.textContent = "Pain pins: 0";
        }};

        window.setAngle = function(radY) {{
          rootGroup.rotation.y = radY;
          rootGroup.rotation.x = 0;
        }};

        let dragging = false, moved = false, prevX = 0, prevY = 0;
        renderer.domElement.addEventListener('pointerdown', e => {{
          dragging = true; moved = false; prevX = e.clientX; prevY = e.clientY;
        }});
        window.addEventListener('pointerup', () => {{ dragging = false; }});

        renderer.domElement.addEventListener('wheel', e => {{
          e.preventDefault();
          camera.position.z = Math.max(1.75, Math.min(4.8, camera.position.z + e.deltaY * 0.002));
        }}, {{ passive: false }});

        const raycaster = new THREE.Raycaster();
        const pointer = new THREE.Vector2();

        renderer.domElement.addEventListener('pointermove', e => {{
          if (!dragging) return;
          const dx = e.clientX - prevX;
          const dy = e.clientY - prevY;
          if (Math.abs(dx) > 2 || Math.abs(dy) > 2) moved = true;
          rootGroup.rotation.y += dx * 0.012;
          rootGroup.rotation.x = Math.max(-0.4, Math.min(0.4, rootGroup.rotation.x + dy * 0.008));
          prevX = e.clientX; prevY = e.clientY;
        }});

        renderer.domElement.addEventListener('click', e => {{
          if (moved) return;
          const rect = renderer.domElement.getBoundingClientRect();
          pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
          pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
          raycaster.setFromCamera(pointer, camera);
          const hits = raycaster.intersectObjects(clickableMeshes, true);
          if (hits.length > 0) {{
            const localPt = rootGroup.worldToLocal(hits[0].point.clone());
            dropPainPin(localPt);
          }}
        }});

        refreshRegionGlows();
        window.switchModel(document.getElementById('model-switcher').value);

        function animate() {{
          requestAnimationFrame(animate);
          renderer.render(scene, camera);
        }}
        animate();
      </script>
    </body>
    </html>
    """
  components.html(html_code, height=514)


def _latin1_safe(text):
  return str(text or "").encode("latin-1", errors="replace").decode("latin-1")


def create_assessment_pdf(
    patient_row, asm_row=None, logo_path="image_500b64.jpg"
):
  pdf = FPDF()
  pdf.set_auto_page_break(auto=True, margin=15)
  pdf.add_page()

  try:
    pdf.image(logo_path, x=12, y=10, w=32)
  except Exception:
    pass

  pdf.set_xy(48, 12)
  pdf.set_font("Helvetica", "B", 16)
  pdf.set_text_color(27, 54, 93)
  pdf.cell(0, 8, _latin1_safe("Dr. Geetanjali's PhysioWorks"), ln=True)

  pdf.set_x(48)
  pdf.set_font("Helvetica", "", 10)
  pdf.set_text_color(244, 121, 32)
  pdf.cell(
      0,
      6,
      _latin1_safe(
          "Physiotherapy | Osteopathy | Chiropractic - Clinical Assessment"
          " Record"
      ),
      ln=True,
  )

  pdf.ln(10)
  pdf.set_draw_color(244, 121, 32)
  pdf.set_line_width(0.8)
  pdf.line(12, pdf.get_y(), 198, pdf.get_y())
  pdf.ln(6)

  pdf.set_font("Helvetica", "B", 12)
  pdf.set_text_color(27, 54, 93)
  pdf.cell(0, 8, _latin1_safe("1. Patient Profile & Screening"), ln=True)

  pdf.set_font("Helvetica", "", 10)
  pdf.set_text_color(30, 41, 59)
  pid = patient_row.get("patient_id") or patient_row.get("Patient_ID", "N/A")
  name = patient_row.get("name") or patient_row.get("Name", "N/A")
  gender = patient_row.get("gender") or patient_row.get("Gender", "N/A")
  phone = patient_row.get("phone") or patient_row.get("Phone", "N/A")
  clinic = patient_row.get("clinic") or patient_row.get(
      "Clinic", "A-3 Paschim Vihar"
  )
  reg_date = patient_row.get("registration_date") or patient_row.get(
      "Registration_Date", str(datetime.date.today())
  )
  med_hist = patient_row.get("medical_history") or patient_row.get(
      "Medical_History", "None reported"
  )

  pdf.cell(95, 7, _latin1_safe(f"Patient ID: {pid} ({clinic})"), border=1)
  pdf.cell(91, 7, _latin1_safe(f"Date: {reg_date}"), border=1, ln=True)
  pdf.cell(95, 7, _latin1_safe(f"Name: {name}"), border=1)
  pdf.cell(
      91, 7, _latin1_safe(f"Gender / Phone: {gender} | {phone}"), border=1, ln=True
  )
  pdf.multi_cell(
      186,
      7,
      _latin1_safe(f"Medical History & Safety Flags: {med_hist}"),
      border=1,
  )
  pdf.ln(5)

  pdf.set_font("Helvetica", "B", 12)
  pdf.set_text_color(27, 54, 93)
  pdf.cell(
      0, 8, _latin1_safe("2. Clinical Assessment & Examination Findings"), ln=True
  )

  pdf.set_font("Helvetica", "", 10)
  pdf.set_text_color(30, 41, 59)

  if asm_row is not None:
    asm_id = asm_row.get("assessment_id") or asm_row.get(
        "Assessment_ID", "N/A"
    )
    asm_date = asm_row.get("date") or asm_row.get("Date", "N/A")
    regions = asm_row.get("body_parts") or asm_row.get("Body_Parts", "N/A")
    vas = asm_row.get("vas_score") or asm_row.get("VAS_Score", "N/A")
    details = asm_row.get("assessment_details") or asm_row.get(
        "Assessment_Details", "N/A"
    )
    plan = asm_row.get("suggested_treatment") or asm_row.get(
        "Suggested_Treatment", "N/A"
    )
    duration = asm_row.get("suggested_duration") or asm_row.get(
        "Suggested_Duration", "N/A"
    )
    therapist = asm_row.get("therapist") or asm_row.get("Therapist", "N/A")

    pdf.cell(95, 7, _latin1_safe(f"Assessment ID: {asm_id}"), border=1)
    pdf.cell(
        91, 7, _latin1_safe(f"Assessment Date: {asm_date}"), border=1, ln=True
    )
    pdf.cell(140, 7, _latin1_safe(f"Affected Region(s): {regions}"), border=1)
    pdf.cell(46, 7, _latin1_safe(f"Activity NPRS: {vas}/10"), border=1, ln=True)
    pdf.multi_cell(
        186,
        7,
        _latin1_safe(f"Examination, ROM, Special Tests & MMT:\n{details}"),
        border=1,
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(27, 54, 93)
    pdf.cell(
        0, 8, _latin1_safe("3. Rehabilitation Plan & Therapist Assignment"), ln=True
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(
        186, 7, _latin1_safe(f"Suggested Modalities & Plan:\n{plan}"), border=1
    )
    pdf.cell(
        95, 7, _latin1_safe(f"Recommended Duration: {duration}"), border=1
    )
    pdf.cell(
        91, 7, _latin1_safe(f"Assigned Therapist: {therapist}"), border=1, ln=True
    )
  else:
    blank_sections = [
        "Chief Complaint, Onset & 24-Hr Behavior:",
        "NPRS Pain Score - Rest: ___/10   Activity: ___/10   Night: ___/10",
        "Observation & Posture:",
        "Active / Passive ROM & End-Feel:",
        "Neurological Screen (Myotomes / Dermatomes / Reflexes):",
        "Manual Muscle Testing (MMT 0-5) & Strength:",
        "Region-Specific Special Tests & Side Comparison:",
        "Clinical Impression & Differential Diagnosis:",
        "Treatment Plan, Modalities & Home Exercise Program:",
    ]
    for sec in blank_sections:
      pdf.multi_cell(186, 12, _latin1_safe(sec), border=1)

  pdf.ln(12)
  pdf.set_font("Helvetica", "I", 9)
  pdf.set_text_color(100, 116, 139)
  pdf.cell(
      0,
      6,
      _latin1_safe(
          "Clinician Signature: ___________________________      Date:"
          " _______________"
      ),
      ln=True,
  )

  return bytes(pdf.output())


if "asm_body_parts" not in st.session_state:
  st.session_state["asm_body_parts"] = []

# =====================================================================
# MODULE 0: STAFF AUTHENTICATION & LOGIN GATE
# =====================================================================
if "auth_user" not in st.session_state:
  st.session_state["auth_user"] = None

if st.session_state["auth_user"] is None:
  st.markdown(
      """
      <div class="clinic-banner">
          <h1>🩺 Dr. Geetanjali’s PhysioWorks</h1>
          <p class="clinic-tagline">Physiotherapy • Osteopathy • Chiropractic — A-3 & A-4 Paschim Vihar Clinical Suite</p>
          <span class="clinic-badge">GET THE CARE YOU DESERVE</span>
      </div>
      """,
      unsafe_allow_html=True,
  )

  col_l1, col_l2, col_l3 = st.columns([1, 1.35, 1])
  with col_l2:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    try:
      st.image("image_500b64.jpg", width=180)
    except Exception:
      pass
    st.markdown("### 🔐 Staff & Clinician Sign-In")
    with st.form("staff_login_form"):
      login_email = st.text_input(
          "Staff Email or ID",
          value="dr.geetanjali@physioworks.in",
          placeholder="e.g., dr.geetanjali@physioworks.in",
      )
      login_pass = st.text_input(
          "Password / Clinic PIN",
          type="password",
          placeholder="Enter your password",
      )
      login_branch = st.selectbox(
          "Select Active Clinic Branch",
          CLINIC_BRANCHES + ["All Clinics"],
      )
      login_btn = st.form_submit_button("Sign In to Clinic Workspace")

      if login_btn:
        user_rec = authenticate_staff(login_email, login_pass)
        if user_rec:
          if (
              user_rec.get("role") != "Admin / Clinic Owner"
              and login_branch == "All Clinics"
          ):
            login_branch = user_rec.get("assigned_clinic") or CLINIC_BRANCHES[0]
          st.session_state["auth_user"] = user_rec
          st.session_state["active_clinic"] = login_branch
          st.rerun()
        else:
          st.error(
              "Invalid staff credentials. Please check your email/ID and"
              " password."
          )

    with st.expander("ℹ️ Default Clinic Login Credentials"):
      st.markdown(
          """
          - **Admin / Clinic Owner:** `dr.geetanjali@physioworks.in` / `admin123`
          - **Physiotherapist:** `physio@physioworks.in` / `physio123`
          - **Front Desk:** `desk@physioworks.in` / `desk123`
          """
      )
    st.markdown("</div>", unsafe_allow_html=True)
  st.stop()

# --- AUTHENTICATED USER SESSION ---
current_user = st.session_state["auth_user"]
active_role = current_user.get("role", "Physiotherapist")
allowed_menus = ROLE_MENUS.get(active_role, ROLE_MENUS["Physiotherapist"])

with st.sidebar:
  try:
    st.sidebar.image("image_500b64.jpg", width=210)
  except Exception:
    st.sidebar.markdown("### 🩺 PhysioWorks")

  st.markdown("---")
  st.markdown(f"**👤 {current_user.get('full_name', 'Staff')}**")
  st.caption(f"Role: {active_role}")

  branch_choices = (
      CLINIC_BRANCHES + ["All Clinics"]
      if active_role == "Admin / Clinic Owner"
      else CLINIC_BRANCHES
  )
  default_branch = st.session_state.get("active_clinic", CLINIC_BRANCHES[0])
  if default_branch not in branch_choices:
    default_branch = branch_choices[0]

  active_clinic = st.selectbox(
      "Active Clinic",
      branch_choices,
      index=branch_choices.index(default_branch),
  )
  st.session_state["active_clinic"] = active_clinic

  menu = st.selectbox("Clinic Workspace", allowed_menus)

  st.markdown("---")
  if db_connected:
    st.success("● Supabase Cloud Sync: Active")
  else:
    st.info("● Storage Mode: Session Memory")

  if st.button("🚪 Sign Out"):
    st.session_state["auth_user"] = None
    st.rerun()

# --- TOP BANNER & CLINIC SNAPSHOT ---
patients_all = filter_by_clinic(get_data("patients"), active_clinic)
assessments_all = filter_by_clinic(get_data("assessments"), active_clinic)
logs_all = filter_by_clinic(get_data("daily_logs"), active_clinic)
appointments_all = filter_by_clinic(get_data("appointments"), active_clinic)
billing_all = filter_by_clinic(get_data("billing"), active_clinic)

st.markdown(
    f"""
    <div class="clinic-banner">
        <h1>🩺 Dr. Geetanjali’s PhysioWorks</h1>
        <p class="clinic-tagline">Physiotherapy • Osteopathy • Chiropractic — Clinical Documentation, Queue & Rehabilitation Suite</p>
        <span class="clinic-badge">GET THE CARE YOU DESERVE</span>
        <span class="clinic-pill-meta">📍 {active_clinic} &nbsp;|&nbsp; 👤 {current_user.get('full_name')} ({active_role})</span>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Patients", len(patients_all))
k2.metric("Queue Appointments", len(appointments_all))
k3.metric("Assessments", len(assessments_all))
k4.metric("Sessions Logged", len(logs_all))

# =====================================================================
# 1. FRONT DESK & APPOINTMENT QUEUE BOARD
# =====================================================================
if menu == "Front Desk & Queue":
  pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
  name_col = col_val(patients_all, ["name", "Name"])

  st.markdown(
      '<div class="ui-card"><div class="section-heading">Book Appointment'
      " & Check-In</div>",
      unsafe_allow_html=True,
  )
  if patients_all.empty or not pid_col:
    st.warning(
        "Register a patient first under **Patient Registration** to add to"
        " the queue."
    )
  else:
    patient_ids, fmt_fn = format_patient_selector(
        patients_all, pid_col, name_col
    )
    with st.form("queue_booking_form"):
      c1, c2, c3, c4 = st.columns(4)
      with c1:
        q_pid = st.selectbox(
            "Patient", patient_ids, format_func=fmt_fn, key="q_pid"
        )
        q_date = st.date_input(
            "Date", datetime.date.today(), key="q_date_input"
        )
      with c2:
        q_slot = st.selectbox(
            "Time Slot",
            [
                "09:00 AM",
                "09:45 AM",
                "10:30 AM",
                "11:15 AM",
                "12:00 PM",
                "04:00 PM",
                "04:45 PM",
                "05:30 PM",
                "06:15 PM",
                "07:00 PM",
            ],
        )
        q_type = st.selectbox(
            "Visit Type",
            [
                "Initial Assessment",
                "Follow-Up Therapy",
                "Reassessment",
                "Home Program Review",
            ],
        )
      with c3:
        q_therapist = st.selectbox(
            "Assigned Therapist",
            ["Dr. Geetanjali", "Dr. Rohan", "Dr. Senior Consultant"],
            key="q_therapist",
        )
        q_clinic = (
            CLINIC_BRANCHES[0]
            if active_clinic == "All Clinics"
            else active_clinic
        )
        st.text_input("Clinic Location", value=q_clinic, disabled=True)
      with c4:
        q_status = st.selectbox(
            "Queue Status",
            ["Scheduled", "Checked-In", "In-Session", "Completed"],
        )
        q_note = st.text_input("Front-Desk Note", placeholder="e.g., Walk-in")

      add_queue = st.form_submit_button("Add to Front-Desk Board")
      if add_queue:
        appt_id = f"APT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        p_match = patients_all[patients_all[pid_col] == q_pid]
        p_label = (
            f"{q_pid} - {p_match.iloc[0][name_col]}"
            if (name_col and not p_match.empty)
            else q_pid
        )
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

  st.markdown(
      '<div class="ui-card"><div class="section-heading">Live Front-Desk'
      " Queue Board</div>",
      unsafe_allow_html=True,
  )
  raw_appts = filter_by_clinic(get_data("appointments"), active_clinic)
  if raw_appts.empty:
    st.info("No appointments in the queue yet.")
  else:
    f1, f2 = st.columns(2)
    with f1:
      view_date = st.date_input(
          "Filter by Date", datetime.date.today(), key="board_date"
      )
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
      appt_ids_list = filtered_appts[id_col].tolist()
      with u1:
        sel_appt_id = st.selectbox("Select Appointment ID", appt_ids_list)
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
          st.success(f"Updated `{sel_appt_id}` → **{next_status}**")
          st.rerun()
  st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# 2. CLINICAL ASSESSMENT (3D MODEL SWITCHER + ALL 10 REGIONS)
# =====================================================================
elif menu == "Clinical Assessment":
  pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
  name_col = col_val(patients_all, ["name", "Name"])

  if patients_all.empty or not pid_col:
    st.warning("Register a patient first under **Patient Registration**.")
  else:
    patient_ids, fmt_fn = format_patient_selector(
        patients_all, pid_col, name_col
    )
    selected_patient = st.selectbox(
        "Select Patient", patient_ids, format_func=fmt_fn
    )
    render_patient_banner(patients_all, selected_patient)

    if not assessments_all.empty:
      asm_pid_col = col_val(assessments_all, ["patient_id", "Patient_ID"])
      if asm_pid_col:
        p_asm = assessments_all[assessments_all[asm_pid_col] == selected_patient]
        if not p_asm.empty:
          with st.expander(
              f"📂 Past Assessments for {selected_patient} ({len(p_asm)})"
          ):
            st.dataframe(p_asm, width="stretch", hide_index=True)

    st.markdown(
        '<div class="ui-card"><div class="section-heading">1. 3D Anatomical'
        " Pain Map & Region Selection</div>",
        unsafe_allow_html=True,
    )
    col_map, col_reg = st.columns([1.12, 1.18])

    with col_map:
      render_true_3d_human_model(st.session_state["asm_body_parts"])

    with col_reg:
      body_parts = st.multiselect(
          "Affected Body Region(s)*:",
          BODY_REGIONS,
          key="asm_body_parts",
      )
      pain_spot_notes = st.text_input(
          "Pinned Pain Locations / Side & Tissue Note",
          placeholder=(
              "e.g., #1 Right Anterior Knee, #2 Left Lumbar Paraspinal"
          ),
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
      functional_goal = st.text_input(
          "Functional Goal / Outcome Note (e.g., NDI, ODI, KOOS, stairs)",
          key="asm_goal",
      )

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div class="ui-card"><div class="section-heading">2. Detailed'
        " Examination, Special Tests & MMT</div>",
        unsafe_allow_html=True,
    )

    assessment_details_dict = {}
    suggested_treatments = []
    bp_str = "".join(body_parts)

    if not body_parts:
      st.info(
          "Select one or more body regions above to open region-specific ROM,"
          " neurological, and special test fields."
      )

    if "Cervical" in bp_str:
      st.markdown("#### 🔹 Cervical Spine / Neck")
      c1, c2 = st.columns(2)
      with c1:
        c_rom = st.text_input(
            "Cervical ROM (Flexion 45°, Extension 45°, Lat Flexion 45°,"
            " Rotation 80°)",
            key="c_rom",
        )
      with c2:
        c_neuro = st.text_input(
            "Neurological Screen (C5–T1 Myotomes/Dermatomes/Reflexes)",
            key="c_neuro",
        )
      c_tests = st.multiselect(
          "Cervical Special Tests",
          [
              "Spurling’s Test",
              "Cervical Distraction Test",
              "Upper Limb Neurodynamic Tests (ULNT)",
              "Bakody Sign",
          ],
          key="c_tests",
      )
      assessment_details_dict["Cervical"] = {
          "ROM": c_rom,
          "Neurological": c_neuro,
          "Tests": c_tests,
      }
      suggested_treatments.append(
          "Cervical Traction + Deep Neck Flexor Endurance + Posture Correction"
      )

    if "Thoracic" in bp_str:
      st.markdown("#### 🔹 Thoracic Spine / Upper Back")
      t1, t2 = st.columns(2)
      with t1:
        t_rom = st.text_input(
            "Thoracic ROM (Flexion, Extension, Rotation, Side-Flexion)",
            key="t_rom",
        )
      with t2:
        t_palp = st.text_input(
            "Palpation / Costovertebral Mobility & Breathing", key="t_palp"
        )
      assessment_details_dict["Thoracic"] = {"ROM": t_rom, "Palpation": t_palp}
      suggested_treatments.append(
          "Thoracic Mobility + Scapular Stabilization + Breathing Re-education"
      )

    if "Lumbar" in bp_str:
      st.markdown("#### 🔹 Lumbar Spine / Low Back")
      l1, l2 = st.columns(2)
      with l1:
        l_rom = st.text_input(
            "Lumbar ROM (Flexion, Extension, Side-Glide, Rotation)", key="l_rom"
        )
      with l2:
        l_neuro = st.text_input(
            "Neurological Screen (L2–S1 Myotomes, Reflexes, Neural Tension)",
            key="l_neuro",
        )
      l_tests = st.multiselect(
          "Lumbar Special Tests",
          [
              "Straight Leg Raise (SLR)",
              "Crossed SLR",
              "Slump Test",
              "Femoral Nerve Stretch",
          ],
          key="l_tests",
      )
      assessment_details_dict["Lumbar"] = {
          "ROM": l_rom,
          "Neurological": l_neuro,
          "Tests": l_tests,
      }
      suggested_treatments.append(
          "Core Stabilization + Lumbar Traction + Centralization Mechanics"
      )

    if "Shoulder" in bp_str:
      st.markdown("#### 🔹 Shoulder Complex")
      sh_rom = st.text_input(
          "Shoulder ROM (Flexion 180°, Abduction 180°, ER/IR, Painful Arc)",
          key="sh_rom",
      )
      sh_tests = st.multiselect(
          "Shoulder Special Tests",
          [
              "Neer Test",
              "Hawkins-Kennedy Test",
              "Empty Can (Jobe)",
              "Speed's / Yergason's",
              "Apprehension / Relocation",
          ],
          key="sh_tests",
      )
      assessment_details_dict["Shoulder"] = {"ROM": sh_rom, "Tests": sh_tests}
      suggested_treatments.append(
          "Rotator Cuff Strengthening + Scapular Retraction + Ultrasound"
      )

    if "Elbow" in bp_str:
      st.markdown("#### 🔹 Elbow")
      el_rom = st.text_input(
          "Elbow Flexion/Extension & Pronation/Supination", key="el_rom"
      )
      el_tests = st.multiselect(
          "Elbow Special Tests",
          [
              "Cozen's / Maudsley's Test",
              "Resisted Wrist Flexion",
              "Valgus/Varus Stress Test",
          ],
          key="el_tests",
      )
      assessment_details_dict["Elbow"] = {"ROM": el_rom, "Tests": el_tests}
      suggested_treatments.append(
          "Eccentric Wrist Extension/Flexion + Soft Tissue Mobilization"
      )

    if "Wrist" in bp_str:
      st.markdown("#### 🔹 Wrist & Hand")
      w_rom = st.text_input(
          "Wrist Flexion/Extension, Radial/Ulnar Deviation, Pronation/Supination",
          key="w_rom",
      )
      w_tests = st.multiselect(
          "Wrist Special Tests",
          [
              "Phalen’s Test",
              "Tinel’s Sign",
              "Durkan's Test",
              "Finkelstein’s Test",
              "Scaphoid Shift Test",
          ],
          key="w_tests",
      )
      assessment_details_dict["Wrist"] = {"ROM": w_rom, "Tests": w_tests}
      suggested_treatments.append(
          "Carpal Tunnel Glides + Splinting Advice + Ergonomic Correction"
      )

    if "Hip" in bp_str:
      st.markdown("#### 🔹 Hip & Groin")
      h_rom = st.text_input(
          "Hip ROM (Flexion, Extension, Abduction/Adduction, ER/IR)", key="h_rom"
      )
      h_tests = st.multiselect(
          "Hip Special Tests",
          [
              "FADIR Test",
              "FABER (Patrick's) Test",
              "Scour Test",
              "Trendelenburg Test",
          ],
          key="h_tests",
      )
      assessment_details_dict["Hip"] = {"ROM": h_rom, "Tests": h_tests}
      suggested_treatments.append(
          "Hip Abductor Strengthening + Capsule Mobilization + Single-Leg Control"
      )

    if "Knee" in bp_str:
      st.markdown("#### 🔹 Knee Joint")
      k_rom = st.text_input(
          "Knee ROM (Flexion 140°, Extension 0°, Effusion/Sweep Test)",
          key="k_rom",
      )
      k_tests = st.multiselect(
          "Knee Special Tests",
          [
              "Lachman Test",
              "Anterior/Posterior Drawer",
              "McMurray Test",
              "Valgus/Varus Stress Test",
              "Patellar Apprehension",
          ],
          key="k_tests",
      )
      assessment_details_dict["Knee"] = {"ROM": k_rom, "Tests": k_tests}
      suggested_treatments.append(
          "Quadriceps VMO Strengthening + Patellar Mobilization + Squat"
          " Mechanics"
      )

    if "Ankle" in bp_str:
      st.markdown("#### 🔹 Ankle & Foot")
      a_rom = st.text_input(
          "Ankle Dorsiflexion/Plantarflexion, Weight-Bearing Lunge Test",
          key="a_rom",
      )
      a_tests = st.multiselect(
          "Ankle Special Tests",
          [
              "Anterior Drawer (ATFL)",
              "Squeeze Test (Syndesmosis)",
              "Thompson Test (Achilles)",
          ],
          key="a_tests",
      )
      assessment_details_dict["Ankle"] = {"ROM": a_rom, "Tests": a_tests}
      suggested_treatments.append(
          "Proprioceptive Balance Training + Calf Raises + Taping/Bracing"
      )

    if "TMJ" in bp_str:
      st.markdown("#### 🔹 TMJ / Jaw")
      j_rom = st.text_input(
          "Jaw Opening (mm), Lateral Excursion, Deviation/Deflection Path",
          key="j_rom",
      )
      j_tests = st.multiselect(
          "TMJ Screening",
          ["Joint Sounds / Clicking History", "Masticatory Muscle Palpation"],
          key="j_tests",
      )
      assessment_details_dict["TMJ"] = {"ROM": j_rom, "Tests": j_tests}
      suggested_treatments.append(
          "Cervicogenic Posture Correction + Jaw Relaxation Drills"
      )

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

    st.markdown(
        '<div class="ui-card"><div class="section-heading">3. Rehabilitation'
        " Plan & Sign-Off</div>",
        unsafe_allow_html=True,
    )

    if not suggested_treatments:
      suggested_treatments.append(
          "General Electrotherapy & Soft Tissue Mobilization"
      )

    with st.form("assessment_save_form"):
      default_plan = " | ".join(suggested_treatments)
      treatment_plan_input = st.text_area(
          "Final Treatment Plan & Suggested Modalities* (Editable)",
          value=default_plan,
          height=90,
      )

      s1, s2 = st.columns(2)
      with s1:
        suggested_time = st.number_input(
            "Suggested Total Sessions*", min_value=1, value=10
        )
      with s2:
        therapist = st.selectbox(
            "Assigned Therapist*",
            ["Dr. Geetanjali", "Dr. Rohan", "Dr. Senior Consultant"],
        )

      save_assessment = st.form_submit_button("Save Assessment & Protocol")
      if save_assessment:
        if not body_parts:
          st.error("Please select at least one Affected Body Region.")
        else:
          assessment_id = (
              f"ASM-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
          )
          spot_note = (
              f" | Pain Locations: {pain_spot_notes.strip()}"
              if pain_spot_notes.strip()
              else ""
          )

          assessment_dict = {
              "assessment_id": assessment_id,
              "patient_id": selected_patient,
              "clinic": (
                  CLINIC_BRANCHES[0]
                  if active_clinic == "All Clinics"
                  else active_clinic
              ),
              "body_parts": ", ".join(body_parts),
              "vas_score": int(nprs_activity),
              "assessment_details": (
                  f"NPRS[Rest:{nprs_rest}, Act:{nprs_activity},"
                  f" Night:{nprs_night}] | Irritability: {irritability} | Goal:"
                  f" {functional_goal}{spot_note} | MMT: {mmt_grade} | Details:"
                  f" {str(assessment_details_dict)}"
              ),
              "suggested_treatment": (
                  treatment_plan_input.strip() or default_plan
              ),
              "suggested_duration": f"{suggested_time} Sessions",
              "therapist": therapist,
              "date": str(datetime.date.today()),
          }
          save_data("assessments", assessment_dict)
          st.success(f"Assessment saved under ID `{assessment_id}`.")

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# 3. PATIENT REGISTRATION & DIRECTORY
# =====================================================================
elif menu == "Patient Registration":
  st.markdown(
      '<div class="ui-card"><div class="section-heading">New Patient'
      " Intake Form</div>",
      unsafe_allow_html=True,
  )

  with st.form("reg_form"):
    c1, c2 = st.columns(2)
    with c1:
      name = st.text_input("Patient Full Name*")
      email = st.text_input("Email Address")
      gender = st.selectbox("Gender", ["Female", "Male", "Other"])
      age_occ = st.text_input("Age / Occupation & Activity Demands")
    with c2:
      phone = st.text_input("Phone Number*")
      dominant_side = st.selectbox(
          "Dominant Side", ["Right", "Left", "Bilateral / Mixed"]
      )
      referral = st.text_input("Referral Source")
      med_history = st.text_area(
          "Medical History & Safety Flags (Diabetes, BP, Surgeries, Medications,"
          " Red Flags)"
      )

    reg_clinic = st.selectbox(
        "Home Clinic Branch*",
        CLINIC_BRANCHES,
        index=0
        if active_clinic == "All Clinics"
        else CLINIC_BRANCHES.index(active_clinic),
    )
    submitted = st.form_submit_button("Register & Generate Patient ID")

    if submitted and name and phone:
      all_p = get_data("patients")
      counter = len(all_p) + 1 if not all_p.empty else 1
      patient_id = f"PW{datetime.datetime.now().strftime('%m%y')}{counter:03d}"

      meta_notes = []
      if age_occ.strip():
        meta_notes.append(f"Profile: {age_occ.strip()}")
      if dominant_side:
        meta_notes.append(f"Dominant: {dominant_side}")
      if referral.strip():
        meta_notes.append(f"Ref: {referral.strip()}")

      combined_history = med_history.strip()
      if meta_notes:
        combined_history = (
            f"{combined_history} | {' ; '.join(meta_notes)}".strip(" |")
        )

      patient_dict = {
          "patient_id": patient_id,
          "name": name.strip(),
          "email": email.strip(),
          "gender": gender,
          "phone": phone.strip(),
          "clinic": reg_clinic,
          "medical_history": combined_history,
          "registration_date": str(datetime.date.today()),
      }

      save_data("patients", patient_dict)
      st.success(f"Patient registered! Generated ID: **{patient_id}**")
      st.rerun()
    elif submitted:
      st.error("Please enter both Patient Full Name and Phone Number.")

  st.markdown("</div>", unsafe_allow_html=True)

  patients_display = filter_by_clinic(get_data("patients"), active_clinic)
  if not patients_display.empty:
    st.markdown(
        '<div class="ui-card"><div class="section-heading">Patient'
        " Directory</div>",
        unsafe_allow_html=True,
    )
    search_q = st.text_input(
        "🔍 Filter directory by Name, Patient ID, or Phone",
        placeholder="Type to search...",
    )
    filtered_df = patients_display.copy()
    if search_q.strip():
      q = search_q.strip().lower()
      filtered_df = filtered_df[
          filtered_df.apply(
              lambda r: any(q in str(val).lower() for val in r.values), axis=1
          )
      ]
    st.caption(f"Showing {len(filtered_df)} of {len(patients_display)} records")
    st.dataframe(filtered_df, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# 4. DAILY TREATMENT LOG & REASSESSMENT
# =====================================================================
elif menu == "Daily Treatment Log":
  pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
  name_col = col_val(patients_all, ["name", "Name"])

  if patients_all.empty or not pid_col:
    st.warning("Register a patient first under **Patient Registration**.")
  else:
    patient_ids, fmt_fn = format_patient_selector(
        patients_all, pid_col, name_col
    )
    log_patient = st.selectbox(
        "Select Patient", patient_ids, format_func=fmt_fn, key="log_p"
    )
    render_patient_banner(patients_all, log_patient)

    completed_sessions = 0
    if not logs_all.empty:
      lp_col = col_val(logs_all, ["patient_id", "Patient_ID"])
      if lp_col:
        completed_sessions = len(logs_all[logs_all[lp_col] == log_patient])

    suggested_target = "Not set"
    if not assessments_all.empty:
      ap_col = col_val(assessments_all, ["patient_id", "Patient_ID"])
      dur_col = col_val(
          assessments_all, ["suggested_duration", "Suggested_Duration"]
      )
      if ap_col and dur_col:
        p_a = assessments_all[assessments_all[ap_col] == log_patient]
        if not p_a.empty:
          suggested_target = p_a.iloc[-1][dur_col]

    m1, m2 = st.columns(2)
    m1.metric("Sessions Logged", completed_sessions)
    m2.metric("Suggested Plan", suggested_target)

    with st.form("daily_log_form"):
      st.markdown("### Log Session & Quick Reassessment")
      c1, c2 = st.columns(2)
      with c1:
        log_date = st.date_input("Session Date*", datetime.date.today())
      with c2:
        current_vas = st.slider(
            "Current Session NPRS (0–10)*", 0, 10, 3, key="cur_v"
        )

      treatment_given = st.text_area(
          "Treatment Provided* (Electrotherapy, Manual Therapy, Exercise"
          " Sets/Reps)"
      )
      reassessment_note = st.text_input(
          "Reassessment / Key ROM or Strength Note (Optional)"
      )
      notes = st.text_area("Therapist Progress & Next-Session Notes")

      submit_log = st.form_submit_button("Save Daily Log")
      if submit_log:
        full_notes = notes.strip()
        if reassessment_note.strip():
          full_notes = (
              f"[Reassessment: {reassessment_note.strip()}] {full_notes}".strip()
          )

        log_dict = {
            "patient_id": log_patient,
            "clinic": (
                CLINIC_BRANCHES[0]
                if active_clinic == "All Clinics"
                else active_clinic
            ),
            "session_date": str(log_date),
            "treatment_given": treatment_given,
            "current_vas": int(current_vas),
            "notes": full_notes,
        }
        save_data("daily_logs", log_dict)
        st.success("Daily treatment log saved.")
        st.rerun()

    if not logs_all.empty:
      lp_col = col_val(logs_all, ["patient_id", "Patient_ID"])
      if lp_col:
        p_logs = logs_all[logs_all[lp_col] == log_patient]
        if not p_logs.empty:
          st.markdown(
              '<div class="ui-card"><div class="section-heading">Session'
              " History</div>",
              unsafe_allow_html=True,
          )
          st.dataframe(p_logs, width="stretch", hide_index=True)
          st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# 5. BILLING, PACKAGES & REMINDERS
# =====================================================================
elif menu == "Billing & Reminders":
  pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
  name_col = col_val(patients_all, ["name", "Name"])

  st.markdown(
      '<div class="ui-card"><div class="section-heading">Session Billing &'
      " Care Packages</div>",
      unsafe_allow_html=True,
  )
  if patients_all.empty or not pid_col:
    st.warning("Register a patient first under **Patient Registration**.")
  else:
    patient_ids, fmt_fn = format_patient_selector(
        patients_all, pid_col, name_col
    )
    with st.form("billing_entry_form"):
      c1, c2, c3 = st.columns(3)
      with c1:
        b_pid = st.selectbox(
            "Patient*", patient_ids, format_func=fmt_fn, key="b_pid"
        )
        b_pkg = st.selectbox(
            "Plan / Package*",
            [
                "Single Session",
                "5-Session Rehab Pack",
                "10-Session Recovery Pack",
                "Assessment + Initial Therapy",
            ],
        )
      with c2:
        b_amt = st.number_input("Amount (₹)*", min_value=0, value=800, step=100)
        b_mode = st.selectbox(
            "Payment Mode*", ["UPI", "Cash", "Card", "Pending"]
        )
      with c3:
        b_status = st.selectbox(
            "Payment Status*", ["Paid", "Partial", "Pending"]
        )
        b_followup = st.date_input(
            "Next Follow-Up Date",
            datetime.date.today() + datetime.timedelta(days=2),
        )

      save_bill = st.form_submit_button("Record Billing & Follow-Up")
      if save_bill:
        inv_id = f"INV-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        save_data(
            "billing",
            {
                "invoice_id": inv_id,
                "patient_id": b_pid,
                "clinic": (
                    CLINIC_BRANCHES[0]
                    if active_clinic == "All Clinics"
                    else active_clinic
                ),
                "package_name": b_pkg,
                "amount_inr": int(b_amt),
                "payment_mode": b_mode,
                "payment_status": b_status,
                "next_followup": str(b_followup),
                "date": str(datetime.date.today()),
            },
        )
        st.success(f"Saved billing entry `{inv_id}`.")
        st.rerun()
  st.markdown("</div>", unsafe_allow_html=True)

  st.markdown(
      '<div class="ui-card"><div class="section-heading">Billing Ledger &'
      " WhatsApp Reminder Link</div>",
      unsafe_allow_html=True,
  )
  if billing_all.empty:
    st.info("No billing records logged yet.")
  else:
    st.dataframe(billing_all, width="stretch", hide_index=True)
    latest_b = billing_all.iloc[-1].to_dict()
    b_patient_id = latest_b.get("patient_id", "Patient")
    b_fup = latest_b.get("next_followup", str(datetime.date.today()))
    msg = (
        f"Hello from Dr. Geetanjali's PhysioWorks ({active_clinic}): reminder"
        f" for patient {b_patient_id}'s upcoming session on {b_fup}."
    )
    wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
    st.markdown(f"[📲 Open WhatsApp Reminder Draft]({wa_url})")
  st.markdown("</div>", unsafe_allow_html=True)

# =====================================================================
# 6. PROGRESS DASHBOARD & CLINICAL SUMMARY
# =====================================================================
elif menu == "Progress & Summary":
  pid_col = col_val(patients_all, ["patient_id", "Patient_ID"])
  name_col = col_val(patients_all, ["name", "Name"])

  if patients_all.empty or not pid_col:
    st.warning("No patient records available.")
  else:
    patient_ids, fmt_fn = format_patient_selector(
        patients_all, pid_col, name_col
    )
    dash_patient = st.selectbox(
        "Select Patient", patient_ids, format_func=fmt_fn, key="dash_p"
    )
    render_patient_banner(patients_all, dash_patient)

    p_logs = pd.DataFrame()
    if not logs_all.empty:
      lp_col = col_val(logs_all, ["patient_id", "Patient_ID"])
      if lp_col:
        p_logs = logs_all[logs_all[lp_col] == dash_patient].copy()

    p_asm = pd.DataFrame()
    if not assessments_all.empty:
      ap_col = col_val(assessments_all, ["patient_id", "Patient_ID"])
      if ap_col:
        p_asm = assessments_all[assessments_all[ap_col] == dash_patient].copy()

    k1, k2, k3 = st.columns(3)
    k1.metric("Assessments", len(p_asm))
    k2.metric("Sessions Logged", len(p_logs))

    vas_col = col_val(p_logs, ["current_vas", "Current_VAS"])
    if not p_logs.empty and vas_col:
      p_logs[vas_col] = pd.to_numeric(p_logs[vas_col], errors="coerce")
      valid_vas = p_logs[vas_col].dropna()
      latest_vas = valid_vas.iloc[-1] if not valid_vas.empty else "N/A"
      first_vas = valid_vas.iloc[0] if not valid_vas.empty else "N/A"
      delta_txt = (
          f"{int(latest_vas - first_vas):+d} vs baseline"
          if isinstance(latest_vas, (int, float))
          and isinstance(first_vas, (int, float))
          else None
      )
      k3.metric("Latest NPRS", latest_vas, delta=delta_txt)
    else:
      k3.metric("Latest NPRS", "N/A")

    tab_chart, tab_records, tab_export = st.tabs(
        ["📈 Pain Trend", "🗂️ Records", "📄 Clinical Summary"]
    )

    with tab_chart:
      date_col = col_val(p_logs, ["session_date", "Session_Date"])
      if p_logs.empty or not date_col or not vas_col:
        st.info(
            "No session logs recorded yet for this patient to plot NPRS progress."
        )
      else:
        fig = px.line(
            p_logs,
            x=date_col,
            y=vas_col,
            markers=True,
            title=f"NPRS Pain Score Trend — {dash_patient}",
            labels={date_col: "Session Date", vas_col: "NPRS Score (0–10)"},
        )
        fig.update_traces(
            line_color="#1B365D", marker=dict(color="#F47920", size=9)
        )
        st.plotly_chart(fig, width="stretch")

    with tab_records:
      st.markdown("**Assessments**")
      if not p_asm.empty:
        st.dataframe(p_asm, width="stretch", hide_index=True)
      else:
        st.caption("No assessments recorded.")

      st.markdown("**Daily Treatment Logs**")
      if not p_logs.empty:
        st.dataframe(p_logs, width="stretch", hide_index=True)
      else:
        st.caption("No daily logs recorded.")

    with tab_export:
      p_row = (
          patients_all[patients_all[pid_col] == dash_patient].iloc[0].to_dict()
      )
      summary_lines = [
          "DR. GEETANJALI'S PHYSIO WORKS — CLINICAL SUMMARY",
          f"Generated On: {datetime.date.today()}",
          "-" * 50,
          f"Patient ID: {dash_patient}",
          f"Patient Profile: {p_row}",
          f"Sessions Completed: {len(p_logs)}",
          "",
          "ASSESSMENTS:",
      ]
      if not p_asm.empty:
        for _, r in p_asm.iterrows():
          summary_lines.append(str(dict(r)))
      else:
        summary_lines.append("No assessments recorded.")

      summary_lines.append("")
      summary_lines.append("DAILY TREATMENT LOGS:")
      if not p_logs.empty:
        for _, r in p_logs.iterrows():
          summary_lines.append(str(dict(r)))
      else:
        summary_lines.append("No daily logs recorded.")

      summary_text = "\n".join(str(x) for x in summary_lines)
      st.download_button(
          label="⬇️ Download Clinical Summary (.txt)",
          data=summary_text,
          file_name=(
              f"{dash_patient}_clinical_summary_{datetime.date.today()}.txt"
          ),
          mime="text/plain",
      )

      st.markdown("---")
      st.markdown("**Printable PDF Clinical Assessment Record**")
      latest_asm = p_asm.iloc[-1].to_dict() if not p_asm.empty else None

      col_pdf1, col_pdf2 = st.columns(2)
      with col_pdf1:
        filled_pdf_bytes = create_assessment_pdf(p_row, asm_row=latest_asm)
        st.download_button(
            label="📄 Download Patient Assessment PDF",
            data=filled_pdf_bytes,
            file_name=(
                f"{dash_patient}_assessment_record_{datetime.date.today()}.pdf"
            ),
            mime="application/pdf",
        )
      with col_pdf2:
        blank_pdf_bytes = create_assessment_pdf(p_row, asm_row=None)
        st.download_button(
            label="🖨️ Download Blank Printable Form (With Patient Header)",
            data=blank_pdf_bytes,
            file_name=f"{dash_patient}_blank_clinical_form.pdf",
            mime="application/pdf",
        )

# =====================================================================
# 7. STAFF & CLINIC MANAGEMENT (ADMIN ONLY)
# =====================================================================
elif menu == "Staff & Clinic Management":
  st.markdown(
      '<div class="ui-card"><div class="section-heading">Add Staff User &'
      " Role Permissions</div>",
      unsafe_allow_html=True,
  )
  with st.form("add_staff_form"):
    c1, c2, c3 = st.columns(3)
    with c1:
      s_name = st.text_input("Full Name*")
      s_email = st.text_input("Staff Email / Login ID*")
    with c2:
      s_role = st.selectbox("Assigned Role*", ROLE_OPTIONS)
      s_clinic = st.selectbox(
          "Default Clinic Branch*", CLINIC_BRANCHES + ["All Clinics"]
      )
    with c3:
      s_pass = st.text_input("Initial Password / PIN*", type="password")
      s_active = st.checkbox("Account Active", value=True)

    add_staff_btn = st.form_submit_button("Create Staff Account")
    if add_staff_btn:
      if s_name and s_email and s_pass:
        staff_df_cur = get_staff_directory()
        new_sid = f"STF-{len(staff_df_cur) + 1:03d}"
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
        st.success(f"Staff user `{s_name}` ({s_role}) created.")
        st.rerun()
      else:
        st.error("Please fill in Full Name, Email/ID, and Initial Password.")
  st.markdown("</div>", unsafe_allow_html=True)

  st.markdown(
      '<div class="ui-card"><div class="section-heading">Active Clinic'
      " Staff Directory</div>",
      unsafe_allow_html=True,
  )
  s_display = get_staff_directory().copy()
  if "password_hash" in s_display.columns:
    s_display = s_display.drop(columns=["password_hash"])
  st.dataframe(s_display, width="stretch", hide_index=True)
  st.markdown("</div>", unsafe_allow_html=True)
