import { motion } from "framer-motion";
import StickerBadge from "./StickerBadge";

/**
 * Full-viewport hero — animates in on mount (not scroll-triggered).
 */
export default function HeroSection() {
  return (
    <section className="landing-hero">
      <div className="landing-hero__badge">
        <StickerBadge label="STYLE" fill="#e8836b" />
      </div>

      <motion.p
        className="landing-hero__kicker"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05 }}
      >
        A personal fashion edit
      </motion.p>

      <motion.h1
        className="landing-hero__headline"
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
      >
        Find your{" "}
        <span className="landing-hero__script">edit</span>
      </motion.h1>

      <motion.p
        className="landing-hero__sub"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, delay: 0.35 }}
      >
        Tell us how you dress. We curate a rack worth swiping — no endless
        scroll, no noise.
      </motion.p>

      <motion.p
        className="landing-hero__scroll-hint"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.9, duration: 0.6 }}
      >
        Scroll ↓
      </motion.p>
    </section>
  );
}
