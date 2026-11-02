
<template>
  <div class="profile-page">
    <div class="page-heading">
      <h2>My Profile</h2>
      <p>Manage your personal account information.</p>
    </div>

    <section class="profile-card">
      <div class="avatar">
        <img
          v-if="profilePicture"
          :src="profilePicture"
          alt="Your profile picture"
        />
        <span v-else>{{ initials }}</span>
      </div>

      <div class="profile-heading">
        <h3>{{ form.name || "Your name" }}</h3>
        <p>{{ email || "Loading account details..." }}</p>
      </div>

      <div class="photo-actions">
        <input
          ref="fileInput"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          class="file-input"
          @change="handlePictureSelection"
        />

        <button
          type="button"
          class="secondary-button"
          :disabled="uploading || initialLoading"
          @click="fileInput?.click()"
        >
          {{ profilePicture ? "Change picture" : "Upload picture" }}
        </button>

        <small>JPEG, PNG or WebP. Maximum size: 5 MB.</small>
      </div>

      <div class="divider"></div>

      <form @submit.prevent="saveProfile">
        <div class="form-group">
          <label for="profile-name">Full name</label>
          <input
            id="profile-name"
            v-model="form.name"
            type="text"
            maxlength="150"
            autocomplete="name"
            placeholder="Enter your name"
            required
          />
        </div>

        <div class="form-group">
          <label for="profile-email">Email address</label>
          <input
            id="profile-email"
            :value="email"
            type="email"
            disabled
          />
          <small>
            Email changes will be available after we implement email verification.
          </small>
        </div>

        <div class="divider"></div>

        <div class="preferences-heading">
          <h3>Investment preferences</h3>
          <p>
            Personalise your stock-market analysis and recommendations.
          </p>
        </div>

        <div class="form-group">
          <label for="preferred-market">Preferred market</label>
          <select
            id="preferred-market"
            v-model="form.preferred_market"
          >
            <option value="global">Global markets</option>
            <option value="us">United States</option>
            <option value="uk">United Kingdom</option>
            <option value="pakistan">Pakistan</option>
          </select>
          <small>
            Choose the market you want to focus on.
          </small>
        </div>

        <div class="form-group">
          <label for="risk-tolerance">Risk tolerance</label>
          <select
            id="risk-tolerance"
            v-model="form.risk_tolerance"
          >
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
          <small>
            Select the level of investment risk you are comfortable with.
          </small>
        </div>

        <div class="form-group">
          <label for="investment-horizon">Investment horizon</label>
          <select
            id="investment-horizon"
            v-model="form.investment_horizon"
          >
            <option value="short">Short-term</option>
            <option value="medium">Medium-term</option>
            <option value="long">Long-term</option>
          </select>
          <small>
            Choose your intended investment timeframe.
          </small>
        </div>

        <div class="form-group">
          <span class="field-label">Preferred sectors</span>
          <p class="field-description">
            Select the sectors you want to follow. You can choose multiple
            sectors or leave them all unselected.
          </p>

          <div class="sector-options">
            <label
              v-for="sector in availableSectors"
              :key="sector"
              class="sector-option"
            >
              <input
                v-model="form.preferred_sectors"
                type="checkbox"
                :value="sector"
              />
              <span>{{ sector }}</span>
            </label>
          </div>
        </div>

        <p v-if="successMessage" class="success-message">
          {{ successMessage }}
        </p>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <button type="submit" :disabled="loading || initialLoading">
          {{ loading ? "Saving..." : "Save changes" }}
        </button>
      </form>
    </section>

    <!-- Custom image crop editor; does not depend on Cropper.js -->
    <div
      v-if="cropOpen"
      class="crop-overlay"
      @click.self="cancelCrop"
      @keydown.esc="cancelCrop"
    >
      <section
        class="crop-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="crop-title"
      >
        <div class="crop-header">
          <div>
            <h3 id="crop-title">Adjust profile picture</h3>
            <p>Drag the image to choose the portion you want.</p>
          </div>

          <button
            type="button"
            class="close-button"
            aria-label="Close crop editor"
            @click="cancelCrop"
          >
            &times;
          </button>
        </div>

        <div
          ref="cropWorkspace"
          class="crop-workspace"
          @pointerdown="startDrag"
          @pointermove="moveDrag"
          @pointerup="endDrag"
          @pointercancel="endDrag"
          @wheel.prevent="zoomWithWheel"
        >
          <img
            v-if="cropSource"
            ref="cropImage"
            :src="cropSource"
            class="crop-image"
            alt="Image being cropped"
            draggable="false"
            @load="initializeCrop"
            @error="handleCropImageError"
          />

          <div v-if="!cropperReady" class="crop-loading">
            Preparing image...
          </div>
        </div>

        <div class="crop-preview-row">
          <div>
            <strong>Profile preview</strong>
            <p>This is how your picture will appear.</p>
          </div>

          <div class="crop-circle-preview">
            <img
              v-if="cropPreview"
              :src="cropPreview"
              alt="Cropped profile preview"
            />
            <span v-else>Preview</span>
          </div>
        </div>

        <label class="zoom-control" for="crop-zoom">
          <span>Zoom</span>
          <input
            id="crop-zoom"
            v-model.number="zoomLevel"
            type="range"
            min="0"
            max="100"
            step="1"
            :disabled="!cropperReady"
            @input="applyZoom"
          />
          <span class="zoom-value">{{ zoomLevel }}%</span>
        </label>

        <p v-if="cropError" class="error-message">
          {{ cropError }}
        </p>

        <div class="crop-actions">
          <button
            type="button"
            class="secondary-button"
            :disabled="uploading"
            @click="cancelCrop"
          >
            Cancel
          </button>

          <button
            type="button"
            :disabled="uploading || !cropperReady || !cropPreview"
            @click="saveCroppedPicture"
          >
            {{ uploading ? "Uploading..." : "Save picture" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
} from "vue";

import {
  getCurrentUser,
  updateProfile,
  uploadProfilePicture,
} from "../services/api";

const availableSectors = [
  "Technology",
  "Healthcare",
  "Finance",
  "Energy",
  "Consumer",
  "Industrials",
  "Real Estate",
  "Utilities",
  "Materials",
  "Communication Services",
];

const form = reactive({
  name: "",
  preferred_market: "global",
  risk_tolerance: "moderate",
  investment_horizon: "medium",
  preferred_sectors: [],
});

const email = ref("");
const profilePicture = ref(null);
const fileInput = ref(null);

const loading = ref(false);
const uploading = ref(false);
const initialLoading = ref(true);
const successMessage = ref("");
const errorMessage = ref("");

const cropOpen = ref(false);
const cropSource = ref("");
const cropImage = ref(null);
const cropWorkspace = ref(null);
const cropPreview = ref("");
const cropError = ref("");
const zoomLevel = ref(0);
const cropperReady = ref(false);

let cropObjectUrl = null;
let baseScale = 1;
let imageScale = 1;
let imageOffsetX = 0;
let imageOffsetY = 0;
let workspaceSize = 0;

let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let dragOriginX = 0;
let dragOriginY = 0;

const initials = computed(() => {
  const name = form.name.trim();

  if (!name) return "U";

  return name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
});

// Retained from the existing cropper implementation.
// The cropper image's position is controlled by updateCropImageStyle().
const imageStyle = computed(() => {
  if (!cropImage.value) return {};

  return {
    width: `${cropImage.value.naturalWidth * imageScale}px`,
    height: `${cropImage.value.naturalHeight * imageScale}px`,
    left: `${imageOffsetX}px`,
    top: `${imageOffsetY}px`,
  };
});

function applyUser(user) {
  form.name = user.name || user.first_name || "";
  email.value = user.email || "";
  profilePicture.value = user.profile_picture || null;

  form.preferred_market = user.preferred_market || "global";
  form.risk_tolerance = user.risk_tolerance || "moderate";
  form.investment_horizon = user.investment_horizon || "medium";

  form.preferred_sectors = Array.isArray(user.preferred_sectors)
    ? [...user.preferred_sectors]
    : [];
}

onMounted(async () => {
  try {
    const response = await getCurrentUser();
    applyUser(response.user);
  } catch {
    errorMessage.value = "Unable to load your profile. Please log in again.";
  } finally {
    initialLoading.value = false;
  }
});

async function saveProfile() {
  successMessage.value = "";
  errorMessage.value = "";

  const name = form.name.trim();

  if (!name) {
    errorMessage.value = "Please enter your name.";
    return;
  }

  loading.value = true;

  try {
    const response = await updateProfile({
      name,
      preferred_market: form.preferred_market,
      risk_tolerance: form.risk_tolerance,
      investment_horizon: form.investment_horizon,
      preferred_sectors: [...form.preferred_sectors],
    });

    applyUser(response.user);
    successMessage.value = "Your profile has been updated.";
  } catch (error) {
    const data = error.response?.data;

    if (data && typeof data === "object") {
      const messages = Object.entries(data).flatMap(([field, value]) => {
        const label = field.replaceAll("_", " ");

        if (Array.isArray(value)) {
          return value.map((message) => `${label}: ${message}`);
        }

        if (typeof value === "string") {
          return [`${label}: ${value}`];
        }

        return [];
      });

      errorMessage.value =
        messages.join(" ") ||
        "Unable to save your profile. Please try again.";
    } else {
      errorMessage.value =
        "Unable to save your profile. Please try again.";
    }
  } finally {
    loading.value = false;
  }
}

function handlePictureSelection(event) {
  const file = event.target.files?.[0];

  if (!file) return;

  successMessage.value = "";
  errorMessage.value = "";
  cropError.value = "";

  const allowedTypes = ["image/jpeg", "image/png", "image/webp"];

  if (!allowedTypes.includes(file.type)) {
    errorMessage.value = "Please select a JPEG, PNG or WebP image.";
    event.target.value = "";
    return;
  }

  if (file.size > 5 * 1024 * 1024) {
    errorMessage.value = "The image must be 5 MB or smaller.";
    event.target.value = "";
    return;
  }

  releaseCropObjectUrl();

  cropObjectUrl = URL.createObjectURL(file);
  cropSource.value = cropObjectUrl;
  cropPreview.value = "";
  zoomLevel.value = 0;
  cropperReady.value = false;
  workspaceSize = 0;

  cropOpen.value = true;

  // Allow selecting the same file again.
  event.target.value = "";
}

async function initializeCrop() {
  await nextTick();

  const image = cropImage.value;
  const workspace = cropWorkspace.value;

  if (!image || !workspace || !image.naturalWidth || !image.naturalHeight) {
    cropError.value = "Unable to load this image. Please select another one.";
    return;
  }

  workspaceSize = workspace.clientWidth;

  if (!workspaceSize) {
    cropError.value = "Unable to prepare the crop area. Please try again.";
    return;
  }

  // Fit the whole image to cover the square crop area.
  baseScale = Math.max(
    workspaceSize / image.naturalWidth,
    workspaceSize / image.naturalHeight,
  );

  imageScale = baseScale;
  imageOffsetX =
    (workspaceSize - image.naturalWidth * imageScale) / 2;
  imageOffsetY =
    (workspaceSize - image.naturalHeight * imageScale) / 2;

  zoomLevel.value = 0;
  clampImagePosition();
  updateCropImageStyle();

  cropperReady.value = true;
  refreshCropPreview();
}

function updateCropImageStyle() {
  const image = cropImage.value;

  if (!image || !workspaceSize) return;

  image.style.position = "absolute";
  image.style.display = "block";
  image.style.maxWidth = "none";
  image.style.maxHeight = "none";
  image.style.width = `${image.naturalWidth * imageScale}px`;
  image.style.height = `${image.naturalHeight * imageScale}px`;
  image.style.left = `${imageOffsetX}px`;
  image.style.top = `${imageOffsetY}px`;
  image.style.transform = "none";
}

function handleCropImageError() {
  cropperReady.value = false;
  cropError.value = "Unable to load this image. Please select another one.";
}

function clampImagePosition() {
  if (!cropImage.value || !workspaceSize) return;

  const renderedWidth = cropImage.value.naturalWidth * imageScale;
  const renderedHeight = cropImage.value.naturalHeight * imageScale;

  // Keep the image covering the entire square crop window.
  imageOffsetX = Math.min(
    0,
    Math.max(workspaceSize - renderedWidth, imageOffsetX),
  );

  imageOffsetY = Math.min(
    0,
    Math.max(workspaceSize - renderedHeight, imageOffsetY),
  );
}

function startDrag(event) {
  if (!cropperReady.value || event.button !== 0) return;

  isDragging = true;
  dragStartX = event.clientX;
  dragStartY = event.clientY;
  dragOriginX = imageOffsetX;
  dragOriginY = imageOffsetY;

  event.currentTarget.setPointerCapture(event.pointerId);
}

function moveDrag(event) {
  if (!isDragging || !cropperReady.value) return;

  const deltaX = event.clientX - dragStartX;
  const deltaY = event.clientY - dragStartY;

  imageOffsetX = dragOriginX + deltaX;
  imageOffsetY = dragOriginY + deltaY;

  clampImagePosition();
  updateCropImageStyle();
  refreshCropPreview();
}

function endDrag() {
  isDragging = false;
}

function applyZoom() {
  if (!cropperReady.value || !cropImage.value) return;

  const oldScale = imageScale;
  const newScale = baseScale * (1 + (zoomLevel.value / 100) * 2.5);
  const center = workspaceSize / 2;

  // Keep the same point of the image under the crop area's center.
  const sourceCenterX = (center - imageOffsetX) / oldScale;
  const sourceCenterY = (center - imageOffsetY) / oldScale;

  imageScale = newScale;
  imageOffsetX = center - sourceCenterX * newScale;
  imageOffsetY = center - sourceCenterY * newScale;

  clampImagePosition();
  updateCropImageStyle();
  refreshCropPreview();
}

function zoomWithWheel(event) {
  if (!cropperReady.value) return;

  const change = event.deltaY < 0 ? 5 : -5;

  zoomLevel.value = Math.max(
    0,
    Math.min(100, zoomLevel.value + change),
  );

  applyZoom();
}

function refreshCropPreview() {
  const image = cropImage.value;

  if (!image || !cropperReady.value || !workspaceSize || !imageScale) {
    cropPreview.value = "";
    return;
  }

  try {
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 400;

    const context = canvas.getContext("2d");

    if (!context) {
      cropPreview.value = "";
      return;
    }

    const sourceX = Math.max(0, -imageOffsetX / imageScale);
    const sourceY = Math.max(0, -imageOffsetY / imageScale);
    const sourceSize = workspaceSize / imageScale;

    context.drawImage(
      image,
      sourceX,
      sourceY,
      sourceSize,
      sourceSize,
      0,
      0,
      canvas.width,
      canvas.height,
    );

    cropPreview.value = canvas.toDataURL("image/jpeg", 0.92);
  } catch (error) {
    console.error("Unable to generate crop preview:", error);
    cropPreview.value = "";
    cropError.value =
      "Unable to generate the preview. Please try another image.";
  }
}

async function saveCroppedPicture() {
  if (!cropperReady.value || !cropImage.value || !cropPreview.value) {
    cropError.value = "Please wait until the image editor is ready.";
    return;
  }

  cropError.value = "";
  successMessage.value = "";
  errorMessage.value = "";
  uploading.value = true;

  try {
    const image = cropImage.value;
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 400;

    const context = canvas.getContext("2d");

    if (!context) {
      throw new Error("Unable to create the cropped image.");
    }

    const sourceX = Math.max(0, -imageOffsetX / imageScale);
    const sourceY = Math.max(0, -imageOffsetY / imageScale);
    const sourceSize = workspaceSize / imageScale;

    context.drawImage(
      image,
      sourceX,
      sourceY,
      sourceSize,
      sourceSize,
      0,
      0,
      canvas.width,
      canvas.height,
    );

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(
        (result) => {
          if (result) {
            resolve(result);
          } else {
            reject(new Error("Image conversion failed."));
          }
        },
        "image/jpeg",
        0.92,
      );
    });

    const croppedFile = new File(
      [blob],
      "profile-picture-cropped.jpg",
      { type: "image/jpeg" },
    );

    const response = await uploadProfilePicture(croppedFile);

    applyUser(response.user);
    successMessage.value = "Your cropped profile picture has been saved.";
    cancelCrop();
  } catch (error) {
    console.error("Profile picture upload failed:", error);

    const data = error.response?.data;
    const pictureError = data?.profile_picture;

    cropError.value = Array.isArray(pictureError)
      ? pictureError.join(" ")
      : pictureError ||
        data?.detail ||
        "Unable to upload your picture. Please try again.";
  } finally {
    uploading.value = false;
  }
}

