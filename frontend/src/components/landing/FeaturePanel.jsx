import { motion } from "framer-motion";
import StickerBadge from "./StickerBadge";

/**
 * One scroll-reveal content panel.
 *
 * Props:
 * - title, description: copy
 * - theme: "olive" | "maroon" | "cream" — full-bleed background
 * - accent: "checker" | "block" | "badge" — decorative visual only
 */
export default function FeaturePanel({
  title,
  description,
  theme = "cream",
  accent = "block",
}) {
  return (
    <section className={`landing-panel landing-panel--${theme}`}>
      <motion.div
        className="landing-panel__inner"
        initial={{ opacity: 0, y: 48 }}
        whileInView={{ opacity: 1, y: 0 }}
        // once: true → animate the first time it enters view, never again
        viewport={{ once: true, amount: 0.35 }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="landing-panel__visual" aria-hidden="true">
          {accent === "checker" && <div className="landing-checker" />}
          {accent === "block" && <div className="landing-color-block" />}
          {accent === "badge" && (
            <StickerBadge
              label="SWIPE"
              fill={theme === "cream" ? "#e8836b" : "#a8c0e0"}
            />
          )}
        </div>

        <div>
          <h2 className="landing-panel__title">{title}</h2>
          <p className="landing-panel__desc">{description}</p>
        </div>
      </motion.div>
    </section>
  );
}
