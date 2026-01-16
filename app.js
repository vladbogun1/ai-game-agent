import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(canvas.clientWidth, canvas.clientHeight);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog("#0b0b0d", 12, 50);

const camera = new THREE.PerspectiveCamera(
  35,
  canvas.clientWidth / canvas.clientHeight,
  0.1,
  100
);
camera.position.set(0, 6.5, 16.5);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.minDistance = 6;
controls.maxDistance = 30;
controls.target.set(0, 1, 0);

const ambient = new THREE.AmbientLight("#ffffff", 1.15);
scene.add(ambient);

const keyLight = new THREE.DirectionalLight("#ffffff", 1.2);
keyLight.position.set(6, 10, 6);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight("#ff99aa", 0.45);
fillLight.position.set(-6, 4, -6);
scene.add(fillLight);

const hemiLight = new THREE.HemisphereLight("#ffffff", "#1a1a24", 0.6);
scene.add(hemiLight);

const cameraLight = new THREE.PointLight("#ffffff", 0.5, 60);
scene.add(cameraLight);

const keyboardGroup = new THREE.Group();
scene.add(keyboardGroup);

const layout = [
  [
    { label: "Esc", w: 1 },
    { label: "F1", w: 1 },
    { label: "F2", w: 1 },
    { label: "F3", w: 1 },
    { label: "F4", w: 1 },
    { label: "F5", w: 1 },
    { label: "F6", w: 1 },
    { label: "F7", w: 1 },
    { label: "F8", w: 1 },
    { label: "F9", w: 1 },
    { label: "F10", w: 1 },
    { label: "F11", w: 1 },
    { label: "F12", w: 1 },
    { label: "Mode", w: 1 },
    { label: "Prt\nSc", w: 1 },
    { label: "Pause", w: 1 },
  ],
  [
    { label: "`\n~", w: 1 },
    { label: "1\n!", w: 1 },
    { label: "2\n@", w: 1 },
    { label: "3\n#", w: 1 },
    { label: "4\n$", w: 1 },
    { label: "5\n%", w: 1 },
    { label: "6\n^", w: 1 },
    { label: "7\n&", w: 1 },
    { label: "8\n*", w: 1 },
    { label: "9\n(", w: 1 },
    { label: "0\n)", w: 1 },
    { label: "-\n_", w: 1 },
    { label: "=\n+", w: 1 },
    { label: "Backspace", w: 2 },
    { label: "Ins", w: 1 },
    { label: "Pg\nUp", w: 1 },
  ],
  [
    { label: "Tab", w: 1.5 },
    { label: "Q", w: 1 },
    { label: "W", w: 1 },
    { label: "E", w: 1 },
    { label: "R", w: 1 },
    { label: "T", w: 1 },
    { label: "Y", w: 1 },
    { label: "U", w: 1 },
    { label: "I", w: 1 },
    { label: "O", w: 1 },
    { label: "P", w: 1 },
    { label: "[", w: 1 },
    { label: "]", w: 1 },
    { label: "\\", w: 1.5 },
    { label: "Del", w: 1 },
    { label: "Pg\nDn", w: 1 },
  ],
  [
    { label: "Caps\nLock", w: 1.75 },
    { label: "A", w: 1 },
    { label: "S", w: 1 },
    { label: "D", w: 1 },
    { label: "F", w: 1 },
    { label: "G", w: 1 },
    { label: "H", w: 1 },
    { label: "J", w: 1 },
    { label: "K", w: 1 },
    { label: "L", w: 1 },
    { label: ";\n:", w: 1 },
    { label: "'\n\"", w: 1 },
    { label: "Enter", w: 2.25 },
    { label: "", w: 1 },
    { label: "", w: 1 },
  ],
  [
    { label: "Shift", w: 2.25 },
    { label: "Z", w: 1 },
    { label: "X", w: 1 },
    { label: "C", w: 1 },
    { label: "V", w: 1 },
    { label: "B", w: 1 },
    { label: "N", w: 1 },
    { label: "M", w: 1 },
    { label: ",\n<", w: 1 },
    { label: ".\n>", w: 1 },
    { label: "/\n?", w: 1 },
    { label: "Shift", w: 2.75 },
    { label: "↑", w: 1 },
    { label: "", w: 1 },
  ],
  [
    { label: "Ctrl", w: 1.25 },
    { label: "Win", w: 1.25 },
    { label: "Alt", w: 1.25 },
    { label: "", w: 6.25 },
    { label: "Alt", w: 1.25 },
    { label: "Fn", w: 1.25 },
    { label: "Ctrl", w: 1.25 },
    { label: "←", w: 1 },
    { label: "↓", w: 1 },
    { label: "→", w: 1 },
  ],
];

const UNIT = 1;
const GAP = 0.15;
const KEY_HEIGHT = 0.45;

const totalWidth =
  Math.max(...layout.map((row) => row.reduce((a, key) => a + key.w, 0))) * (UNIT + GAP) - GAP;
const totalHeight = layout.length * (UNIT + GAP) - GAP;

const frameGeometry = new THREE.BoxGeometry(totalWidth + 1.4, 0.8, totalHeight + 1.2);
const frameMaterial = new THREE.MeshStandardMaterial({ color: "#1c1c1f", roughness: 0.6 });
const frame = new THREE.Mesh(frameGeometry, frameMaterial);
frame.position.y = -0.2;
keyboardGroup.add(frame);

const keycaps = [];

const textureCanvas = document.createElement("canvas");
textureCanvas.width = 1024;
textureCanvas.height = 512;
const textureContext = textureCanvas.getContext("2d");

const texture = new THREE.CanvasTexture(textureCanvas);
texture.colorSpace = THREE.SRGBColorSpace;
texture.anisotropy = 8;
texture.wrapS = THREE.ClampToEdgeWrapping;
texture.wrapT = THREE.ClampToEdgeWrapping;