function releaseCropObjectUrl() {
  if (cropObjectUrl) {
    URL.revokeObjectURL(cropObjectUrl);
    cropObjectUrl = null;
  }
}

function cancelCrop() {
  cropOpen.value = false;
  cropSource.value = "";
  cropPreview.value = "";
  cropError.value = "";
  cropperReady.value = false;
  isDragging = false;
  releaseCropObjectUrl();
}

onBeforeUnmount(() => {
  releaseCropObjectUrl();
});
</script>

<style scoped>
.profile-page {
  max-width: 760px;
  margin: 0 auto;
  color: #111827;
}

.page-heading {
  margin-bottom: 24px;
}

.page-heading h2 {
  margin: 0 0 8px;
  font-size: 26px;
}

.page-heading p,
.profile-heading p {
  color: #6b7280;
  margin: 0;
}

.profile-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 28px;
  box-shadow: 0 4px 16px rgb(17 24 39 / 4%);
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  overflow: hidden;
  border-radius: 50%;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 28px;
  font-weight: 700;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-heading {
  margin: 16px 0;
}

.profile-heading h3 {
  margin: 0 0 6px;
  font-size: 20px;
}

.photo-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 24px;
}

.file-input {
  display: none;
}

.photo-actions small,
.form-group small {
  color: #6b7280;
  font-size: 12px;
}

