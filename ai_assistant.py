import json
import os
import requests
import streamlit as st

try:
  from google import genai
except Exception:
  genai = None

EMBEDDED_GEMINI_API_KEY = ""


def get_gemini_api_key() -> str:
  try:
    s_val = st.secrets.get("AQ.Ab8RN6JfoJBPrMm5AvpjzN0EcLDn1lcK0NBguCH3xmfM-lCF_A")
    if s_val and str(s_val).strip():
      return str(s_val).strip()
  except Exception:
    pass
  e_val = os.environ.get("AQ.Ab8RN6JfoJBPrMm5AvpjzN0EcLDn1lcK0NBguCH3xmfM-lCF_A")
  if e_val and e_val.strip():
    return e_val.strip()
  if EMBEDDED_GEMINI_API_KEY and EMBEDDED_GEMINI_API_KEY.strip():
    return EMBEDDED_GEMINI_API_KEY.strip()
  return ""


def generate_clinical_insights(
    context_payload: dict, detailed_plan: bool = False
) -> str:
  api_key = get_gemini_api_key()
  mode_instruction = (
      "Provide a detailed rehabilitation protocol with modalities, exercise"
      " dosage (sets/reps), progression criteria, and home program."
      if detailed_plan
      else (
          "Provide concise clinical insights with likely tissue/movement"
          " pattern, safety notes, and focus."
      )
  )
  prompt = (
      "You are a clinical physiotherapy decision-support assistant for Dr."
      " Geetanjali's PhysioWorks.\n"
      "Frame findings as clinical support (not a standalone medical"
      " diagnosis).\n"
      f"{mode_instruction}\n\n"
      f"Assessment Context:\n{json.dumps(context_payload, indent=2)}"
  )
  models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
  errors = []

  if api_key:
    if genai is not None:
      try:
        client = genai.Client(api_key=api_key)
        for m in models:
          try:
            resp = client.models.generate_content(model=m, contents=prompt)
            txt = getattr(resp, "text", None)
            if txt and txt.strip():
              return txt.strip()
          except Exception as ex:
            errors.append(f"SDK[{m}]: {ex}")
      except Exception as ex:
        errors.append(f"SDK init: {ex}")

    for m in models:
      url = (
          "https://generativelanguage.googleapis.com/v1beta/models/"
          f"{m}:generateContent"
      )
      try:
        r = requests.post(
            url,
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if r.status_code == 200:
          data = r.json()
          cands = data.get("candidates") or []
          if cands:
            parts = (cands[0].get("content") or {}).get("parts") or []
            joined = "".join(p.get("text", "") for p in parts if p.get("text"))
            if joined.strip():
              return joined.strip()
        else:
          errors.append(f"REST[{m}] HTTP {r.status_code}")
      except Exception as ex:
        errors.append(f"REST[{m}]: {ex}")

  regions = ", ".join(
      context_payload.get("affected_regions") or ["General Musculoskeletal"]
  )
  nprs_act = context_payload.get("nprs_activity", "N/A")
  irr = context_payload.get("irritability", "Moderate")
  flags = context_payload.get("medical_history", "None noted")
  err_summary = (
      "; ".join(errors[-2:]) if errors else "No GEMINI_API_KEY configured"
  )
  status_note = f"*(Structured Clinical Fallback — {err_summary})*"

  if not detailed_plan:
    return (
        f"{status_note}\n\n"
        f"- **Primary Regions:** {regions}\n"
        f"- **Activity NPRS & Irritability:** {nprs_act}/10 | {irr}\n"
        f"- **Precautions:** {flags}\n"
        "- **Focus:** Pain modulation, graded mobility, and neuromuscular"
        " control."
    )

  return (
      f"{status_note}\n\n"
      f"### Detailed Rehabilitation Protocol ({regions})\n"
      f"1. **Safety & Irritability:** Respect **{irr}** and history"
      " (**{flags}**); keep pain <= 3/10 during drills.\n"
      "2. **Phase 1 (Sessions 1-4):** Modalities + gentle mobility/soft-tissue"
      " work (2 sets x 8-10 reps).\n"
      "3. **Phase 2 (Sessions 5-10):** Progressive isometric/isotonic strength"
      " & motor control (3 sets x 10-12 reps).\n"
      "4. **Reassessment:** Track NPRS, ROM, MMT grade, and functional"
      " milestones at follow-up."
  )