function setCanvasDefault() {
  textureContext.fillStyle = "#1f1f27";
  textureContext.fillRect(0, 0, textureCanvas.width, textureCanvas.height);
}

setCanvasDefault();

const topMaterial = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.35 });
const sideMaterial = new THREE.MeshStandardMaterial({ color: "#26262f", roughness: 0.5 });
const keyMaterials = [sideMaterial, sideMaterial, topMaterial, sideMaterial, sideMaterial, sideMaterial];

function createLabelSprite(text, width, height) {
  if (!text) return null;

  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(255, 255, 255, 0.85)";
  context.font = "500 24px Inter, sans-serif";
  context.textAlign = "left";
  context.textBaseline = "top";

  const lines = text.split("\n");
  const lineHeight = 26;
  const paddingX = 36;
  const paddingY = 32;
  lines.forEach((line, index) => {
    context.fillText(line, paddingX, paddingY + index * lineHeight);
  });

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(width * 0.7, height * 0.7, 1);
  return sprite;
}

function createKeycap(width, height, x, z, label) {
  const geometry = new THREE.BoxGeometry(width, KEY_HEIGHT, height);
  geometry.translate(0, KEY_HEIGHT / 2, 0);

  const uMin = x / totalWidth;
  const uMax = (x + width) / totalWidth;
  const vMin = z / totalHeight;
  const vMax = (z + height) / totalHeight;

  const uv = geometry.attributes.uv;

  uv.setXY(8, uMin, 1 - vMin);
  uv.setXY(9, uMax, 1 - vMin);
  uv.setXY(10, uMin, 1 - vMax);
  uv.setXY(11, uMax, 1 - vMax);
  uv.needsUpdate = true;

  const mesh = new THREE.Mesh(geometry, keyMaterials);
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  mesh.position.set(x - totalWidth / 2 + width / 2, 0, z - totalHeight / 2 + height / 2);
  keyboardGroup.add(mesh);
  keycaps.push(mesh);

  const labelSprite = createLabelSprite(label, width, height);
  if (labelSprite) {
    labelSprite.position.set(mesh.position.x - width * 0.2, KEY_HEIGHT + 0.02, mesh.position.z - height * 0.2);
    keyboardGroup.add(labelSprite);
  }
}

let cursorZ = 0;
layout.forEach((row) => {
  let cursorX = 0;
  row.forEach((key) => {
    const width = key.w * UNIT + (key.w - 1) * GAP;
    const height = UNIT;
    createKeycap(width, height, cursorX, cursorZ, key.label);
    cursorX += width + GAP;
  });
  cursorZ += UNIT + GAP;
});

const frameColorInput = document.getElementById("frameColor");
frameColorInput.addEventListener("input", (event) => {
  frameMaterial.color.set(event.target.value);
});

const sliders = {
  zoom: document.getElementById("zoom"),
  offsetX: document.getElementById("offsetX"),
  offsetY: document.getElementById("offsetY"),
  brightness: document.getElementById("brightness"),
  contrast: document.getElementById("contrast"),
  saturation: document.getElementById("saturation"),
  hue: document.getElementById("hue"),
};

let uploadedImage = null;

function drawTexture() {
  setCanvasDefault();
  if (!uploadedImage) {
    texture.needsUpdate = true;
    return;
  }

  const zoom = parseFloat(sliders.zoom.value);
  const offsetX = parseFloat(sliders.offsetX.value);
  const offsetY = parseFloat(sliders.offsetY.value);
  const brightness = parseFloat(sliders.brightness.value);
  const contrast = parseFloat(sliders.contrast.value);
  const saturation = parseFloat(sliders.saturation.value);
  const hue = parseFloat(sliders.hue.value);

  const canvasWidth = textureCanvas.width;
  const canvasHeight = textureCanvas.height;

  const baseScale = Math.max(
    canvasWidth / uploadedImage.width,
    canvasHeight / uploadedImage.height
  );
  const scale = baseScale * zoom;
  const drawWidth = uploadedImage.width * scale;
  const drawHeight = uploadedImage.height * scale;

  const centerX = canvasWidth / 2 + offsetX * canvasWidth;
  const centerY = canvasHeight / 2 + offsetY * canvasHeight;

  textureContext.save();
  textureContext.filter = `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%) hue-rotate(${hue}deg)`;
  textureContext.drawImage(
    uploadedImage,
    centerX - drawWidth / 2,
    centerY - drawHeight / 2,
    drawWidth,
    drawHeight
  );
  textureContext.restore();

  texture.needsUpdate = true;
}

Object.values(sliders).forEach((slider) => {
  slider.addEventListener("input", drawTexture);
});

const uploader = document.getElementById("imageUpload");
const clearButton = document.getElementById("clearImage");

uploader.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const image = new Image();
  image.onload = () => {
    uploadedImage = image;
    drawTexture();
  };
  image.src = URL.createObjectURL(file);
});

clearButton.addEventListener("click", () => {
  uploadedImage = null;
  uploader.value = "";
  drawTexture();
});

const resetView = document.getElementById("resetView");
resetView.addEventListener("click", () => {
  controls.reset();
  camera.position.set(0, 6.5, 16.5);
  controls.target.set(0, 1, 0);
});

function resizeRenderer() {
  const { clientWidth, clientHeight } = canvas;
  renderer.setSize(clientWidth, clientHeight, false);
  camera.aspect = clientWidth / clientHeight;
  camera.updateProjectionMatrix();
}

window.addEventListener("resize", resizeRenderer);

function animate() {
  controls.update();
  cameraLight.position.copy(camera.position);
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

resizeRenderer();
animate();
