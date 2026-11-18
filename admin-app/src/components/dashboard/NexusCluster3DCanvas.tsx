import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { ChevronDown, ChevronUp, Maximize2, Minimize2, RotateCcw } from 'lucide-react';

export interface InfraNode3DTelemetry {
  id: string;
  name: string;
  shortLabel: string;
  role: string;
  gpuPct: number;
  memoryPct: number;
  aiComputePct: number;
  status: 'HEALTHY' | 'CAUTION' | 'STANDBY' | 'POLICY_LOCK';
  accentHex: number;
}

interface NexusCluster3DCanvasProps {
  nodes: InfraNode3DTelemetry[];
  selectedNodeId: string;
  onSelectNode: (id: string) => void;
  fullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

type CameraPresetId = 'overview' | 'mac-mini' | 'oracle' | 'ai-gateway';

const CAMERA_PRESETS: Record<
  CameraPresetId,
  { label: string; pos: [number, number, number]; target: [number, number, number] }
> = {
  overview: { label: 'Cluster Overview', pos: [0, 7.2, 11.8], target: [0, 1.1, 0] },
  'mac-mini': { label: 'Mac mini Metal', pos: [-4.6, 3.6, 5.4], target: [-3.4, 1.0, 0.2] },
  oracle: { label: 'Oracle Control', pos: [0.4, 4.1, 5.2], target: [0, 1.2, -1.8] },
  'ai-gateway': { label: 'AI & GPU Cloud', pos: [5.0, 3.8, 5.5], target: [3.2, 1.1, 0.2] },
};

// Pre-allocated scratch math helpers (zero GC churn inside tick loop)
const _vec3A = new THREE.Vector3();
const _mat4 = new THREE.Matrix4();
const _quat = new THREE.Quaternion();
const _scale = new THREE.Vector3();
const _up = new THREE.Vector3(0, 1, 0);

function detectSoftwareWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
    if (!gl) return true;
    const ext = gl.getExtension('WEBGL_debug_renderer_info');
    const param = ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER;
    const gpu = String(gl.getParameter(param) || '');
    gl.getExtension('WEBGL_lose_context')?.loseContext();
    return /SwiftShader|llvmpipe|softpipe|Software|Basic Render/i.test(gpu);
  } catch {
    return true;
  }
}

function createStudioGridTexture(maxAnisotropy: number): THREE.CanvasTexture {
  const size = 512;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.fillStyle = '#e2e8f0';
    ctx.fillRect(0, 0, size, size);

    // Subtle brushed grain
    ctx.fillStyle = '#cbd5e1';
    for (let i = 0; i < size; i += 32) {
      ctx.fillRect(i, 0, 1, size);
      ctx.fillRect(0, i, size, 1);
    }
    ctx.fillStyle = '#94a3b8';
    ctx.fillRect(0, 0, 2, size);
    ctx.fillRect(0, 0, size, 2);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(16, 16);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = Math.min(8, maxAnisotropy || 1);
  return tex;
}

function createBrushedMetalRoughnessTexture(): THREE.CanvasTexture {
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.fillStyle = '#999999';
    ctx.fillRect(0, 0, size, size);
    for (let y = 0; y < size; y += 2) {
      const shade = 128 + Math.floor(Math.sin(y * 0.45) * 24 + (y % 6 === 0 ? 18 : 0));
      ctx.fillStyle = `rgb(${shade},${shade},${shade})`;
      ctx.fillRect(0, y, size, 1);
    }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  return tex;
}

