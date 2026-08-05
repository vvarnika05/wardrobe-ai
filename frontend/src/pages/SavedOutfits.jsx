import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getSavedOutfits } from "../api/client";
import NavBar from "../components/NavBar";

function formatDate(value) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return String(value);
  }
}

export default function SavedOutfits() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getSavedOutfits();
        if (!cancelled) setItems(Array.isArray(data) ? data : []);
      } catch (err) {
        if (!cancelled) setError(err.message || "Failed to load saved outfits");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-shell">
      <NavBar />

      <main className="app-main">
        <div className="app-main__header">
          <div>
            <p className="eyebrow">Your wardrobe</p>
            <h1 className="page-title">Saved</h1>
          </div>
          <Link to="/swipe" className="auth-submit" style={{ textDecoration: "none" }}>
            New picks
          </Link>
        </div>

        {loading && <p className="page-sub">Loading your saves…</p>}
        {error && <p className="auth-error">{error}</p>}

        {!loading && !error && items.length === 0 && (
          <div className="empty-state">
            <h2 className="page-title" style={{ fontSize: "1.8rem" }}>
              Nothing saved yet
            </h2>
            <p className="page-sub">
              Go find your edit.{" "}
              <Link to="/swipe" className="text-link">
                Open the swipe deck
              </Link>
            </p>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="saved-grid">
            {items.map((item) => (
              <article key={`${item.outfit_id}-${item.swiped_at}`} className="saved-card">
                <div className="saved-card__media">
                  {item.image_url ? (
                    <img src={item.image_url} alt={item.category || "Saved outfit"} />
                  ) : (
                    <div className="saved-card__placeholder">No image</div>
                  )}
                </div>
                <div className="saved-card__body">
                  <h2 className="saved-card__title">{item.category || "Look"}</h2>
                  <p className="saved-card__meta">
                    {item.formality_level || "—"}
                    {Array.isArray(item.color_tags) && item.color_tags.length > 0
                      ? ` · ${item.color_tags.join(", ")}`
                      : ""}
                  </p>
                  <p className="saved-card__date">Saved {formatDate(item.swiped_at)}</p>
                </div>
              </article>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
