/**
 * Presentational outfit card.
 * SwipeDeck owns drag behavior — wrap this in motion.div there if needed.
 */
export default function OutfitCard({ outfit, tint = 0, style, className = "" }) {
  if (!outfit) return null;

  const colors = Array.isArray(outfit.color_tags)
    ? outfit.color_tags.join(" · ")
    : "";

  // tint: -1..1 from drag — negative = reject grey, positive = accept coral
  const overlay =
    tint > 0.05
      ? `rgba(232, 131, 107, ${Math.min(tint, 1) * 0.35})`
      : tint < -0.05
        ? `rgba(120, 130, 145, ${Math.min(Math.abs(tint), 1) * 0.35})`
        : "transparent";

  return (
    <article className={`outfit-card ${className}`.trim()} style={style}>
      <div className="outfit-card__media">
        {outfit.image_url ? (
          <img
            src={outfit.image_url}
            alt={outfit.category || "Outfit"}
            draggable={false}
          />
        ) : (
          <div className="outfit-card__placeholder">No image</div>
        )}
        <div className="outfit-card__scrim" />
        <div
          className="outfit-card__tint"
          style={{ background: overlay }}
          aria-hidden
        />
        <div className="outfit-card__labels">
          <span className="outfit-card__category">
            {outfit.category || "Look"}
          </span>
          {outfit.formality_level && (
            <span className="outfit-card__meta">{outfit.formality_level}</span>
          )}
          {colors && <span className="outfit-card__meta">{colors}</span>}
        </div>
      </div>
      {outfit.reason && <p className="outfit-card__reason">{outfit.reason}</p>}
    </article>
  );
}