.divider {
  height: 1px;
  background: #e5e7eb;
  margin-bottom: 24px;
}

.preferences-heading {
  margin-bottom: 24px;
}

.preferences-heading h3 {
  margin: 0 0 8px;
  font-size: 18px;
}

.preferences-heading p,
.field-description {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.form-group > label,
.field-label {
  font-size: 14px;
  font-weight: 600;
}

.form-group input,
.form-group select {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font: inherit;
}

.form-group input:focus,
.form-group select:focus {
  outline: 2px solid #93c5fd;
  border-color: #2563eb;
}

.form-group input:disabled {
  background: #f3f4f6;
  color: #6b7280;
}

.sector-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 4px;
}

.sector-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 400;
}

.sector-option:has(input:checked) {
  border-color: #93c5fd;
  background: #eff6ff;
}

.sector-option input {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin: 0;
  accent-color: #2563eb;
}

.sector-option span {
  overflow-wrap: anywhere;
}

button {
  padding: 12px 18px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

button:hover {
  background: #1d4ed8;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-button {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
}

.secondary-button:hover {
  background: #dbeafe;
}

.success-message {
  color: #15803d;
  margin-bottom: 16px;
}

.error-message {
  color: #b91c1c;
  margin-bottom: 16px;
  overflow-wrap: anywhere;
}

/* Crop editor */
.crop-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow-y: auto;
  padding: 20px;
  background: rgb(15 23 42 / 65%);
}

