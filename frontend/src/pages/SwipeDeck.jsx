import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { getRecommendations, submitSwipe } from "../api/client";
import OutfitCard from "../components/OutfitCard";
import SwipeButtons from "../components/SwipeButtons";
import NavBar from "../components/NavBar";

const SWIPE_THRESHOLD = 120;

export default function SwipeDeck() {
  const [deck, setDeck] = useState([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exitX, setExitX] = useState(0);

  const x = useMotionValue(0);
  const tint = useTransform(x, [-200, 0, 200], [-1, 0, 1]);
  const [tintValue, setTintValue] = useState(0);

  useEffect(() => {
    const unsub = tint.on("change", (v) => setTintValue(v));
    return () => unsub();
  }, [tint]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const outfits = await getRecommendations();
        if (!cancelled) {
          setDeck(outfits);
          setIndex(0);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Failed to load recommendations");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const exhausted = !loading && !error && index >= deck.length;
  const empty = !loading && !error && deck.length === 0;

  const decide = useCallback(
    (decision, flyX) => {
      const outfit = deck[index];
      if (!outfit) return;

      setExitX(flyX);
      window.setTimeout(() => {
        setIndex((i) => i + 1);
        setExitX(0);
        x.set(0);
      }, 180);

      submitSwipe(outfit.outfit_id, decision).catch((err) => {
        console.error("Swipe log failed:", err);
      });
    },
    [deck, index, x]
  );

  function handleReject() {
    decide("rejected", -320);
  }

  function handleAccept() {
    decide("accepted", 320);
  }

  function handleDragEnd(_, info) {
    const offset = info.offset.x;
    const velocity = info.velocity.x;
    if (offset > SWIPE_THRESHOLD || velocity > 600) {
      decide("accepted", 400);
    } else if (offset < -SWIPE_THRESHOLD || velocity < -600) {
      decide("rejected", -400);
    }
  }

  function shell(content) {
    return (
      <div className="app-shell">
        <NavBar />
        {content}
      </div>
    );
  }

  if (loading) {
    return shell(
      <div className="swipe-page">
        <p className="swipe-status">Curating today&apos;s edit…</p>
      </div>
    );
  }

  if (error) {
    return shell(
      <div className="swipe-page">
        <p className="swipe-status swipe-status--error">{error}</p>
        <button
          type="button"
          className="text-link"
          onClick={() => window.location.reload()}
        >
          Try again
        </button>
      </div>
    );
  }

  if (empty) {
    return shell(
      <div className="swipe-page">
        <h1 className="swipe-end-title">Nothing in the rack</h1>
        <p className="swipe-end-copy">
          No recommendations came back. Check your{" "}
          <Link to="/profile" className="text-link">
            profile
          </Link>{" "}
          or try again later.
        </p>
      </div>
    );
  }

  if (exhausted) {
    return shell(
      <div className="swipe-page">
        <h1 className="swipe-end-title">That&apos;s today&apos;s edit.</h1>
        <p className="swipe-end-copy">
          You&apos;ve seen every look in this deck.{" "}
          <Link to="/saved" className="text-link">
            View your saved outfits
          </Link>
        </p>
        <p style={{ marginTop: 20 }}>
          <button
            type="button"
            className="auth-submit"
            onClick={() => window.location.assign("/swipe")}
          >
            New picks
          </button>
        </p>
      </div>
    );
  }

  const stack = deck.slice(index, index + 3);

  return shell(
    <div className="swipe-page">
      <header className="swipe-header">
        <p className="swipe-kicker">The Edit</p>
        <p className="swipe-progress">
          {Math.min(index + 1, deck.length)} / {deck.length}
        </p>
      </header>

      <div className="swipe-stack">
        {stack
          .map((outfit, i) => {
            const isTop = i === 0;
            const depth = i;
            const scale = 1 - depth * 0.04;
            const yOffset = depth * 10;

            if (!isTop) {
              return (
                <div
                  key={outfit.outfit_id}
                  className="swipe-stack__layer"
                  style={{
                    transform: `translateY(${yOffset}px) scale(${scale})`,
                    zIndex: 10 - depth,
                  }}
                >
                  <OutfitCard outfit={outfit} />
                </div>
              );
            }

            return (
              <motion.div
                key={outfit.outfit_id}
                className="swipe-stack__layer swipe-stack__layer--top"
                style={{ x, zIndex: 20, cursor: "grab" }}
                drag="x"
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.9}
                onDragEnd={handleDragEnd}
                animate={exitX ? { x: exitX, opacity: 0 } : { x: 0, opacity: 1 }}
                transition={{ type: "spring", stiffness: 300, damping: 28 }}
              >
                <OutfitCard outfit={outfit} tint={tintValue} />
              </motion.div>
            );
          })
          .reverse()}
      </div>

      <SwipeButtons onReject={handleReject} onAccept={handleAccept} />
    </div>
  );
}
