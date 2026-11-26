import hashlib
import pandas as pd
import streamlit as st
from supabase import create_client

# ==============================================================================
# DATABASE & AUTHENTICATION LAYER (SUPABASE + SESSION MEMORY FALLBACK)
# ==============================================================================
supabase = None
db_connected = False

# New physiowork Supabase credentials (st.secrets checked first if configured)
EMBEDDED_SUPABASE_URL = "https://cavsikyqrvguuocegsmv.supabase.co"
EMBEDDED_SUPABASE_KEY = "sb_publishable_9EmHVLBa0f9wSDv_PASTE_YOUR_FULL_KEY_HERE"

try:
    SUPABASE_URL = (st.secrets.get("SUPABASE_URL") or EMBEDDED_SUPABASE_URL).strip()
    SUPABASE_KEY = (st.secrets.get("SUPABASE_KEY") or EMBEDDED_SUPABASE_KEY).strip()
except Exception:
    SUPABASE_URL = EMBEDDED_SUPABASE_URL.strip()
    SUPABASE_KEY = EMBEDDED_SUPABASE_KEY.strip()

try:
    if SUPABASE_URL and SUPABASE_KEY and "PASTE_YOUR_FULL_KEY" not in SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        db_connected = True
except Exception:
    supabase = None
    db_connected = False


def hash_password(raw_pw: str) -> str:
    return hashlib.sha256(str(raw_pw).strip().encode("utf-8")).hexdigest()


DEFAULT_CLINIC_SETTINGS = {
    "clinic_title": "Dr. Geetanjali’s PhysioWorks",
    "clinic_tagline": "Physiotherapy • Osteopathy • Chiropractic — A-3 & A-4 Paschim Vihar Clinical Suite",
    "clinic_badge": "GET THE CARE YOU DESERVE",
    "branches": "A-3 Paschim Vihar, A-4 Paschim Vihar",
    "therapists": "Dr. Geetanjali, Dr. Rohan, Dr. Senior Consultant",
    "default_sessions": 10,
    "default_fee_inr": 800,
    "logo_path": "image_500b64.jpg",
}

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


def get_data(table_name: str) -> pd.DataFrame:
    client = globals().get("supabase")
    if client is not None:
        try:
            response = client.table(table_name).select("*").execute()
            if response.data is not None:
                return pd.DataFrame(response.data)
        except Exception:
            pass
    if table_name not in st.session_state:
        st.session_state[table_name] = pd.DataFrame()
    return st.session_state[table_name]


def save_data(table_name: str, row_dict: dict) -> bool:
    client = globals().get("supabase")
    saved_cloud = False
    if client is not None:
        try:
            client.table(table_name).insert(row_dict).execute()
            saved_cloud = True
        except Exception as e:
            st.warning(f"Cloud sync fallback ({table_name}): {e}")
    if table_name not in st.session_state:
        st.session_state[table_name] = pd.DataFrame()
    new_df = pd.DataFrame([row_dict])
    st.session_state[table_name] = pd.concat([st.session_state[table_name], new_df], ignore_index=True)
    return saved_cloud


def get_clinic_settings() -> dict:
    if "clinic_settings_cache" not in st.session_state:
        st.session_state["clinic_settings_cache"] = DEFAULT_CLINIC_SETTINGS.copy()
        df = get_data("clinic_settings")
        if not df.empty:
            latest = df.iloc[-1].to_dict()
            for k in DEFAULT_CLINIC_SETTINGS:
                if k in latest and latest[k] not in (None, ""):
                    st.session_state["clinic_settings_cache"][k] = latest[k]
    return st.session_state["clinic_settings_cache"]


def save_clinic_settings(updated_dict: dict):
    st.session_state["clinic_settings_cache"] = updated_dict.copy()
    save_data("clinic_settings", updated_dict)


def get_branches_list() -> list:
    cfg = get_clinic_settings()
    raw = str(cfg.get("branches", "A-3 Paschim Vihar, A-4 Paschim Vihar"))
    items = [b.strip() for b in raw.split(",") if b.strip()]
    return items or ["A-3 Paschim Vihar", "A-4 Paschim Vihar"]


