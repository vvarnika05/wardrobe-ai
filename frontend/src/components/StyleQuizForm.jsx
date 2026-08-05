import { useState } from "react";
import { createProfile } from "../api/client";

const COLOR_OPTIONS = [
  "black",
  "white",
  "beige",
  "navy",
  "grey",
  "brown",
  "olive",
  "red",
  "blue",
];

const FIT_OPTIONS = ["relaxed", "fitted", "oversized", "tailored"];
const SLEEVE_OPTIONS = ["long", "short", "sleeveless", "varies"];

/**
 * Form fields match backend ProfileCreate.
 * Visual-only: chips for colors, dark-themed inputs — logic unchanged.
 */
export default function StyleQuizForm({
  onSuccess,
  onCancel,
  initialValues = null,
  apiSubmit = createProfile,
  submitLabel = "Open my edit",
}) {
  const [styleDescription, setStyleDescription] = useState(
    initialValues?.style_description || ""
  );
  const [colorPrefs, setColorPrefs] = useState(
    initialValues?.color_prefs || []
  );
  const [fitPref, setFitPref] = useState(initialValues?.fit_pref || "relaxed");
  const [sleevePref, setSleevePref] = useState(
    initialValues?.sleeve_pref || "long"
  );
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function toggleColor(color) {
    setColorPrefs((prev) =>
      prev.includes(color) ? prev.filter((c) => c !== color) : [...prev, color]
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!styleDescription.trim()) {
      setError("Please describe your style.");
      return;
    }
    if (colorPrefs.length === 0) {
      setError("Pick at least one color preference.");
      return;
    }

    setSubmitting(true);
    try {
      const profile = await apiSubmit({
        style_description: styleDescription.trim(),
        color_prefs: colorPrefs,
        fit_pref: fitPref,
        sleeve_pref: sleevePref,
      });
      onSuccess?.(profile);
    } catch (err) {
      setError(err.message || "Failed to save profile");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="style-quiz" onSubmit={handleSubmit}>
      <div className="quiz-field">
        <label className="quiz-field__label" htmlFor="style_description">
          Describe your style
        </label>
        <textarea
          id="style_description"
          className="quiz-textarea"
          value={styleDescription}
          onChange={(e) => setStyleDescription(e.target.value)}
          placeholder="e.g. Clean minimalist looks, mostly neutrals, nothing too formal"
          required
        />
      </div>

      <div className="quiz-field">
        <span className="quiz-field__label">Color preferences</span>
        <div className="color-chip-row" role="group" aria-label="Color preferences">
          {COLOR_OPTIONS.map((color) => {
            const selected = colorPrefs.includes(color);
            return (
              <button
                key={color}
                type="button"
                className={
                  selected
                    ? "color-chip color-chip--selected"
                    : "color-chip"
                }
                aria-pressed={selected}
                onClick={() => toggleColor(color)}
              >
                {color}
              </button>
            );
          })}
        </div>
      </div>

      <div className="quiz-field">
        <label className="quiz-field__label" htmlFor="fit_pref">
          Fit preference
        </label>
        <select
          id="fit_pref"
          className="quiz-select"
          value={fitPref}
          onChange={(e) => setFitPref(e.target.value)}
        >
          {FIT_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>

      <div className="quiz-field">
        <label className="quiz-field__label" htmlFor="sleeve_pref">
          Sleeve preference
        </label>
        <select
          id="sleeve_pref"
          className="quiz-select"
          value={sleevePref}
          onChange={(e) => setSleevePref(e.target.value)}
        >
          {SLEEVE_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>

      {error && <p className="auth-error">{error}</p>}

      <div className="form-actions">
        <button className="auth-submit" type="submit" disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="text-link" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
