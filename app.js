import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const canvas = document.getElementById("scene");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(canvas.clientWidth, canvas.clientHeight);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog("#0b0b0d", 10, 30);

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

const ambient = new THREE.AmbientLight("#ffffff", 0.7);
scene.add(ambient);

const keyLight = new THREE.DirectionalLight("#ffffff", 0.9);
keyLight.position.set(6, 10, 6);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight("#ff99aa", 0.35);
fillLight.position.set(-6, 4, -6);
scene.add(fillLight);

const keyboardGroup = new THREE.Group();
scene.add(keyboardGroup);

const layout = [
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.5],
  [1.5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.75],
  [1.75, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2.25],
  [2.25, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2.75],
  [2.75, 1, 1, 1, 1, 1, 1, 1, 1, 2.75],
];

const UNIT = 1;
const GAP = 0.15;
const KEY_HEIGHT = 0.45;

const totalWidth = Math.max(...layout.map((row) => row.reduce((a, b) => a + b, 0))) * (UNIT + GAP) - GAP;
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

function createKeycap(width, height, x, z) {
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
}

let cursorZ = 0;
layout.forEach((row) => {
  let cursorX = 0;
  row.forEach((keyWidthUnits) => {
    const width = keyWidthUnits * UNIT + (keyWidthUnits - 1) * GAP;
    const height = UNIT;
    createKeycap(width, height, cursorX, cursorZ);
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
  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

resizeRenderer();
animate();
