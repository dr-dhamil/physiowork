import json
import streamlit.components.v1 as components


def render_ecorche_3d_viewer(selected_regions: list):
  active_json = json.dumps(selected_regions or [])
  html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{
          margin: 0; background: #141B29;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          color: #F8FAFC;
        }}
        #wrap {{
          position: relative; width: 100%; height: 520px;
          border-radius: 12px; overflow: hidden; border: 1px solid #CBD5E1;
          background: radial-gradient(circle at 50% 40%, #2B364B 0%, #111827 100%);
        }}
        .top-hud {{
          position: absolute; top: 10px; left: 10px; right: 10px;
          display: flex; justify-content: space-between; align-items: center;
          gap: 6px; z-index: 20; flex-wrap: wrap;
        }}
        .btn-row {{ display: flex; gap: 5px; flex-wrap: wrap; align-items: center; }}
        .vbtn {{
          background: rgba(27, 54, 93, 0.95); color: #F8FAFC;
          border: 1px solid #64748B; padding: 5px 9px; border-radius: 6px;
          font-size: 11px; font-weight: 600; cursor: pointer;
        }}
        .vbtn:hover {{ background: #F47920; border-color: #F47920; }}
        .vbtn.active {{ background: #F47920; border-color: #FDBA74; }}
        .vbtn.clear {{ background: rgba(153, 27, 27, 0.92); border-color: #DC2626; }}
        #badge {{
          background: #F47920; color: #FFFFFF;
          padding: 5px 11px; border-radius: 999px; font-size: 11px; font-weight: 700;
        }}
        .bottom-hud {{
          position: absolute; bottom: 10px; left: 10px; right: 10px;
          background: rgba(15, 23, 42, 0.9); border: 1px solid #334155;
          border-radius: 8px; padding: 7px 12px; font-size: 11px; color: #E2E8F0;
          display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap;
        }}
        #pin-readout {{ color: #FDBA74; font-weight: 600; }}
      </style>
    </head>
    <body>
      <div id="wrap">
        <div class="top-hud">
          <div class="btn-row">
            <button id="mode-full" class="vbtn active" onclick="setMode('full')">Full Ecorche</button>
            <button id="mode-shoulder" class="vbtn" onclick="setMode('shoulder')">Shoulder Cutaway</button>
            <button id="btn-skin" class="vbtn" onclick="toggleSkin()">Skin Shell: ON</button>
            <button class="vbtn" onclick="setAngle(0)">Front</button>
            <button class="vbtn" onclick="setAngle(Math.PI)">Back</button>
            <button class="vbtn" onclick="setAngle(Math.PI/2)">Left</button>
            <button class="vbtn" onclick="setAngle(-Math.PI/2)">Right</button>
            <button class="vbtn clear" onclick="clearPins()">Clear Pins</button>
          </div>
          <span id="badge">3D Ecorche Ready • Click muscle to pin pain</span>
        </div>
        <div class="bottom-hud">
          <span>Drag to rotate 360 deg • Scroll to zoom • Click anatomy to mark pain point</span>
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

        scene.add(new THREE.AmbientLight(0xF8FAFC, 0.7));
        const keyLight = new THREE.DirectionalLight(0xFFF7ED, 0.95);
        keyLight.position.set(2.5, 4.2, 3.5);
        scene.add(keyLight);
        const rimLight = new THREE.DirectionalLight(0x93C5FD, 0.55);
        rimLight.position.set(-2.5, 2.5, -3.5);
        scene.add(rimLight);

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

        function mat(hex, rough=0.44, metal=0.05, opacity=1.0) {{
          return new THREE.MeshStandardMaterial({{
            color: hex, roughness: rough, metalness: metal,
            transparent: opacity < 1.0, opacity: opacity
          }});
        }}

        const mPec = mat(0xD9777F);
        const mDeltoid = mat(0xC96A52);
        const mAbs = mat(0xC85A68);
        const mOblique = mat(0x7C73A8);
        const mBicep = mat(0xB86B84);
        const mForearm = mat(0x6BA38B);
        const mQuad = mat(0x88B06A);
        const mAdductor = mat(0x6E8FB8);
        const mGlute = mat(0xD47A6A);
        const mCalf = mat(0x9E7BB5);
        const mHead = mat(0xC9A86A);
        const mTendon = mat(0xF1EDE1, 0.32);
        const mBone = mat(0xD6CBB5, 0.50);
        const mSkin = mat(0xF5E6DC, 0.25, 0.0, 0.20);

        function addPart(group, clickList, geo, material, x, y, z, rx=0, ry=0, rz=0, sx=1, sy=1, sz=1, region="", structure="") {{
          const mesh = new THREE.Mesh(geo, material);
          mesh.position.set(x, y, z);
          mesh.rotation.set(rx, ry, rz);
          mesh.scale.set(sx, sy, sz);
          mesh.userData = {{ region: region, structure: structure }};
          group.add(mesh);
          if (clickList) clickList.push(mesh);
          return mesh;
        }}

        addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.105, 24, 20), mHead, 0, 1.66, 0, 0,0,0, 0.90, 1.12, 1.0, "TMJ / Jaw", "Temporalis / Cranium");
        addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.078, 20, 16), mPec, 0, 1.56, 0.03, 0,0,0, 0.85, 0.82, 0.88, "TMJ / Jaw", "Masseter / Jaw");
        addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.048, 0.056, 0.14, 20), mAdductor, 0, 1.46, -0.01, 0,0,0, 1,1,1, "Cervical Spine (Neck)", "Cervical / SCM");
        addPart(fullBodyGroup, clickableFull, new THREE.BoxGeometry(0.012, 0.28, 0.03), mTendon, 0, 1.11, 0.082, 0,0,0, 1,1,1, "Lumbar Spine (Lower Back)", "Linea Alba");

        [-1, 1].forEach(s => {{
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.082, 20, 16), mPec, s*0.078, 1.33, 0.055, 0,0,-s*0.18, 1.15, 0.82, 0.58, "Thoracic Spine (Upper Back)", "Pectoralis Major");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.088, 20, 16), mPec, s*0.082, 1.31, -0.058, 0,0,s*0.22, 1.15, 1.05, 0.55, "Thoracic Spine (Upper Back)", "Trapezius / Rhomboids");
          [1.20, 1.12, 1.04, 0.96].forEach(yy => {{
            addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.038, 16, 14), mAbs, s*0.042, yy, 0.075, 0,0,0, 1.05, 0.88, 0.55, "Lumbar Spine (Lower Back)", "Rectus Abdominis");
          }});
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.052, 0.058, 0.24, 18), mOblique, s*0.115, 1.10, 0.01, 0,0,-s*0.06, 0.72, 1.0, 1.15, "Lumbar Spine (Lower Back)", "External Oblique");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.055, 0.065, 0.24, 18), mAdductor, s*0.065, 1.08, -0.055, 0,0,0, 1.0, 1.0, 0.75, "Lumbar Spine (Lower Back)", "Erector Spinae");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.088, 20, 18), mGlute, s*0.078, 0.88, -0.055, 0,0,0, 1.02, 1.05, 0.82, "Hip & Groin", "Gluteus Maximus");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.068, 18, 16), mAdductor, s*0.095, 0.89, 0.042, 0,0,0, 0.95, 1.05, 0.75, "Hip & Groin", "Iliopsoas / TFL");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.066, 20, 18), mDeltoid, s*0.195, 1.35, 0.0, 0,0,-s*0.25, 0.95, 1.25, 0.95, "Shoulder Complex", "Deltoid");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.042, 0.036, 0.22, 18), mBicep, s*0.235, 1.18, 0.012, 0,0,s*0.18, 1,1,1, "Shoulder Complex", "Biceps / Triceps");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.036, 16, 14), mTendon, s*0.265, 1.06, 0.0, 0,0,0, 1,1,1, "Elbow", "Elbow / Olecranon");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.036, 0.025, 0.22, 18), mForearm, s*0.295, 0.94, 0.015, 0,0,s*0.14, 1,1,1, "Elbow", "Forearm");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.032, 16, 14), mTendon, s*0.325, 0.80, 0.025, 0,0,s*0.12, 0.65, 1.55, 0.95, "Wrist & Hand", "Wrist & Hand");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.072, 0.052, 0.34, 20), mQuad, s*0.095, 0.66, 0.018, 0,0,-s*0.03, 0.95, 1.0, 1.05, "Hip & Groin", "Quadriceps");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.048, 0.036, 0.32, 16), mAdductor, s*0.058, 0.67, 0.0, 0,0,-s*0.05, 0.85, 1.0, 0.95, "Hip & Groin", "Adductors");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.064, 0.048, 0.33, 18), mBicep, s*0.092, 0.66, -0.025, 0,0,-s*0.03, 0.95, 1.0, 0.95, "Hip & Groin", "Hamstrings");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.046, 18, 16), mTendon, s*0.095, 0.47, 0.015, 0,0,0, 0.95, 1.05, 1.0, "Knee Joint", "Patella & Knee");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.050, 0.032, 0.34, 20), mCalf, s*0.095, 0.27, -0.008, 0,0,0, 0.95, 1.0, 1.05, "Knee Joint", "Gastrocnemius / Tibialis");
          addPart(fullBodyGroup, clickableFull, new THREE.CylinderGeometry(0.016, 0.020, 0.14, 12), mTendon, s*0.095, 0.14, -0.028, 0,0,0, 1,1,1, "Ankle & Foot", "Achilles Tendon");
          addPart(fullBodyGroup, clickableFull, new THREE.SphereGeometry(0.038, 16, 14), mTendon, s*0.095, 0.04, 0.038, 0,0,0, 0.88, 0.55, 1.85, "Ankle & Foot", "Ankle & Foot");
        }});

        const torsoSkin = new THREE.Mesh(new THREE.CylinderGeometry(0.165, 0.145, 0.62, 24), mSkin);
        torsoSkin.position.set(0, 1.12, 0);
        torsoSkin.scale.set(1.08, 1.0, 0.68);
        skinShellGroup.add(torsoSkin);

        addPart(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.024, 0.028, 0.56, 18), mBone, 0.08, 1.42, 0.04, 0, 0, Math.PI/2 - 0.08, 1,1,1, "Shoulder Complex", "Clavicle");
        [1.26, 1.14, 1.02, 0.90, 0.78].forEach((ry, i) => {{
          const rib = new THREE.TorusGeometry(0.24 - i*0.01, 0.016, 12, 28, Math.PI * 0.85);
          addPart(shoulderDetailGroup, clickableShoulder, rib, mBone, 0.24, ry, -0.02, Math.PI/2, 0.2, -0.4, 1,1,1, "Thoracic Spine (Upper Back)", `Rib #${{i+2}}`);
        }});
        addPart(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.036, 0.032, 0.68, 18), mBone, -0.14, 1.04, 0.0, 0, 0, 0.05, 1,1,1, "Shoulder Complex", "Humerus");
        addPart(shoulderDetailGroup, clickableShoulder, new THREE.SphereGeometry(0.135, 24, 20), mDeltoid, -0.17, 1.26, 0.03, 0.1, 0.2, -0.22, 0.85, 1.55, 0.78, "Shoulder Complex", "Deltoid");
        addPart(shoulderDetailGroup, clickableShoulder, new THREE.BoxGeometry(0.16, 0.34, 0.035), mDeltoid, 0.06, 1.18, 0.11, -0.15, 0.2, 0.42, 1,1,1, "Shoulder Complex", "Pectoralis Minor");
        addPart(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.018, 0.026, 0.32, 16), mTendon, -0.11, 1.16, 0.08, 0.08, 0, -0.14, 1,1,1, "Shoulder Complex", "Biceps Tendon");
        addPart(shoulderDetailGroup, clickableShoulder, new THREE.CylinderGeometry(0.034, 0.042, 0.38, 18), mDeltoid, -0.13, 0.84, 0.08, 0, 0, 0.04, 1,1,1, "Shoulder Complex", "Biceps Belly");
        addPart(shoulderDetailGroup, null, new THREE.CylinderGeometry(0.24, 0.22, 0.85, 24), mSkin, -0.05, 1.08, 0.0, 0,0,0, 1.15, 1.0, 0.85, "", "");

        window.setMode = function(mode) {{
          currentMode = mode;
          fullBodyGroup.visible = (mode === 'full');
          shoulderDetailGroup.visible = (mode === 'shoulder');
          document.getElementById('mode-full').classList.toggle('active', mode === 'full');
          document.getElementById('mode-shoulder').classList.toggle('active', mode === 'shoulder');
          badgeEl.textContent = mode === 'full' ? "3D Ecorche Ready • Click muscle to pin pain" : "Shoulder Deep Anatomy Cutaway";
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
          const structure = ud.structure || ud.region || "Anatomical Point";
          const desc = `#${{num}} ${{lr}}${{structure}}`;
          markedPins.push(desc);
          badgeEl.textContent = "Pinned: " + desc;
          pinReadoutEl.textContent = "Pain pins (" + markedPins.length + "): " + markedPins.slice(-2).join(" | ");
        }}

        window.clearPins = function() {{
          while (painPinsGroup.children.length > 0) painPinsGroup.remove(painPinsGroup.children[0]);
          markedPins.length = 0;
          badgeEl.textContent = "Pain pins cleared";
          pinReadoutEl.textContent = "Pain pins: 0";
        }};

        window.setAngle = function(radY) {{
          rootGroup.rotation.y = radY;
          rootGroup.rotation.x = 0;
        }};

        let dragging = false, moved = false, prevX = 0, prevY = 0;
        renderer.domElement.addEventListener('pointerdown', e => {{ dragging = true; moved = false; prevX = e.clientX; prevY = e.clientY; }});
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
  components.html(html_code, height=534)