function createRadialContactShadowTexture(): THREE.CanvasTexture {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const grad = ctx.createRadialGradient(
      size / 2,
      size / 2,
      size * 0.08,
      size / 2,
      size / 2,
      size * 0.48
    );
    grad.addColorStop(0, 'rgba(15, 23, 42, 0.42)');
    grad.addColorStop(0.55, 'rgba(15, 23, 42, 0.16)');
    grad.addColorStop(1, 'rgba(15, 23, 42, 0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export const NexusCluster3DCanvas: React.FC<NexusCluster3DCanvasProps> = ({
  nodes,
  selectedNodeId,
  onSelectNode,
  fullscreen = false,
  onToggleFullscreen,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const nodesRef = useRef<InfraNode3DTelemetry[]>(nodes);
  const selectedIdRef = useRef<string>(selectedNodeId);
  const onSelectRef = useRef(onSelectNode);

  const [dockCollapsed, setDockCollapsed] = useState(false);
  const [activePreset, setActivePreset] = useState<CameraPresetId>('overview');

  const presetTargetRef = useRef<{
    active: boolean;
    pos: THREE.Vector3;
    target: THREE.Vector3;
  }>({
    active: false,
    pos: new THREE.Vector3(...CAMERA_PRESETS.overview.pos),
    target: new THREE.Vector3(...CAMERA_PRESETS.overview.target),
  });

  useEffect(() => {
    nodesRef.current = nodes;
  }, [nodes]);

  useEffect(() => {
    selectedIdRef.current = selectedNodeId;
  }, [selectedNodeId]);

  useEffect(() => {
    onSelectRef.current = onSelectNode;
  }, [onSelectNode]);

  const applyCameraPreset = (presetId: CameraPresetId) => {
    const p = CAMERA_PRESETS[presetId];
    setActivePreset(presetId);
    presetTargetRef.current.pos.set(...p.pos);
    presetTargetRef.current.target.set(...p.target);
    presetTargetRef.current.active = true;
  };

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const isSoftwareGl = detectSoftwareWebGL();
    const width = Math.max(320, container.clientWidth);
    const height = Math.max(240, container.clientHeight);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf1f5f9);
    scene.fog = new THREE.FogExp2(0xf1f5f9, 0.026);

    const camera = new THREE.PerspectiveCamera(44, width / height, 0.1, 100);
    camera.position.set(...CAMERA_PRESETS.overview.pos);

    const renderer = new THREE.WebGLRenderer({
      antialias: !isSoftwareGl,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(isSoftwareGl ? 1 : Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    renderer.shadowMap.enabled = !isSoftwareGl;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.style.display = 'block';
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    container.appendChild(renderer.domElement);

    // Studio IBL Environment
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    const envRT = pmremGenerator.fromScene(new RoomEnvironment(), 0.04);
    scene.environment = envRT.texture;
    pmremGenerator.dispose();

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(...CAMERA_PRESETS.overview.target);
    controls.enableDamping = !isSoftwareGl;
    controls.dampingFactor = 0.07;
    controls.minDistance = 4.2;
    controls.maxDistance = 22;
    controls.maxPolarAngle = Math.PI / 2 - 0.06;
    controls.addEventListener('start', () => {
      presetTargetRef.current.active = false;
    });

    // Warm/Cool Balanced 3-Point Studio Lighting
    const hemiLight = new THREE.HemisphereLight(0xdbeafe, 0xcbd5e1, 0.9);
    hemiLight.position.set(0, 18, 0);
    scene.add(hemiLight);

    const keyLight = new THREE.DirectionalLight(0xfff7ed, 2.0);
    keyLight.position.set(8, 13, 9);
    keyLight.castShadow = !isSoftwareGl;
    keyLight.shadow.mapSize.set(1024, 1024);
    keyLight.shadow.camera.near = 1;
    keyLight.shadow.camera.far = 36;
    const shadowBound = 10;
    keyLight.shadow.camera.left = -shadowBound;
    keyLight.shadow.camera.right = shadowBound;
    keyLight.shadow.camera.top = shadowBound;
    keyLight.shadow.camera.bottom = -shadowBound;
    keyLight.shadow.bias = -0.0005;
    keyLight.shadow.normalBias = 0.02;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0xbfdbfe, 0.75);
    rimLight.position.set(-9, 7, -8);
    scene.add(rimLight);

    // Procedural Textures
    const gridTex = createStudioGridTexture(renderer.capabilities.getMaxAnisotropy());
    const metalRoughTex = createBrushedMetalRoughnessTexture();
    const shadowTex = createRadialContactShadowTexture();

    // Track disposable resources cleanly
    const disposables: { dispose: () => void }[] = [gridTex, metalRoughTex, shadowTex, envRT];
    const trackGeo = <T extends THREE.BufferGeometry>(g: T): T => {
      disposables.push(g);
      return g;
    };
    const trackMat = <T extends THREE.Material>(m: T): T => {
      disposables.push(m);
      return m;
    };

    // Studio Ground Plane
    const floorGeo = trackGeo(new THREE.PlaneGeometry(54, 54));
    const floorMat = trackMat(
      new THREE.MeshStandardMaterial({
        map: gridTex,
        roughness: 0.88,
        metalness: 0.08,
      })
    );
    const floorMesh = new THREE.Mesh(floorGeo, floorMat);
    floorMesh.rotation.x = -Math.PI / 2;
    floorMesh.receiveShadow = true;
    scene.add(floorMesh);

    // Shared Materials
    const brushedAluminumMat = trackMat(
      new THREE.MeshPhysicalMaterial({
        color: 0xdbe2ea,
        metalness: 0.85,
        roughness: 0.24,
        roughnessMap: metalRoughTex,
        clearcoat: 0.25,
      })
    );
    const darkAnodizedMat = trackMat(
      new THREE.MeshStandardMaterial({
        color: 0x1e293b,
        metalness: 0.65,
        roughness: 0.52,
      })
    );
    const ceramicSlateMat = trackMat(
      new THREE.MeshStandardMaterial({
        color: 0xf8fafc,
        metalness: 0.08,
        roughness: 0.35,
      })
    );
    const copperTrimMat = trackMat(
      new THREE.MeshStandardMaterial({
        color: 0x0284c7,
        metalness: 0.78,
        roughness: 0.22,
      })
    );
    const shadowPlaneMat = trackMat(
      new THREE.MeshBasicMaterial({
        map: shadowTex,
        transparent: true,
        depthWrite: false,
        opacity: 0.45,
      })
    );

    const bevelShape = new THREE.Shape();
    bevelShape.moveTo(-0.75, -0.75);
    bevelShape.lineTo(0.75, -0.75);
    bevelShape.lineTo(0.75, 0.75);
    bevelShape.lineTo(-0.75, 0.75);
    bevelShape.closePath();

    const plinthGeo = trackGeo(
      new THREE.ExtrudeGeometry(bevelShape, {
        depth: 0.16,
        bevelEnabled: true,
        bevelThickness: 0.04,
        bevelSize: 0.05,
        bevelSegments: 2,
      })
    );
    plinthGeo.rotateX(Math.PI / 2);

    const shadowPlaneGeo = trackGeo(new THREE.PlaneGeometry(3.1, 3.1));
    const barTrackGeo = trackGeo(new THREE.BoxGeometry(0.22, 1.5, 0.22));
    const barFillGeo = trackGeo(new THREE.BoxGeometry(0.2, 1, 0.2));
    // Shift origin of barFillGeo so Y scales cleanly upward from y = 0
    barFillGeo.translate(0, 0.5, 0);

    // Node spatial positions on the cluster floor
    const layoutCoords: Record<string, [number, number, number]> = {
      'node-mac-mini': [-3.6, 0, 0.8],
      'node-contabo': [-1.4, 0, -1.3],
      'node-oracle': [0, 0, -2.5],
      'node-openrouter': [2.2, 0, -0.8],
      'node-modal': [3.8, 0, 1.2],
    };

    interface NodeRig {
      id: string;
      group: THREE.Group;
      gpuBar: THREE.Mesh;
      memBar: THREE.Mesh;
      aiBar: THREE.Mesh;
      haloMesh?: THREE.Mesh;
      selectionRing: THREE.Mesh;
      hitProxy: THREE.Mesh;
      currentGpu: number;
      currentMem: number;
      currentAi: number;
    }

    const nodeRigs: NodeRig[] = [];
    const hitProxies: THREE.Object3D[] = [];
    const ringGeo = trackGeo(new THREE.RingGeometry(1.18, 1.28, 36));
    ringGeo.rotateX(-Math.PI / 2);

    const buildCompositeNode = (node: InfraNode3DTelemetry, idx: number): NodeRig => {
      const group = new THREE.Group();
      const coords = layoutCoords[node.id] || [
        (idx - 2) * 2.4,
        0,
        idx % 2 === 0 ? 0.6 : -1.0,
      ];
      group.position.set(coords[0], 0, coords[2]);

      // 1. Contact Shadow (flush slightly above ground)
      const contactShadow = new THREE.Mesh(shadowPlaneGeo, shadowPlaneMat);
      contactShadow.rotation.x = -Math.PI / 2;
      contactShadow.position.y = 0.02;
      group.add(contactShadow);

      // 2. Selection Ring (flush at y = 0.03)
      const selMat = trackMat(
        new THREE.MeshBasicMaterial({
          color: node.accentHex,
          transparent: true,
          opacity: node.id === selectedNodeId ? 0.95 : 0.15,
          side: THREE.DoubleSide,
        })
      );
      const selectionRing = new THREE.Mesh(ringGeo, selMat);
      selectionRing.position.y = 0.03;
      group.add(selectionRing);

      // 3. Base Beveled Plinth (bottom-center grounded)
      const plinth = new THREE.Mesh(plinthGeo, darkAnodizedMat);
      plinth.position.y = 0.2;
      plinth.castShadow = true;
      plinth.receiveShadow = true;
      group.add(plinth);

      // 4. Primary & Secondary Composite Architectural Assembly (3-10 parts per node)
      let haloMesh: THREE.Mesh | undefined;

      if (node.id === 'node-mac-mini') {
        // Unibody Apple Silicon Aluminum Deck + Heat Sink Fins + Metal Core Puck
        const bodyGeo = trackGeo(new THREE.BoxGeometry(1.22, 0.34, 1.22));
        const body = new THREE.Mesh(bodyGeo, brushedAluminumMat);
        body.position.y = 0.41;
        body.castShadow = true;
        group.add(body);

        const capGeo = trackGeo(new THREE.CylinderGeometry(0.46, 0.5, 0.1, 24));
        const cap = new THREE.Mesh(capGeo, ceramicSlateMat);
        cap.position.y = 0.63;
        cap.castShadow = true;
        group.add(cap);

        const finGeo = trackGeo(new THREE.BoxGeometry(0.95, 0.08, 0.05));
        for (let f = -2; f <= 2; f++) {
          const fin = new THREE.Mesh(finGeo, darkAnodizedMat);
          fin.position.set(0, 0.72, f * 0.14);
          group.add(fin);
        }

        const corePuckGeo = trackGeo(new THREE.CylinderGeometry(0.24, 0.24, 0.14, 20));
        const corePuck = new THREE.Mesh(corePuckGeo, copperTrimMat);
        corePuck.position.y = 0.76;
        group.add(corePuck);
      } else if (node.id === 'node-oracle') {
        // Hexagonal Coordination Pedestal + Twin Waveguides + Coordination Halo
        const towerGeo = trackGeo(new THREE.CylinderGeometry(0.46, 0.58, 1.05, 6));
        const tower = new THREE.Mesh(towerGeo, ceramicSlateMat);
        tower.position.y = 0.74;
        tower.castShadow = true;
        group.add(tower);

        const collarGeo = trackGeo(new THREE.CylinderGeometry(0.52, 0.52, 0.12, 6));
        const collar = new THREE.Mesh(collarGeo, darkAnodizedMat);
        collar.position.y = 1.26;
        group.add(collar);

        const mastGeo = trackGeo(new THREE.CylinderGeometry(0.035, 0.045, 0.65, 10));
        const mastL = new THREE.Mesh(mastGeo, brushedAluminumMat);
        mastL.position.set(-0.22, 1.62, 0);
        const mastR = new THREE.Mesh(mastGeo, brushedAluminumMat);
        mastR.position.set(0.22, 1.62, 0);
        group.add(mastL, mastR);

        const haloGeo = trackGeo(new THREE.TorusGeometry(0.42, 0.035, 12, 32));
        haloMesh = new THREE.Mesh(haloGeo, copperTrimMat);
        haloMesh.rotation.x = Math.PI / 2;
        haloMesh.position.y = 1.56;
        group.add(haloMesh);
      } else if (node.id === 'node-openrouter') {
        // Fluted Lathe AI Gateway Core + Torus Optical Manifold
        const points = [
          new THREE.Vector2(0.01, 0),
          new THREE.Vector2(0.48, 0),
          new THREE.Vector2(0.42, 0.45),
          new THREE.Vector2(0.28, 0.95),
          new THREE.Vector2(0.36, 1.28),
          new THREE.Vector2(0.01, 1.32),
        ];
        const latheGeo = trackGeo(new THREE.LatheGeometry(points, 24));
        const body = new THREE.Mesh(latheGeo, brushedAluminumMat);
        body.position.y = 0.24;
        body.castShadow = true;
        group.add(body);

        const ringCollarGeo = trackGeo(new THREE.TorusGeometry(0.38, 0.05, 12, 28));
        haloMesh = new THREE.Mesh(ringCollarGeo, copperTrimMat);
        haloMesh.rotation.x = Math.PI / 2;
        haloMesh.position.y = 1.24;
        group.add(haloMesh);
      } else {
        // Multi-Blade Server Chassis (Contabo / Modal)
        const rackGeo = trackGeo(new THREE.BoxGeometry(1.06, 1.22, 0.88));
        const rack = new THREE.Mesh(rackGeo, darkAnodizedMat);
        rack.position.y = 0.84;
        rack.castShadow = true;
        group.add(rack);

        const bladeGeo = trackGeo(new THREE.BoxGeometry(0.92, 0.18, 0.91));
        for (let b = 0; b < 4; b++) {
          const blade = new THREE.Mesh(
            bladeGeo,
            b % 2 === 0 ? brushedAluminumMat : ceramicSlateMat
          );
          blade.position.y = 0.42 + b * 0.26;
          group.add(blade);
        }

        const shroudGeo = trackGeo(new THREE.BoxGeometry(0.86, 0.14, 0.72));
        const shroud = new THREE.Mesh(shroudGeo, copperTrimMat);
        shroud.position.y = 1.52;
        group.add(shroud);
      }

      // 5. Three Vertical Animated Telemetry Columns Mounted on FrontApron: GPU / MEM / AI
      const barTrackMat = trackMat(
        new THREE.MeshStandardMaterial({
          color: 0xe2e8f0,
          transparent: true,
          opacity: 0.32,
          roughness: 0.4,
        })
      );

      const makeMeterColumn = (xOffset: number, colorHex: number) => {
        const track = new THREE.Mesh(barTrackGeo, barTrackMat);
        track.position.set(xOffset, 0.99, 0.66);
        group.add(track);

        const fillMat = trackMat(
          new THREE.MeshStandardMaterial({
            color: colorHex,
            emissive: colorHex,
            emissiveIntensity: 0.28,
            roughness: 0.25,
            metalness: 0.15,
          })
        );
        const fill = new THREE.Mesh(barFillGeo, fillMat);
        fill.position.set(xOffset, 0.24, 0.66);
        fill.scale.y = 0.1;
        group.add(fill);
        return fill;
      };

      const gpuBar = makeMeterColumn(-0.34, 0x2563eb); // Blue = GPU / Metal
      const memBar = makeMeterColumn(0.0, 0x059669); // Emerald = Memory
      const aiBar = makeMeterColumn(0.34, 0x7c3aed); // Violet = AI Compute Availability

      // 6. Dedicated Hit Proxy for clean Raycasting
      const proxyGeo = trackGeo(new THREE.BoxGeometry(1.75, 2.2, 1.75));
      const proxyMat = trackMat(new THREE.MeshBasicMaterial({ visible: false }));
      const hitProxy = new THREE.Mesh(proxyGeo, proxyMat);
      hitProxy.position.y = 1.1;
      hitProxy.userData = { nodeId: node.id };
      hitProxy.layers.set(1);
      group.add(hitProxy);
      hitProxies.push(hitProxy);

      scene.add(group);
      return {
        id: node.id,
        group,
        gpuBar,
        memBar,
        aiBar,
        haloMesh,
        selectionRing,
        hitProxy,
        currentGpu: node.gpuPct / 100,
        currentMem: node.memoryPct / 100,
        currentAi: node.aiComputePct / 100,
      };
    };

    nodes.forEach((n, idx) => {
      nodeRigs.push(buildCompositeNode(n, idx));
    });

    // Fiber Conduit Curves connecting Oracle Control Plane <-> Infrastructure Nodes
    const oracleAnchor = new THREE.Vector3(...(layoutCoords['node-oracle'] || [0, 0, -2.5]));
    oracleAnchor.y = 0.28;
    const curves: THREE.CatmullRomCurve3[] = [];
    const tubeMat = trackMat(
      new THREE.MeshStandardMaterial({
        color: 0x94a3b8,
        roughness: 0.4,
        metalness: 0.5,
      })
    );

    nodeRigs.forEach(rig => {
      if (rig.id === 'node-oracle') return;
      const start = oracleAnchor.clone();
      const end = rig.group.position.clone();
      end.y = 0.28;
      const mid = start.clone().lerp(end, 0.5);
      mid.y = 0.48;
      const curve = new THREE.CatmullRomCurve3([start, mid, end]);
      curves.push(curve);
      const tubeGeo = trackGeo(new THREE.TubeGeometry(curve, 24, 0.025, 8, false));
      const tube = new THREE.Mesh(tubeGeo, tubeMat);
      scene.add(tube);
    });

    // Instanced Data Packets flowing smoothly along the fiber conduits
    const packetCount = Math.max(1, curves.length * 6);
    const packetGeo = trackGeo(new THREE.SphereGeometry(0.055, 10, 10));
    const packetMat = trackMat(
      new THREE.MeshStandardMaterial({
        color: 0x2563eb,
        emissive: 0x3b82f6,
        emissiveIntensity: 0.7,
        roughness: 0.2,
      })
    );
    const packetMesh = new THREE.InstancedMesh(packetGeo, packetMat, packetCount);
    packetMesh.frustumCulled = false;
    scene.add(packetMesh);

    // Pre-warm shaders when hardware WebGL is active
    if (!isSoftwareGl) {
      renderer.compile(scene, camera);
    }

    // Raycaster on Layer 1
    const raycaster = new THREE.Raycaster();
    raycaster.layers.set(1);
    const pointerNdc = new THREE.Vector2();

    const handlePointerDown = (e: PointerEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      pointerNdc.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      pointerNdc.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointerNdc, camera);
      const hits = raycaster.intersectObjects(hitProxies, false);
      if (hits.length > 0) {
        const hitId = hits[0].object.userData?.nodeId;
        if (hitId) {
          onSelectRef.current(hitId);
        }
      }
    };
    renderer.domElement.addEventListener('pointerdown', handlePointerDown);

    // ResizeObserver for clean container responsiveness
    const handleResize = () => {
      if (!container) return;
      const w = Math.max(320, container.clientWidth);
      const h = Math.max(240, container.clientHeight);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(container);

    // Render Loop with software-WebGL pacing & zero per-frame allocations
    const clock = new THREE.Clock();
    let frameId = 0;
    let isDisposed = false;

    const afterDraw = (cb: () => void) => {
      const gl = renderer.getContext() as WebGL2RenderingContext;
      if (!gl || typeof gl.fenceSync !== 'function') {
        frameId = window.setTimeout(cb, 80);
        return;
      }
      const sync = gl.fenceSync(gl.SYNC_GPU_COMMANDS_COMPLETE, 0);
      gl.flush();
      const poll = () => {
        if (isDisposed) return;
        const state = sync && gl.getSyncParameter(sync, gl.SYNC_STATUS);
        if (state === gl.UNSIGNALED) {
          frameId = window.setTimeout(poll, 5);
        } else {
          if (sync) gl.deleteSync(sync);
          frameId = window.setTimeout(cb, 80);
        }
      };
      frameId = window.setTimeout(poll, 5);
    };

    const tick = () => {
      if (isDisposed) return;
      const dt = Math.min(clock.getDelta(), 0.05);
      const elapsed = clock.getElapsedTime();

      // Smooth damped camera preset transitions
      if (presetTargetRef.current.active) {
        const factor = 1 - Math.exp(-5.5 * dt);
        camera.position.lerp(presetTargetRef.current.pos, factor);
        controls.target.lerp(presetTargetRef.current.target, factor);
        if (
          camera.position.distanceToSquared(presetTargetRef.current.pos) < 0.004 &&
          controls.target.distanceToSquared(presetTargetRef.current.target) < 0.004
        ) {
          presetTargetRef.current.active = false;
        }
      }

      controls.update();

      // Update composite node telemetry bars & halos smoothly
      const currentNodes = nodesRef.current;
      const selId = selectedIdRef.current;

      for (let i = 0; i < nodeRigs.length; i++) {
        const rig = nodeRigs[i];
        const data = currentNodes.find(n => n.id === rig.id);
        if (data) {
          const targetGpu = Math.max(0.04, Math.min(1, data.gpuPct / 100));
          const targetMem = Math.max(0.04, Math.min(1, data.memoryPct / 100));
          const targetAi = Math.max(0.04, Math.min(1, data.aiComputePct / 100));

          rig.currentGpu = THREE.MathUtils.damp(rig.currentGpu, targetGpu, 6, dt);
          rig.currentMem = THREE.MathUtils.damp(rig.currentMem, targetMem, 6, dt);
          rig.currentAi = THREE.MathUtils.damp(rig.currentAi, targetAi, 6, dt);

          rig.gpuBar.scale.y = rig.currentGpu * 1.48;
          rig.memBar.scale.y = rig.currentMem * 1.48;
          rig.aiBar.scale.y = rig.currentAi * 1.48;
        }

        const ringMat = rig.selectionRing.material as THREE.MeshBasicMaterial;
        ringMat.opacity = THREE.MathUtils.damp(
          ringMat.opacity,
          rig.id === selId ? 0.95 : 0.14,
          8,
          dt
        );

        if (rig.haloMesh) {
          rig.haloMesh.rotation.z = elapsed * 0.55;
        }
      }

      // Animate InstancedMesh telemetry packets along fiber conduits
      let idx = 0;
      for (let c = 0; c < curves.length; c++) {
        const curve = curves[c];
        for (let p = 0; p < 6; p++) {
          const t = ((elapsed * 0.24 + p / 6 + c * 0.13) % 1 + 1) % 1;
          curve.getPointAt(t, _vec3A);
          _quat.setFromAxisAngle(_up, elapsed + p);
          _scale.setScalar(0.85 + Math.sin(elapsed * 3 + p) * 0.15);
          _mat4.compose(_vec3A, _quat, _scale);
          packetMesh.setMatrixAt(idx, _mat4);
          idx++;
        }
      }
      if (curves.length > 0) {
        packetMesh.instanceMatrix.needsUpdate = true;
      }

      renderer.render(scene, camera);

      if (isSoftwareGl) {
        afterDraw(tick);
      } else {
        frameId = requestAnimationFrame(tick);
      }
    };

    tick();

    return () => {
      isDisposed = true;
      cancelAnimationFrame(frameId);
      clearTimeout(frameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener('pointerdown', handlePointerDown);
      controls.dispose();
      disposables.forEach(d => d.dispose());
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  const selectedNode = nodes.find(n => n.id === selectedNodeId) || nodes[0];

  return (
    <div
      className={
        fullscreen
          ? 'fixed inset-0 z-50 bg-slate-100 select-none'
          : 'relative w-full h-[380px] rounded-xl border border-slate-200/90 bg-slate-100 overflow-hidden select-none'
      }
    >
      {/* Isolated WebGL Canvas Mount */}
      <div ref={mountRef} className="w-full h-full" />

      {/* Minimal Top-Left Selected Node Spec Strip (no backdrop-filter over WebGL) */}
      <div
        className="absolute top-3 left-3 px-3 py-2 rounded-xl border border-slate-200 shadow-xs max-w-[300px]"
        style={{ backgroundColor: 'rgba(255, 255, 255, 0.94)' }}
      >
        <div className="flex items-center justify-between gap-3">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            3D Infrastructure Twin
          </span>
          <span className="text-[10px] font-mono font-semibold text-blue-700">
            Click node to inspect
          </span>
        </div>
        {selectedNode && (
          <div className="mt-1 space-y-1">
            <div className="text-xs font-bold text-slate-900 truncate">{selectedNode.name}</div>
            <div className="flex items-center gap-3 text-[11px] font-mono tabular-nums">
              <span className="text-blue-700 font-semibold">GPU {selectedNode.gpuPct}%</span>
              <span className="text-emerald-700 font-semibold">MEM {selectedNode.memoryPct}%</span>
              <span className="text-violet-700 font-semibold">AI {selectedNode.aiComputePct}%</span>
            </div>
          </div>
        )}
      </div>

      {/* Top-Right Fullscreen Expand/Collapse Button */}
      {onToggleFullscreen && (
        <button
          type="button"
          onClick={onToggleFullscreen}
          className="absolute top-3 right-3 px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:text-slate-900 flex items-center gap-1.5 shadow-xs cursor-pointer"
          style={{ backgroundColor: 'rgba(255, 255, 255, 0.94)' }}
        >
          {fullscreen ? (
            <>
              <Minimize2 className="w-3.5 h-3.5" />
              <span>Exit Fullscreen</span>
            </>
          ) : (
            <>
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Expand 3D View</span>
            </>
          )}
        </button>
      )}

      {/* Collapsible Bottom Control Dock */}
      <div
        className="absolute left-1/2 -translate-x-1/2 transition-transform duration-300"
        style={{
          bottom: dockCollapsed ? '-46px' : '12px',
          maxWidth: 'min(760px, 94%)',
        }}
      >
        <div className="flex justify-center mb-1">
          <button
            type="button"
            onClick={() => setDockCollapsed(v => !v)}
            className="px-2.5 py-0.5 rounded-t-lg border border-b-0 border-slate-200 text-[10px] font-semibold text-slate-600 hover:text-slate-900 flex items-center gap-1 cursor-pointer shadow-2xs"
            style={{ backgroundColor: 'rgba(255, 255, 255, 0.95)' }}
          >
            {dockCollapsed ? (
              <>
                <ChevronUp className="w-3 h-3" />
                <span>Show Camera Dock</span>
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                <span>Hide Dock</span>
              </>
            )}
          </button>
        </div>

        <div
          className="px-2.5 py-1.5 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-center gap-1.5"
          style={{ backgroundColor: 'rgba(255, 255, 255, 0.96)' }}
        >
          {(Object.keys(CAMERA_PRESETS) as CameraPresetId[]).map(presetId => (
            <button
              key={presetId}
              type="button"
              onClick={() => applyCameraPreset(presetId)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-colors cursor-pointer ${
                activePreset === presetId
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {CAMERA_PRESETS[presetId].label}
            </button>
          ))}
          <span className="text-slate-300">|</span>
          <button
            type="button"
            onClick={() => applyCameraPreset('overview')}
            className="px-2 py-1 rounded-lg text-[11px] font-semibold text-slate-600 hover:bg-slate-100 flex items-center gap-1 cursor-pointer"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset</span>
          </button>
          <span className="hidden sm:inline text-[10px] font-mono text-slate-400 pl-1">
            Blue=GPU · Green=Mem · Violet=AI
          </span>
        </div>
      </div>
    </div>
  );
};
