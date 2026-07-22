import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin } from '@pixiv/three-vrm';
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from '@pixiv/three-vrm-animation';

import { MascotState, MascotStateMachine } from './state-machine.js';

const bridge = window.webkit?.messageHandlers?.mascot;
const post = (type, payload = {}) => bridge?.postMessage({ type, ...payload });
window.addEventListener('error', (event) => {
  post('error', { message: event.error?.message ?? event.message });
});
window.addEventListener('unhandledrejection', (event) => {
  post('error', { message: event.reason?.message ?? String(event.reason) });
});
post('diagnostic', { message: 'script-started' });
const status = document.getElementById('status');
const canvas = document.getElementById('stage');
const machine = new MascotStateMachine();

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xeeeeee);
scene.add(new THREE.HemisphereLight(0xffffff, 0x888888, 1.5));
const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
keyLight.position.set(2, 3, 4);
scene.add(keyLight);

const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 20);
camera.position.set(0, 1.25, 3.2);
camera.lookAt(0, 1.05, 0);

let vrm = null;
let mixer = null;
let idleAction = null;
let animationFrame = null;
let lastFrameTime = performance.now();

function resize() {
  const width = window.innerWidth;
  const height = window.innerHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

function render(time) {
  const delta = Math.min((time - lastFrameTime) / 1000, 0.1);
  lastFrameTime = time;
  mixer?.update(delta);
  vrm?.update(delta);
  renderer.render(scene, camera);
  animationFrame = requestAnimationFrame(render);
}

function startRendering() {
  if (animationFrame !== null) return;
  lastFrameTime = performance.now();
  animationFrame = requestAnimationFrame(render);
}

function stopRendering() {
  if (animationFrame === null) return;
  cancelAnimationFrame(animationFrame);
  animationFrame = null;
}

async function loadGLTF(url, configure) {
  const loader = new GLTFLoader();
  configure(loader);
  return loader.loadAsync(url);
}

async function boot() {
  try {
    post('diagnostic', { message: 'boot-started' });
    const vrmGLTF = await loadGLTF('./model.vrm', (loader) => {
      loader.register((parser) => new VRMLoaderPlugin(parser));
    });
    post('diagnostic', { message: 'model-loaded' });
    vrm = vrmGLTF.userData.vrm;
    vrm.scene.rotation.y = Math.PI;
    scene.add(vrm.scene);
    mixer = new THREE.AnimationMixer(vrm.scene);

    const animationGLTF = await loadGLTF('./idle.vrma', (loader) => {
      loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
    });
    post('diagnostic', { message: 'idle-loaded' });
    const vrmAnimation = animationGLTF.userData.vrmAnimations?.[0];
    if (!vrmAnimation) throw new Error('idle.vrma にVRM Animationがありません');
    const clip = createVRMAnimationClip(vrmAnimation, vrm);
    idleAction = mixer.clipAction(clip);
    idleAction.play();

    machine.transition(MascotState.IDLE);
    status.hidden = true;
    startRendering();
    post('ready');
  } catch (error) {
    machine.transition(MascotState.ERROR);
    status.textContent = '読み込みに失敗しました';
    post('error', { message: error instanceof Error ? error.message : String(error) });
  }
}

window.mascotApp = {
  suspend() {
    machine.transition(MascotState.SUSPENDED);
    if (idleAction) idleAction.paused = true;
    stopRendering();
  },
  resume() {
    machine.transition(MascotState.IDLE);
    if (idleAction) idleAction.paused = false;
    startRendering();
  },
};

window.addEventListener('resize', resize);
resize();
boot();
