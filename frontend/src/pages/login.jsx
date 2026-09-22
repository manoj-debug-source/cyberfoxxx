import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

export default function Login() {
  const navigate = useNavigate();

  const [role, setRole] = useState("officer");
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isAdmin = role === "admin";

  async function handleLogin(e) {
    e.preventDefault();

    setError("");

    if (!userId || !password) {
      setError(
        isAdmin
          ? "Please enter Administrator ID and authentication key."
          : "Please enter Officer ID and authentication key."
      );
      return;
    }

    try {
      setLoading(true);

      const response = await axios.post(
        "http://127.0.0.1:8000/api/auth/login",
        {
          username: userId,
          password: password,
        }
      );

      console.log("LOGIN RESPONSE:", response.data);

      const data = response.data;

      if (!data?.access_token) {
        setError("Authentication token was not returned.");
        return;
      }

      if (!data?.user) {
        setError("User information was not returned.");
        return;
      }

      if (data.user.role !== role) {
        setError(
          `This account is registered as ${data.user.role}, not ${role}.`
        );
        return;
      }

      localStorage.setItem("access_token", data.access_token);

      localStorage.setItem(
        "cyberfoxxx_user",
        JSON.stringify(data.user)
      );

      console.log(
        "TOKEN SAVED:",
        localStorage.getItem("access_token")
          ? "YES"
          : "NO"
      );

      if (data.user.role === "admin") {
        navigate("/admin");
      } else {
        navigate("/officer");
      }
    } catch (err) {
      console.error("LOGIN ERROR:", err);

      if (err.response) {
        setError(
          err.response.data?.detail ||
            "Invalid username or password."
        );
      } else {
        setError(
          "Unable to establish connection with CYBERFOXXX."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  function handleRoleChange(selectedRole) {
    setRole(selectedRole);
    setError("");
    setPassword("");
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white relative overflow-hidden flex items-center justify-center px-6">

      {/* =========================================================
          BACKGROUND SECURITY GRID
      ========================================================= */}

      <div
        className="absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(59,130,246,0.7) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59,130,246,0.7) 1px, transparent 1px)
          `,
          backgroundSize: "55px 55px",
        }}
      />

      {/* Ambient glow */}

      <div className="absolute -top-40 -left-40 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px]" />

      <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[120px]" />

      {/* =========================================================
          TOP SECURITY BAR
      ========================================================= */}

      <div className="absolute top-0 left-0 right-0 border-b border-white/5 bg-black/20 backdrop-blur-md">

        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">

          <div className="flex items-center gap-3">

            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />

            <span className="text-[10px] font-bold tracking-[0.25em] text-emerald-400">
              SECURE NETWORK
            </span>

          </div>

          <div className="hidden sm:flex items-center gap-6 text-[9px] tracking-[0.18em] text-slate-500">

            <span>
              ENCRYPTED SESSION
            </span>

            <span className="text-slate-700">
              //
            </span>

            <span>
              NODE: CYBERFOXXX-01
            </span>

          </div>

        </div>

      </div>

      {/* =========================================================
          LOGIN CONTAINER
      ========================================================= */}

      <div className="relative z-10 w-full max-w-md mt-8">

        {/* Brand */}

        <div className="text-center mb-8">

          <div className="relative inline-flex mb-5">

            <div className="absolute inset-[-8px] rounded-2xl border border-blue-500/20" />

            <div className="absolute inset-[-14px] rounded-2xl border border-blue-500/5" />

            <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center shadow-2xl shadow-blue-900/40">

              <span className="text-3xl font-black tracking-tighter">
                C-
              </span>

            </div>

          </div>

          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            CYBERFOXX<span className="text-blue-500"> -AI SYSTEM</span>
          </h1>

          <div className="flex items-center justify-center gap-3 mt-3">

            <div className="h-px w-10 bg-slate-700" />

            <p className="text-[10px] font-bold tracking-[0.3em] text-slate-400 uppercase">
              Identity Security Platform
            </p>

            <div className="h-px w-10 bg-slate-700" />

          </div>

        </div>

        {/* =========================================================
            LOGIN CARD
        ========================================================= */}

        <div className="relative">

          <div className="absolute -inset-1 bg-blue-600/10 rounded-3xl blur-xl" />

          <div className="relative bg-slate-900/90 backdrop-blur-xl border border-slate-700/60 rounded-3xl shadow-2xl overflow-hidden">

            {/* Top accent */}

            <div className="h-1 bg-gradient-to-r from-blue-700 via-blue-400 to-cyan-400" />

            <div className="p-7 sm:p-8">

              {/* =====================================================
                  CARD HEADING
              ===================================================== */}

              <div className="mb-7">

                <div className="flex items-center justify-between">

                  <div>

                    <p className="text-[10px] font-bold tracking-[0.2em] text-blue-400 mb-2 transition-all duration-300">
                      {isAdmin
                        ? "AUTHENTICATION GATEWAY"
                        : "OFFICER AUTHENTICATION"}
                    </p>

                    <h2 className="text-2xl font-bold text-white transition-all duration-300">
                      {isAdmin
                        ? "Secure Access"
                        : "Screening Access"}
                    </h2>

                  </div>

                  <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">

                    <span className="text-emerald-400 text-lg">
                      ✓
                    </span>

                  </div>

                </div>

                <p className="text-xs text-slate-500 mt-2 leading-relaxed transition-all duration-300">
                  {isAdmin
                    ? "Authorized personnel only. Credentials are verified against the CYBERFOXXX authentication service."
                    : "Authorized screening personnel only. Officer credentials are verified before access to the identity screening console."}
                </p>

              </div>

              {/* =====================================================
                  ROLE SELECTOR
              ===================================================== */}

              <div className="mb-6">

                <label className="block text-[10px] font-bold tracking-[0.18em] text-slate-400 uppercase mb-3">
                  Access Classification
                </label>

                <div className="grid grid-cols-2 gap-3">

                  {/* =================================================
                      OFFICER
                  ================================================= */}

                  <button
                    type="button"
                    onClick={() =>
                      handleRoleChange("officer")
                    }
                    className={`relative p-4 rounded-xl border text-left transition-all duration-300 ${
                      role === "officer"
                        ? "bg-blue-600/15 border-blue-500/60 shadow-lg shadow-blue-900/20"
                        : "bg-slate-950/40 border-slate-700 hover:border-slate-600"
                    }`}
                  >

                    {role === "officer" && (
                      <span className="absolute top-3 right-3 w-2 h-2 rounded-full bg-blue-400 shadow-lg shadow-blue-400/50" />
                    )}

                    <div
                      className={`text-lg mb-2 transition-all ${
                        role === "officer"
                          ? "text-blue-400"
                          : "text-slate-500"
                      }`}
                    >
                      ◈
                    </div>

                    <p
                      className={`text-sm font-bold ${
                        role === "officer"
                          ? "text-blue-300"
                          : "text-slate-300"
                      }`}
                    >
                      Officer
                    </p>

                    <p className="text-[9px] text-slate-500 mt-1">
                      SCREENING ACCESS
                    </p>

                  </button>

                  {/* =================================================
                      ADMIN
                  ================================================= */}

                  <button
                    type="button"
                    onClick={() =>
                      handleRoleChange("admin")
                    }
                    className={`relative p-4 rounded-xl border text-left transition-all duration-300 ${
                      role === "admin"
                        ? "bg-blue-600/15 border-blue-500/60 shadow-lg shadow-blue-900/20"
                        : "bg-slate-950/40 border-slate-700 hover:border-slate-600"
                    }`}
                  >

                    {role === "admin" && (
                      <span className="absolute top-3 right-3 w-2 h-2 rounded-full bg-blue-400 shadow-lg shadow-blue-400/50" />
                    )}

                    <div
                      className={`text-lg mb-2 transition-all ${
                        role === "admin"
                          ? "text-blue-400"
                          : "text-slate-500"
                      }`}
                    >
                      ◆
                    </div>

                    <p
                      className={`text-sm font-bold ${
                        role === "admin"
                          ? "text-blue-300"
                          : "text-slate-300"
                      }`}
                    >
                      Administrator
                    </p>

                    <p className="text-[9px] text-slate-500 mt-1">
                      SYSTEM OVERSIGHT
                    </p>

                  </button>

                </div>

              </div>

              {/* =====================================================
                  ROLE-SPECIFIC ACCESS NOTICE
              ===================================================== */}

              <div
                className={`mb-6 rounded-xl border px-4 py-3 transition-all duration-300 ${
                  isAdmin
                    ? "border-blue-500/20 bg-blue-500/5"
                    : "border-cyan-500/20 bg-cyan-500/5"
                }`}
              >

                <div className="flex items-center gap-3">

                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      isAdmin
                        ? "bg-blue-500/10 text-blue-400"
                        : "bg-cyan-500/10 text-cyan-400"
                    }`}
                  >
                    {isAdmin ? "◆" : "◈"}
                  </div>

                  <div>

                    <p
                      className={`text-[10px] font-bold tracking-[0.15em] ${
                        isAdmin
                          ? "text-blue-400"
                          : "text-cyan-400"
                      }`}
                    >
                      {isAdmin
                        ? "ADMINISTRATIVE ACCESS"
                        : "OFFICER SCREENING ACCESS"}
                    </p>

                    <p className="text-[9px] text-slate-600 mt-1">
                      {isAdmin
                        ? "Dashboard • Audit • System Oversight"
                        : "Document Screening • Risk Review • Identity Verification"}
                    </p>

                  </div>

                </div>

              </div>

              {/* =====================================================
                  LOGIN FORM
              ===================================================== */}

              <form onSubmit={handleLogin}>

                {/* User ID */}

                <div className="mb-5">

                  <label className="block text-[10px] font-bold tracking-[0.18em] text-slate-400 uppercase mb-2">
                    {isAdmin
                      ? "Administrator ID"
                      : "Officer ID"}
                  </label>

                  <div className="relative">

                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                      ◉
                    </span>

                    <input
                      type="text"
                      value={userId}
                      onChange={(e) =>
                        setUserId(e.target.value)
                      }
                      placeholder={
                        isAdmin
                          ? "Enter administrator ID"
                          : "Enter officer ID"
                      }
                      autoComplete="username"
                      className="w-full bg-slate-950/60 border border-slate-700 rounded-xl pl-11 pr-4 py-3.5 text-sm text-white placeholder:text-slate-600 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10"
                    />

                  </div>

                </div>

                {/* Password */}

                <div className="mb-5">

                  <div className="flex items-center justify-between mb-2">

                    <label className="block text-[10px] font-bold tracking-[0.18em] text-slate-400 uppercase">
                      Authentication Key
                    </label>

                    <span className="text-[9px] text-slate-600">
                      ENCRYPTED
                    </span>

                  </div>

                  <div className="relative">

                    <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500">
                      ◈
                    </span>

                    <input
                      type="password"
                      value={password}
                      onChange={(e) =>
                        setPassword(e.target.value)
                      }
                      placeholder="Enter authentication key"
                      autoComplete="current-password"
                      className="w-full bg-slate-950/60 border border-slate-700 rounded-xl pl-11 pr-4 py-3.5 text-sm text-white placeholder:text-slate-600 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10"
                    />

                  </div>

                </div>

                {/* Error */}

                {error && (

                  <div className="mb-5 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">

                    <div className="flex items-start gap-3">

                      <span className="text-red-400">
                        !
                      </span>

                      <div>

                        <p className="text-xs font-semibold text-red-400">
                          AUTHENTICATION FAILED
                        </p>

                        <p className="text-[11px] text-red-400/70 mt-1">
                          {error}
                        </p>

                      </div>

                    </div>

                  </div>

                )}

                {/* Login */}

                <button
                  type="submit"
                  disabled={loading}
                  className="group relative w-full overflow-hidden rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900 disabled:cursor-not-allowed py-4 font-bold text-sm tracking-wider transition-all duration-200 shadow-xl shadow-blue-900/20"
                >

                  <span className="relative z-10">

                    {loading ? (
                      <span className="flex items-center justify-center gap-3">

                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />

                        VERIFYING CREDENTIALS...

                      </span>
                    ) : (
                      isAdmin
                        ? "AUTHENTICATE & ENTER"
                        : "AUTHENTICATE & BEGIN SCREENING"
                    )}

                  </span>

                </button>

              </form>

              {/* =====================================================
                  SECURITY FOOTER
              ===================================================== */}

              <div className="mt-6 pt-5 border-t border-slate-800">

                <div className="grid grid-cols-3 gap-3">

                  <SecurityItem
                    icon="✓"
                    label="JWT"
                    value="SECURED"
                  />

                  <SecurityItem
                    icon="◆"
                    label="SHA-256"
                    value="ACTIVE"
                  />

                  <SecurityItem
                    icon="●"
                    label="API"
                    value="ONLINE"
                  />

                </div>

              </div>

            </div>

          </div>

        </div>

        {/* =========================================================
            BOTTOM STATUS
        ========================================================= */}

        <div className="mt-6 flex items-center justify-center gap-3">

          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />

          <p className="text-[9px] font-bold tracking-[0.2em] text-slate-600 uppercase">
            CYBERFOXXX Security Infrastructure Online
          </p>

        </div>

        <p className="text-center text-[9px] text-slate-700 mt-3">
          Unauthorized access is prohibited • Authorized personnel only
        </p>

      </div>

    </div>
  );
}


/* =============================================================
   SECURITY ITEM
============================================================= */

function SecurityItem({
  icon,
  label,
  value,
}) {
  return (
    <div className="text-center">

      <div className="flex items-center justify-center gap-1.5">

        <span className="text-[10px] text-emerald-500">
          {icon}
        </span>

        <span className="text-[9px] font-bold tracking-wider text-slate-500">
          {label}
        </span>

      </div>

      <p className="text-[8px] text-slate-700 mt-1">
        {value}
      </p>

    </div>
  );
}