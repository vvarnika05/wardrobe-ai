/**
 * Decorative scalloped-edge "sticker" badge.
 * Pure SVG — no images. Text is short accent copy only.
 */
export default function StickerBadge({
  label = "EDIT",
  fill = "#e8836b",
  className = "",
}) {
  return (
    <svg
      className={`landing-sticker ${className}`.trim()}
      viewBox="0 0 120 120"
      aria-hidden="true"
    >
      {/* Wavy / scalloped circle path */}
      <path
        d="M60 4
           C66 4 70 10 76 8 C82 6 84 14 90 14 C96 14 98 8 104 12
           C110 16 106 22 110 28 C114 34 108 36 110 42 C112 48 118 50 116 56
           C114 62 108 62 108 68 C108 74 114 78 110 84 C106 90 98 88 94 94
           C90 100 84 96 78 100 C72 104 70 110 64 110 C58 110 56 104 50 102
           C44 100 40 106 34 102 C28 98 30 90 24 88 C18 86 12 90 10 84
           C8 78 14 74 12 68 C10 62 4 62 4 56 C4 50 10 48 10 42 C10 36 4 34 8 28
           C12 22 18 26 22 20 C26 14 24 8 30 8 C36 8 40 14 46 10 C52 6 54 4 60 4 Z"
        fill={fill}
      />
      <text x="60" y="58" textAnchor="middle" dominantBaseline="middle">
        {label}
      </text>
    </svg>
  );
}
