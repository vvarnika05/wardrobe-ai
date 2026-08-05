import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import StyleQuizForm from "../components/StyleQuizForm";

export default function Onboarding() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleSuccess() {
    navigate("/swipe");
  }

  return (
    <div className="onboarding-page">
      <p className="eyebrow">Your style note</p>
      <h1 className="page-title">Tell us how you dress</h1>
      <p className="page-sub">
        Signed in as <strong style={{ color: "var(--text)" }}>{user?.email}</strong>
        {" · "}
        <button type="button" className="text-link" onClick={logout}>
          Log out
        </button>
      </p>
      <p className="page-sub" style={{ marginTop: -12 }}>
        A short free-text note plus a few preferences — we&apos;ll open
        today&apos;s edit from there.
      </p>
      <StyleQuizForm onSuccess={handleSuccess} />
    </div>
  );
}
