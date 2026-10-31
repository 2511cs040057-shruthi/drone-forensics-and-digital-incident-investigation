import { useState } from "react";
import { Eye, EyeOff, LockKeyhole, LogIn, ShieldCheck, UserPlus, Waypoints } from "lucide-react";

export default function LoginPage({ mode = "login", onLogin, onRegister, onModeChange, initialError = "" }) {
  const isRegister = mode === "register";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (isRegister) {
        if (password.length < 12) throw new Error("Password must contain at least 12 characters.");
        if (password !== confirmPassword) throw new Error("The passwords do not match.");
        await onRegister({ username, password, confirm_password: confirmPassword });
      } else {
        await onLogin({ username, password });
      }
    } catch (formError) {
      setError(formError.message);
    } finally {
      setBusy(false);
    }
  }

  function changeMode(nextMode) {
    setError("");
    setPassword("");
    setConfirmPassword("");
    onModeChange(nextMode);
  }

  function updateValue(setValue) {
    return (event) => {
      setValue(event.target.value);
      setError("");
    };
  }

  return <main className="login-screen">
    <section className="login-story">
      <div className="login-brand"><span className="login-brand-mark"><Waypoints size={21} /></span><span><b>DRONE FORENSICS</b><small>INVESTIGATION SYSTEM</small></span></div>
      <div className="login-story-copy"><span className="login-overline">DIGITAL EVIDENCE WORKSPACE</span><h1>Every detail<br /><em>has a record.</em></h1><p>A secure local workspace for drone evidence, flight data, and incident investigations.</p></div>
      <div className="login-visual" aria-hidden="true"><div className="login-orbit orbit-one" /><div className="login-orbit orbit-two" /><div className="login-visual-core"><Waypoints size={50} strokeWidth={1.1} /></div><span className="orbit-point point-one" /><span className="orbit-point point-two" /><span className="orbit-point point-three" /><span className="login-coordinate coord-one">47° 36′ 14.4″ N</span><span className="login-coordinate coord-two">LOCAL CASE STORE · MYSQL</span></div>
      <div className="login-story-foot"><span><ShieldCheck size={15} /> CONTROLLED EXAMINER ACCESS</span><span>LOCAL INSTANCE · PHASE 2</span></div>
    </section>

    <section className="login-panel"><form className="login-form" onSubmit={submit}>
      <div className="login-form-icon"><LockKeyhole size={18} /></div>
      <div className="auth-mode-tabs" role="tablist" aria-label="Account access">
        <button type="button" role="tab" aria-selected={!isRegister} className={!isRegister ? "selected" : ""} onClick={() => changeMode("login")}><LogIn size={15} />Login</button>
        <button type="button" role="tab" aria-selected={isRegister} className={isRegister ? "selected" : ""} onClick={() => changeMode("register")}><UserPlus size={15} />Register</button>
      </div>
      <span className="login-overline">{isRegister ? "NEW INVESTIGATOR" : "EXAMINER SIGN IN"}</span>
      <h2>{isRegister ? "Create your account" : "Welcome back"}</h2>
      <p className="login-intro">{isRegister ? "Register to access the investigation workspace." : "Sign in to access your investigation workspace."}</p>
      <label className="login-field">Username<input autoComplete="username" autoCapitalize="none" spellCheck="false" autoFocus required minLength={isRegister ? 3 : 1} maxLength={80} value={username} onChange={updateValue(setUsername)} placeholder={isRegister ? "Choose an investigator username" : "Your investigator username"} /></label>
      <label className="login-field">Password<span className="password-input"><input autoComplete={isRegister ? "new-password" : "current-password"} required minLength={isRegister ? 12 : undefined} type={showPassword ? "text" : "password"} value={password} onChange={updateValue(setPassword)} placeholder={isRegister ? "At least 12 characters" : "Enter your password"} /><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></span>{isRegister && <small className="field-hint">Use 12 or more characters. Letters, numbers, and symbols are accepted.</small>}</label>
      {isRegister && <label className="login-field">Confirm password<span className="password-input"><input autoComplete="new-password" required minLength={12} type={showPassword ? "text" : "password"} value={confirmPassword} onChange={updateValue(setConfirmPassword)} placeholder="Enter your password again" /></span>{confirmPassword && password !== confirmPassword && <small className="field-hint field-hint-error">Passwords do not match yet.</small>}</label>}
      {(error || initialError) && <div className="login-error" role="alert">{error || initialError}</div>}
      <button className="login-submit" type="submit" disabled={busy}>{busy ? (isRegister ? "Creating account…" : "Signing in…") : (isRegister ? "Create account" : "Sign in")}<span>→</span></button>
      <div className="login-security-note"><ShieldCheck size={14} /><span>Passwords are stored as hashes in your MySQL database.</span></div>
    </form></section>
  </main>;
}