def get_therapists_list() -> list:
    cfg = get_clinic_settings()
    raw = str(cfg.get("therapists", "Dr. Geetanjali, Dr. Rohan, Dr. Senior Consultant"))
    items = [t.strip() for t in raw.split(",") if t.strip()]
    return items or ["Dr. Geetanjali", "Dr. Rohan"]


def get_staff_directory() -> pd.DataFrame:
    df = get_data("staff_users")
    if df.empty:
        return pd.DataFrame(DEFAULT_STAFF_ACCOUNTS)
    return df


def authenticate_staff(login_id: str, raw_password: str):
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


def update_appointment_status(appt_id: str, new_status: str):
    client = globals().get("supabase")
    if client is not None:
        try:
            client.table("appointments").update({"status": new_status}).eq("appointment_id", appt_id).execute()
        except Exception:
            pass
    if "appointments" in st.session_state and not st.session_state["appointments"].empty:
        df = st.session_state["appointments"].copy()
        if "appointment_id" in df.columns and "status" in df.columns:
            df.loc[df["appointment_id"] == appt_id, "status"] = new_status
            st.session_state["appointments"] = df


def filter_by_clinic(df: pd.DataFrame, selected_clinic: str) -> pd.DataFrame:
    if df.empty or selected_clinic == "All Clinics":
        return df
    for c in ("clinic", "Clinic", "clinic_id"):
        if c in df.columns:
            return df[df[c] == selected_clinic]
    return df


def col_val(df: pd.DataFrame, col_options: list, default: str = "") -> str:
    for c in col_options:
        if c in df.columns:
            return c
    return default

FILE: anatomy_3d.py
import json
import streamlit.components.v1 as components


