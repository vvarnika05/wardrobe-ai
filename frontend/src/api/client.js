/**
 * API client — single place for all backend HTTP calls.
 *
 * Why this file exists:
 * - Components should not scatter raw fetch() calls with URLs and auth headers.
 * - If an endpoint path or response shape changes, we update it here once.
 * - JWT attachment and error handling stay consistent across the app.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const TOKEN_KEY = "access_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Low-level request helper.
 * - Prefixes path with VITE_API_BASE_URL
 * - Attaches Authorization: Bearer <token> when a token is stored
 * - Throws Error with the backend's `detail` message when response is not ok
 */
async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const token = getStoredToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Some endpoints (rarely) return empty bodies — handle that safely.
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    // FastAPI usually returns { detail: "..." } or { detail: [validation...] }
    let message = `Request failed (${response.status})`;
    if (data && typeof data === "object" && data.detail !== undefined) {
      message =
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail);
    }
    throw new Error(message);
  }

  return data;
}

export function signup(email, password) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getMe() {
  return request("/auth/me", { method: "GET" });
}

export function createProfile(profileData) {
  // profileData: { style_description, color_prefs, fit_pref, sleeve_pref }
  return request("/profile", {
    method: "POST",
    body: JSON.stringify(profileData),
  });
}

export function getMyProfile() {
  return request("/profile/me", { method: "GET" });
}

/** Same endpoint as createProfile — backend upserts by user. */
export function updateProfile(profileData) {
  return createProfile(profileData);
}

/** GET /saved → list of accepted outfits. */
export function getSavedOutfits() {
  return request("/saved", { method: "GET" });
}

/** GET /recommend → { outfits: [...] } ; returns the outfits array. */
export async function getRecommendations() {
  const data = await request("/recommend", { method: "GET" });
  return data?.outfits ?? [];
}

/** POST /swipe — decision must be "accepted" or "rejected". */
export function submitSwipe(outfitId, decision) {
  return request("/swipe", {
    method: "POST",
    body: JSON.stringify({ outfit_id: outfitId, decision }),
  });
}
