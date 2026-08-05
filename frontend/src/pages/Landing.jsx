import HeroSection from "../components/landing/HeroSection";
import FeaturePanel from "../components/landing/FeaturePanel";
import CTASection from "../components/landing/CTASection";
import "../styles/landing.css";

/**
 * Public marketing landing page.
 * CSS is scoped under .landing-page so dark app theme stays untouched.
 */
export default function Landing() {
  return (
    <div className="landing-page">
      <HeroSection />

      <FeaturePanel
        theme="olive"
        accent="checker"
        title="Tell us your style"
        description="A short free-text note plus a few preferences. We read the vibe — not a forty-question survey."
      />

      <FeaturePanel
        theme="maroon"
        accent="block"
        title="AI curates your edit"
        description="Retrieval finds looks that fit. An LLM ranks a tight deck with reasons — a personal rack, not a feed."
      />

      <FeaturePanel
        theme="cream"
        accent="badge"
        title="Swipe to build your wardrobe"
        description="Accept what feels right. Pass on the rest. Your taste compounds with every decision."
      />

      <CTASection />
    </div>
  );
}