def render_ecorche_3d_viewer(selected_regions: list):
    """
    3D Musculoskeletal Ecorche & Shoulder/Joint Anatomy Viewer (Three.js WebGL):
    - Multi-colored anatomical muscle groups (pectoralis, deltoid, biceps/triceps, abdominals, quads, gastrocnemius)
    - Translucent skin envelope toggle + Deep Shoulder/Clavicle/Ribs/Tendon cutaway mode
    - 360-degree drag rotation, zoom, Anterior/Posterior/Left/Right presets, and numbered red pain-spot pins
    """
    active_json = json.dumps(selected_regions)
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{
          margin: 0; background: #1E222B;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: #F8FAFC;
        }}
        #wrap {{
          position: relative; width: 100%; height: 530px;
          border-radius: 12px; overflow: hidden; border: 1px solid #334155;
          background: radial-gradient(circle at 50% 42%, #3A3F4B 0%, #1F232C 100%);
        }}
        .top-hud {{
          position: absolute; top: 10px; left: 10px; right: 10px;
          display: flex; justify-content: space-between; align-items: center;
          gap: 6px; z-index: 20; flex-wrap: wrap;
        }}
        .btn-row {{ display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }}
        .vbtn {{
          background: rgba(27, 54, 93, 0.94); color: #F8FAFC;
          border: 1px solid #475569; padding: 5px 9px; border-radius: 6px;
          font-size: 11px; font-weight: 600; cursor: pointer;
        }}
        .vbtn:hover {{ background: #F47920; border-color: #F47920; }}
        .vbtn.active {{ background: #F47920; border-color: #FDBA74; }}
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
            <button id="mode-full" class="vbtn active" onclick="setMode('full')">Full Muscle Body</button>
            <button id="mode-shoulder" class="vbtn" onclick="setMode('shoulder')">Shoulder Deep Anatomy</button>
            <button id="btn-skin" class="vbtn" onclick="toggleSkin()">Skin Shell: ON</button>
            <button class="vbtn" onclick="setAngle(0)">Front</button>
            <button class="vbtn" onclick="setAngle(Math.PI)">Back</button>
            <button class="vbtn" onclick="setAngle(Math.PI/2)">Left</button>
            <button class="vbtn" onclick="setAngle(-Math.PI/2)">Right</button>
            <button class="vbtn clear" onclick="clearPins()">Clear Pins</button>
          </div>
          <span id="badge">3D Musculoskeletal Ecorche • Click muscle to mark pain</span>
        </div>
        <div class="bottom-hud">
          <span>360° Drag to Rotate • Scroll to Zoom • Click any muscle/tendon/joint to drop numbered pin</span>
          <span id="pin-readout">Pain pins: 0</span>
        </div>
      </div>

      <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
      <script>
        const activeRegions = new Set({active_json});
        const container = document.getElementById('wrap');
        const badgeEl = document.getElementById('badge');
        const pinReadoutEl = document.getElementById('pin-readout');

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(36, container.clientWidth / container.clientHeight, 0.05, 100);
        camera.position.set(0, 0.96, 3.25);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.outputEncoding = THREE.sRGBEncoding;
        container.appendChild(renderer.domElement);

        scene.add(new THREE.AmbientLight(0xF8FAFC, 0.65));
        const keyLight = new THREE.DirectionalLight(0xFFF7ED, 0.95);
        keyLight.position.set(2.5, 4.2, 3.5);
        scene.add(keyLight);
        const rimLight = new THREE.DirectionalLight(0xBAE6FD, 0.55);
        rimLight.position.set(-2.5, 2.5, -3.5);
        scene.add(rimLight);
        const fillLight = new THREE.DirectionalLight(0xE2E8F0, 0.4);
        fillLight.position.set(0, -1.8, 2.5);
        scene.add(fillLight);

        const gridHelper = new THREE.PolarGridHelper(0.62, 16, 4, 48, 0x64748B, 0x334155);
        scene.add(gridHelper);

        const rootGroup = new THREE.Group();
        scene.add(rootGroup);

        const fullBodyGroup = new THREE.Group();
        rootGroup.add(fullBodyGroup);

        const shoulderDetailGroup = new THREE.Group();
        shoulderDetailGroup.visible = false;
        rootGroup.add(shoulderDetailGroup);

        const skinShellGroup = new THREE.Group();
        fullBodyGroup.add(skinShellGroup);

        const painPinsGroup = new THREE.Group();
        rootGroup.add(painPinsGroup);

        const clickableFull = [];
        const clickableShoulder = [];
        const markedPins = [];
        let currentMode = 'full';
        let skinVisible = true;

        function mat(hex, rough=0.45, metal=0.05, opacity=1.0) {{
          return new THREE.MeshStandardMaterial({{
            color: hex,
            roughness: rough,
            metalness: metal,
            transparent: opacity < 1.0,
            opacity: opacity
          }});
        }}

        // Muscle-group palette matching anatomical ecorche diagram
        const mPec = mat(0xD9777F, 0.42);       // Pectoralis / Upper Torso (Rose Coral)
        const mDeltoid = mat(0xC96A52, 0.40);   // Deltoid / Shoulder (Terracotta Muscle)
        const mAbs = mat(0xC85A68, 0.44);       // Rectus Abdominis (Deep Rose)
        const mOblique = mat(0x7C73A8, 0.45);   // External Oblique / Serratus (Muted Violet)
        const mBicep = mat(0xB86B84, 0.42);     // Biceps / Arm Flexors (Plum Rose)
        const mForearm = mat(0x6BA38B, 0.44);   // Forearm Extensors/Flexors (Sage Green)
        const mQuad = mat(0x88B06A, 0.42);      // Quadriceps / Sartorius (Olive Green)
        const mAdductor = mat(0x6E8FB8, 0.44);  // Adductors / Hip (Slate Blue)
        const mGlute = mat(0xD47A6A, 0.42);     // Gluteus Maximus (Warm Coral)
        const mCalf = mat(0x9E7BB5, 0.44);      // Gastrocnemius / Tibialis (Lavender)
        const mHead = mat(0xC9A86A, 0.46);      // Cranial / Facial Muscles (Ochre)
        const mTendon = mat(0xF1EDE1, 0.32);    // Tendons & Aponeurosis (Ivory White)
        const mBone = mat(0xD6CBB5, 0.50);      // Clavicle, Ribs, Humerus (Bone)
        const mSkin = mat(0xF5E6DC, 0.25, 0.0, 0.20); // Translucent outer skin envelope

        function addMuscle(group, clickList, geo, material, x, y, z, rx=0, ry=0, rz=0, sx=1, sy=1, sz=1, regionLabel="", muscleName="") {{
          const mesh = new THREE.Mesh(geo, material);
          mesh.position.set(x, y, z);
          mesh.rotation.set(rx, ry, rz);
          mesh.scale.set(sx, sy, sz);
          mesh.userData = {{ region: regionLabel, muscle: muscleName }};
          group.add(mesh);
          if (clickList) clickList.push(mesh);
          return mesh;
        }}

        // -----------------------------------------------------------------
        // 1. FULL-BODY COLOR-CODED MUSCULOSKELETAL ECORCHE
        // -----------------------------------------------------------------
        // Cranium & TMJ/Jaw
        addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.105, 24, 20), mHead, 0, 1.66, 0, 0,0,0, 0.90, 1.12, 1.0, "TMJ / Jaw", "Temporalis / Cranium");
        addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.078, 20, 16), mPec, 0, 1.56, 0.03, 0,0,0, 0.85, 0.82, 0.88, "TMJ / Jaw", "Masseter / Jaw");

        // Cervical Neck (Sternocleidomastoid & Trapezius)
        addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.048, 0.056, 0.14, 20), mAdductor, 0, 1.46, -0.01, 0,0,0, 1,1,1, "Cervical Spine (Neck)", "Cervical / SCM");

        // Pectoralis Major & Upper Back Trapezius/Latissimus
        [-1, 1].forEach(s => {{
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.082, 20, 16), mPec, s*0.078, 1.33, 0.055, 0,0,-s*0.18, 1.15, 0.82, 0.58, "Thoracic Spine (Upper Back)", "Pectoralis Major");
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.088, 20, 16), mPec, s*0.082, 1.31, -0.058, 0,0,s*0.22, 1.15, 1.05, 0.55, "Thoracic Spine (Upper Back)", "Trapezius / Rhomboids");
        }});

        // Rectus Abdominis (6-pack segments) & Linea Alba Tendon
        addMuscle(fullBodyGroup, clickableFull, new THREE.BoxGeometry(0.012, 0.28, 0.03), mTendon, 0, 1.11, 0.082, 0,0,0, 1,1,1, "Lumbar Spine (Lower Back)", "Linea Alba");
        [-1, 1].forEach(s => {{
          [1.20, 1.12, 1.04, 0.96].forEach((yy, idx) => {{
            addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.038, 16, 14), mAbs, s*0.042, yy, 0.075, 0,0,0, 1.05, 0.88, 0.55, "Lumbar Spine (Lower Back)", "Rectus Abdominis");
          }});
          // External Obliques
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.052, 0.058, 0.24, 18), mOblique, s*0.115, 1.10, 0.01, 0,0,-s*0.06, 0.72, 1.0, 1.15, "Lumbar Spine (Lower Back)", "External Oblique");
          // Lumbar Erector Spinae
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.055, 0.065, 0.24, 18), mAdductor, s*0.065, 1.08, -0.055, 0,0,0, 1.0, 1.0, 0.75, "Lumbar Spine (Lower Back)", "Erector Spinae");
          // Gluteus Maximus
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.088, 20, 18), mGlute, s*0.078, 0.88, -0.055, 0,0,0, 1.02, 1.05, 0.82, "Hip & Groin", "Gluteus Maximus");
          // Hip Flexor / Iliopsoas / TFL
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.068, 18, 16), mAdductor, s*0.095, 0.89, 0.042, 0,0,0, 0.95, 1.05, 0.75, "Hip & Groin", "Iliopsoas / TFL");
        }});

        // Shoulders, Arms, Elbows, Forearms, Wrists
        [-1, 1].forEach(s => {{
          // Deltoid cap
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.066, 20, 18), mDeltoid, s*0.195, 1.35, 0.0, 0,0,-s*0.25, 0.95, 1.25, 0.95, "Shoulder Complex", "Deltoid");
          // Biceps & Triceps
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.042, 0.036, 0.22, 18), mBicep, s*0.235, 1.18, 0.012, 0,0,s*0.18, 1,1,1, "Shoulder Complex", "Biceps / Triceps");
          // Elbow joint tendon
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.036, 16, 14), mTendon, s*0.265, 1.06, 0.0, 0,0,0, 1,1,1, "Elbow", "Elbow / Olecranon");
          // Forearm
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.036, 0.025, 0.22, 18), mForearm, s*0.295, 0.94, 0.015, 0,0,s*0.14, 1,1,1, "Elbow", "Brachioradialis / Forearm");
          // Wrist & Hand
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.032, 16, 14), mTendon, s*0.325, 0.80, 0.025, 0,0,s*0.12, 0.65, 1.55, 0.95, "Wrist & Hand", "Wrist & Hand");
        }});

        // Thighs (Quads / Hamstrings), Knees, Calves, Ankles & Feet
        [-1, 1].forEach(s => {{
          // Quadriceps (Vastus Lateralis / Rectus Femoris)
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.072, 0.052, 0.34, 20), mQuad, s*0.095, 0.66, 0.018, 0,0,-s*0.03, 0.95, 1.0, 1.05, "Hip & Groin", "Quadriceps Femoris");
          // Medial Adductor / Gracilis
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.048, 0.036, 0.32, 16), mAdductor, s*0.058, 0.67, 0.0, 0,0,-s*0.05, 0.85, 1.0, 0.95, "Hip & Groin", "Adductor Group");
          // Posterior Hamstrings
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.064, 0.048, 0.33, 18), mBicep, s*0.092, 0.66, -0.025, 0,0,-s*0.03, 0.95, 1.0, 0.95, "Hip & Groin", "Hamstrings");
          // Patella & Knee Tendon
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.046, 18, 16), mTendon, s*0.095, 0.47, 0.015, 0,0,0, 0.95, 1.05, 1.0, "Knee Joint", "Patella & Knee Capsule");
          // Gastrocnemius / Tibialis Anterior
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.050, 0.032, 0.34, 20), mCalf, s*0.095, 0.27, -0.008, 0,0,0, 0.95, 1.0, 1.05, "Knee Joint", "Gastrocnemius / Tibialis");
          // Achilles Tendon
          addMuscle(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.016, 0.020, 0.14, 12), mTendon, s*0.095, 0.14, -0.028, 0,0,0, 1,1,1, "Ankle & Foot", "Achilles Tendon");
          // Ankle & Foot
          addMuscle(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.038, 16, 14), mTendon, s*0.095, 0.04, 0.038, 0,0,0, 0.88, 0.55, 1.85, "Ankle & Foot", "Ankle & Foot");
        }});

        // Translucent outer skin envelope (as shown in reference diagram)
        const torsoSkin = new THREE.Mesh(new THREE.CylinderGeometry(0.165, 0.145, 0.62, 24), mSkin);
        torsoSkin.position.set(0, 1.12, 0);
        torsoSkin.scale.set(1.08, 1.0, 0.68);
        skinShellGroup.add(torsoSkin);

        // -----------------------------------------------------------------
        // 2. DEEP SHOULDER ANATOMY CUTAWAY (CLAVICLE, RIBS, DELTOID, PEC MINOR, BICEPS TENDON)
        // -----------------------------------------------------------------
        // Clavicle & Acromion (Bone)
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.024, 0.028, 0.56, 18), mBone, 0.08, 1.42, 0.04, 0, 0, Math.PI/2 - 0.08, 1,1,1, "Shoulder Complex", "Clavicle & AC Joint");
        // Rib Cage Arcs
        [1.26, 1.14, 1.02, 0.90, 0.78].forEach((ry, i) => {{
          const rib = new THREE.TorusGeometry(0.24 - i*0.01, 0.016, 12, 28, Math.PI * 0.85);
          addMuscle(shoulderDetailGroup, clickableShoulder, rib, mBone, 0.24, ry, -0.02, Math.PI/2, 0.2, -0.4, 1,1,1, "Thoracic Spine (Upper Back)", `Rib #${{i+2}}`);
        }});
        // Humerus Shaft
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.036, 0.032, 0.68, 18), mBone, -0.14, 1.04, 0.0, 0, 0, 0.05, 1,1,1, "Shoulder Complex", "Humerus Shaft");
        // Deltoid Muscle Fibers (Anterior & Lateral Heads)
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.SphereGeometry(0.135, 24, 20), mDeltoid, -0.17, 1.26, 0.03, 0.1, 0.2, -0.22, 0.85, 1.55, 0.78, "Shoulder Complex", "Anterior/Lateral Deltoid");
        // Pectoralis Minor (Fanning to ribs 3-5)
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.BoxGeometry(0.16, 0.34, 0.035), mDeltoid, 0.06, 1.18, 0.11, -0.15, 0.2, 0.42, 1,1,1, "Shoulder Complex", "Pectoralis Minor");
        // Biceps Long & Short Head Tendons (Ivory White) + Muscle Bellies
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.018, 0.026, 0.32, 16), mTendon, -0.11, 1.16, 0.08, 0.08, 0, -0.14, 1,1,1, "Shoulder Complex", "Biceps Long Head Tendon");
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.034, 0.042, 0.38, 18), mDeltoid, -0.13, 0.84, 0.08, 0, 0, 0.04, 1,1,1, "Shoulder Complex", "Biceps Brachii Belly");
        addMuscle(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.034, 0.040, 0.38, 18), mPec, -0.21, 0.84, 0.02, 0, 0, 0.06, 1,1,1, "Elbow", "Brachialis / Lateral Head");
        // Outer translucent skin contour around shoulder
        addMuscle(shoulderDetailGroup, null, new THREE.CylinderGeometry(0.24, 0.22, 0.85, 24), mSkin, -0.05, 1.08, 0.0, 0,0,0, 1.15, 1.0, 0.85, "", "");

        window.setMode = function(mode) {{
          currentMode = mode;
          fullBodyGroup.visible = (mode === 'full');
          shoulderDetailGroup.visible = (mode === 'shoulder');
          document.getElementById('mode-full').classList.toggle('active', mode === 'full');
          document.getElementById('mode-shoulder').classList.toggle('active', mode === 'shoulder');
          badgeEl.textContent = mode === 'full'
            ? "3D Musculoskeletal Ecorche • Click muscle to mark pain"
            : "Shoulder Deep Anatomy (Deltoid/Pec Minor/Biceps Tendon)";
        }};

        window.toggleSkin = function() {{
          skinVisible = !skinVisible;
          skinShellGroup.visible = skinVisible;
          document.getElementById('btn-skin').textContent = skinVisible ? "Skin Shell: ON" : "Skin Shell: OFF";
        }};

        function dropPainPin(localPt, hitMesh) {{
          const num = markedPins.length + 1;
          const pinCore = new THREE.Mesh(
            new THREE.SphereGeometry(0.022, 16, 16),
            new THREE.MeshStandardMaterial({{ color: 0xEF4444, emissive: 0xB91C1C, roughness: 0.2 }})
          );
          pinCore.position.copy(localPt);

          const pinRing = new THREE.Mesh(
            new THREE.SphereGeometry(0.042, 16, 16),
            new THREE.MeshBasicMaterial({{ color: 0xF47920, transparent: true, opacity: 0.48 }})
          );
          pinRing.position.copy(localPt);

          painPinsGroup.add(pinCore);
          painPinsGroup.add(pinRing);

          const ud = hitMesh.userData || {{}};
          const lr = localPt.x < -0.03 ? "Left " : (localPt.x > 0.03 ? "Right " : "");
          const structure = ud.muscle || ud.region || "Anatomical Point";
          const desc = `#${{num}} ${{lr}}${{structure}}`;
          markedPins.push(desc);
          badgeEl.textContent = "Pinned: " + desc;
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
          camera.position.z = Math.max(1.65, Math.min(4.6, camera.position.z + e.deltaY * 0.002));
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
          const targets = currentMode === 'full' ? clickableFull : clickableShoulder;
          const hits = raycaster.intersectObjects(targets, true);
          if (hits.length > 0) {{
            const localPt = rootGroup.worldToLocal(hits[0].point.clone());
            dropPainPin(localPt, hits[0].object);
          }}
        }});

        function animate() {{
          requestAnimationFrame(animate);
          renderer.render(scene, camera);
        }}
        animate();
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=544)