.crop-modal {
  width: min(100%, 600px);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  padding: 24px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 24px 80px rgb(0 0 0 / 25%);
}

.crop-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.crop-header h3 {
  margin: 0 0 6px;
  font-size: 20px;
}

.crop-header p,
.crop-preview-row p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.5;
}

.close-button {
  flex-shrink: 0;
  padding: 2px 8px;
  background: transparent;
  color: #6b7280;
  font-size: 28px;
  line-height: 1.2;
}

.close-button:hover {
  background: #f3f4f6;
  color: #111827;
}

/* The cropping window is square, so the crop and preview match exactly. */
.crop-workspace {
  position: relative;
  width: min(100%, 360px);
  aspect-ratio: 1;
  margin: 0 auto;
  overflow: hidden;
  border-radius: 10px;
  background: #111827;
  cursor: grab;
  touch-action: none;
  user-select: none;
}

.crop-workspace:active {
  cursor: grabbing;
}

.crop-image {
  position: absolute;
  display: block;
  max-width: none !important;
  max-height: none !important;
  object-fit: fill;
  margin: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  transform: none !important;
  pointer-events: none;
  user-select: none;
}

.crop-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: rgb(17 24 39 / 70%);
  pointer-events: none;
}

.crop-preview-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin: 20px 0;
}

.crop-preview-row strong {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
}

.crop-circle-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  flex-shrink: 0;
  overflow: hidden;
  border: 2px solid #dbeafe;
  border-radius: 50%;
  background: #eff6ff;
  color: #6b7280;
  font-size: 11px;
}

.crop-circle-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.zoom-control {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  margin: 20px 0;
  font-size: 14px;
  font-weight: 600;
}

.zoom-control input {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
}

.zoom-value {
  min-width: 40px;
  color: #6b7280;
  text-align: right;
  font-weight: 400;
}

.crop-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.crop-actions .secondary-button {
  background: #f9fafb;
  color: #374151;
  border-color: #d1d5db;
}

.crop-actions .secondary-button:hover {
  background: #f3f4f6;
}

@media (max-width: 640px) {
  .profile-card {
    padding: 20px;
  }

  .sector-options {
    grid-template-columns: 1fr;
  }

  .crop-overlay {
    padding: 10px;
  }

  .crop-modal {
    padding: 18px;
    max-height: calc(100vh - 20px);
  }

  .crop-actions button {
    flex: 1;
  }
}
</style>
