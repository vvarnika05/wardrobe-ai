/**
 * Accept / reject controls for the swipe deck.
 * Keep icons simple (text) so we don't need an icon library.
 */
export default function SwipeButtons({ onReject, onAccept, disabled = false }) {
  return (
    <div className="swipe-buttons">
      <button
        type="button"
        className="swipe-btn swipe-btn--reject"
        onClick={onReject}
        disabled={disabled}
        aria-label="Reject"
      >
        ✕
      </button>
      <button
        type="button"
        className="swipe-btn swipe-btn--accept"
        onClick={onAccept}
        disabled={disabled}
        aria-label="Accept"
      >
        ♡
      </button>
    </div>
  );
}
