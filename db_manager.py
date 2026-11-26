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
EMBEDDED_SUPABASE_KEY = "sb_publishable_9EmHVLBa0f9wSDv69MD2Mw_aruWo_fh"

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

