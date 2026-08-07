import { useEffect, useState } from "react";
import { getMyProfile, updateProfile } from "../api/client";
import NavBar from "../components/NavBar";
import StyleQuizForm from "../components/StyleQuizForm";

/** Render values as brand chips; empty → muted italic placeholder. */
function ChipList({ items, emptyLabel = "None yet" }) {
  const list = Array.isArray(items)
    ? items.map((v) => String(v).trim()).filter(Boolean)
    : items
      ? [String(items)]
      : [];

  if (list.length === 0) {
    return <span className="profile-empty">{emptyLabel}</span>;
  }

  return (
    <ul className="brand-chips">
      {list.map((item) => (
        <li key={item} className="brand-chip">
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getMyProfile();
        if (!cancelled) setProfile(data);
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load profile");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleUpdate(formData) {
    setProfile(formData);
    setEditing(false);
  }

  const styleTags =
    profile?.style_tags && typeof profile.style_tags === "object"
      ? profile.style_tags
      : {};

  return (
    <div className="app-shell">
      <NavBar />

      <main className="app-main profile-page">
        <div className="profile-page__header">
          <div>
            <p className="eyebrow">You</p>
            <h1 className="page-title">Profile</h1>
          </div>
          {!loading && !error && profile && !editing && (
            <button
              type="button"
              className="auth-submit"
              onClick={() => setEditing(true)}
            >
              Edit
            </button>
          )}
        </div>

        {loading && <p className="page-sub">Loading profile…</p>}
        {error && <p className="auth-error">{error}</p>}

        {!loading && !error && profile && !editing && (
          <div className="profile-cards">
            <section className="profile-card profile-card--full">
              <h2 className="profile-card__title">Style Note</h2>
              <p className="profile-body">
                {profile.style_description || (
                  <span className="profile-empty">No style note yet</span>
                )}
              </p>
            </section>

            <section className="profile-card">
              <h2 className="profile-card__title">Parsed Tags</h2>
              <div className="profile-grid">
                <div className="profile-field">
                  <h3 className="profile-field__label">Aesthetic</h3>
                  <ChipList items={styleTags.aesthetic} />
                </div>
                <div className="profile-field">
                  <h3 className="profile-field__label">Formality</h3>
                  <ChipList items={styleTags.formality_range} />
                </div>
                <div className="profile-field">
                  <h3 className="profile-field__label">Pattern</h3>
                  <ChipList items={styleTags.pattern_pref} />
                </div>
                <div className="profile-field">
                  <h3 className="profile-field__label">Dominant Colors</h3>
                  <ChipList
                    items={styleTags.dominant_colors}
                    emptyLabel="None detected"
                  />
                </div>
              </div>
            </section>

            <section className="profile-card">
              <h2 className="profile-card__title">Preferences</h2>
              <div className="profile-grid">
                <div className="profile-field">
                  <h3 className="profile-field__label">Clothing to show</h3>
                  <ChipList
                    items={profile.gender_pref}
                    emptyLabel="Not set yet"
                  />
                </div>
                <div className="profile-field">
                  <h3 className="profile-field__label">Colors</h3>
                  <ChipList items={profile.color_prefs} />
                </div>
                <div className="profile-field">
                  <h3 className="profile-field__label">Fit</h3>
                  <ChipList items={profile.fit_pref} />
                </div>
                <div className="profile-field">
                  <h3 className="profile-field__label">Sleeve</h3>
                  <ChipList items={profile.sleeve_pref} />
                </div>
              </div>
            </section>
          </div>
        )}

        {!loading && profile && editing && (
          <>
            <p className="page-sub">
              Update your note — we&apos;ll re-parse with Gemini.
            </p>
            <StyleQuizForm
              initialValues={{
                style_description: profile.style_description || "",
                color_prefs: Array.isArray(profile.color_prefs)
                  ? profile.color_prefs
                  : [],
                fit_pref: profile.fit_pref || "relaxed",
                sleeve_pref: profile.sleeve_pref || "long",
                gender_pref: profile.gender_pref || "",
              }}
              submitLabel="Save changes"
              apiSubmit={updateProfile}
              onSuccess={handleUpdate}
              onCancel={() => setEditing(false)}
            />
          </>
        )}
      </main>
    </div>
  );
}
