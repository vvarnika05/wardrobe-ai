import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";

/**
 * Final CTA — Sign Up / Log In.
 */
export default function CTASection() {
  const navigate = useNavigate();

  return (
    <section className="landing-cta">
      <motion.h2
        className="landing-cta__headline"
        initial={{ opacity: 0, y: 36 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
      >
        Find your edit.
      </motion.h2>

      <motion.p
        className="landing-cta__sub"
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ duration: 0.55, delay: 0.1 }}
      >
        Start with a short style note. Walk out with a rack that feels like yours.
      </motion.p>

      <motion.div
        className="landing-cta__actions"
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.4 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <button
          type="button"
          className="landing-btn landing-btn--primary"
          onClick={() => navigate("/signup")}
        >
          Sign Up
        </button>
        <button
          type="button"
          className="landing-btn landing-btn--ghost"
          onClick={() => navigate("/login")}
        >
          Log In
        </button>
      </motion.div>
    </section>
  );
}
