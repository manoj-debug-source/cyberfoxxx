import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  getScreeningStats,
  getAuditLogs,
} from "../api/client";


export default function AdminDashboard() {

  const navigate = useNavigate();

  const [stats, setStats] = useState({
    total_screenings: 0,
    clear: 0,
    review: 0,
    rejected: 0,
  });

  const [auditLogs, setAuditLogs] = useState([]);

  const [screeningId, setScreeningId] = useState("");
  const [lookupError, setLookupError] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const user = JSON.parse(
    localStorage.getItem("cyberfoxxx_user") || "{}"
  );


  /* =========================================================
     LOAD DASHBOARD DATA
  ========================================================= */

  useEffect(() => {

    let mounted = true;

    async function loadDashboard() {

      try {

        setLoading(true);
        setError("");

        const statsData = await getScreeningStats();

        console.log(
          "ADMIN DASHBOARD STATS:",
          statsData
        );

        let auditData = null;

        try {

          auditData = await getAuditLogs();

        } catch (auditError) {

          console.warn(
            "Could not load audit logs:",
            auditError
          );

        }

        if (!mounted) return;

        setStats({
          total_screenings:
            Number(statsData?.total_screenings || 0),

          clear:
            Number(statsData?.clear || 0),

          review:
            Number(statsData?.review || 0),

          rejected:
            Number(statsData?.rejected || 0),
        });

        const logs =
          auditData?.items ||
          auditData?.logs ||
          [];

        setAuditLogs(
          Array.isArray(logs)
            ? logs
            : []
        );

      }

      catch (err) {

        console.error(
          "ADMIN DASHBOARD ERROR:",
          err
        );

        if (mounted) {

          setError(
            err?.response?.data?.detail ||
            err?.message ||
            "Failed to load dashboard data."
          );

        }

      }

      finally {

        if (mounted) {
          setLoading(false);
        }

      }

    }

    loadDashboard();

    return () => {
      mounted = false;
    };

  }, []);


  /* =========================================================
     CASE INTELLIGENCE LOOKUP
  ========================================================= */

  function handleCaseLookup(event) {

    event.preventDefault();

    setLookupError("");

    const id =
      screeningId.trim().toUpperCase();

    if (!id) {

      setLookupError(
        "Please enter a Screening ID."
      );

      return;
    }

    if (!id.startsWith("SCR-")) {

      setLookupError(
        "Invalid Screening ID. Example: SCR-24D96249"
      );

      return;
    }

    navigate(
      `/admin/case/${encodeURIComponent(id)}`
    );

  }


  /* =========================================================
     OFFICER STATISTICS
  ========================================================= */

  const officerStats =
    buildOfficerStats(auditLogs);


  /* =========================================================
     RECENT ACTIONS
  ========================================================= */

  const recentActions =
    auditLogs
      .filter((item) => {

        return (
          item?.officer_decision ||
          item?.officer ||
          item?.decided_by
        );

      })
      .slice(0, 6);


  /* =========================================================
     SUMMARY
  ========================================================= */

  const finalized =
    stats.clear +
    stats.review +
    stats.rejected;

  const pending =
    Math.max(
      stats.total_screenings - finalized,
      0
    );

  const decisionRate =
    stats.total_screenings > 0
      ? Math.round(
          (finalized / stats.total_screenings) * 100
        )
      : 0;


  /* =========================================================
     LOGOUT
  ========================================================= */

  function logout() {

    localStorage.removeItem(
      "cyberfoxxx_user"
    );

    localStorage.removeItem(
      "access_token"
    );

    navigate("/login");

  }


  /* =========================================================
     PAGE
  ========================================================= */

  return (

    <div className="min-h-screen bg-[#020617] text-white">


      {/* =====================================================
          BACKGROUND
      ===================================================== */}

      <div className="fixed inset-0 pointer-events-none">

        <div
          className="absolute inset-0 opacity-[0.035]"
          style={{
            backgroundImage: `
              linear-gradient(rgba(59,130,246,0.8) 1px, transparent 1px),
              linear-gradient(90deg, rgba(59,130,246,0.8) 1px, transparent 1px)
            `,
            backgroundSize: "60px 60px",
          }}
        />

        <div className="absolute top-0 left-1/4 w-[500px] h-[300px] bg-blue-600/5 blur-[130px]" />

        <div className="absolute bottom-0 right-0 w-[500px] h-[400px] bg-cyan-500/5 blur-[140px]" />

      </div>


      {/* =====================================================
          HEADER
      ===================================================== */}

      <header className="relative z-10 border-b border-white/[0.06] bg-[#020617]/90 backdrop-blur-xl">

        <div className="max-w-[1500px] mx-auto px-6 lg:px-8 h-20 flex items-center justify-between">


          {/* BRAND */}

          <div className="flex items-center gap-4">

            <div className="relative">

              <div className="w-11 h-11 bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-900/30">

                <span className="text-xl font-black">
                  C
                </span>

              </div>

              <span className="absolute -right-1 -bottom-1 w-3 h-3 bg-emerald-400 border-2 border-[#020617] rounded-full" />

            </div>


            <div>

              <h1 className="text-lg font-black tracking-[0.08em]">
                CYBER<span className="text-blue-500">FOXXX</span>
              </h1>

              <p className="text-[8px] tracking-[0.3em] text-slate-600">
                COMMAND & CONTROL
              </p>

            </div>

          </div>


          {/* CENTER STATUS */}

          <div className="hidden lg:flex items-center gap-3">

            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />

            <span className="text-[9px] font-bold tracking-[0.25em] text-emerald-400">
              ALL SYSTEMS OPERATIONAL
            </span>

          </div>


          {/* ADMIN */}

          <div className="flex items-center gap-5">

            <div className="hidden sm:block text-right">

              <p className="text-xs font-semibold text-white">
                {user.name || user.username || "Administrator"}
              </p>

              <p className="text-[8px] tracking-wider text-slate-600">
                SYSTEM ADMINISTRATOR
              </p>

            </div>


            <div className="w-px h-8 bg-slate-800" />


            <button
              onClick={logout}
              className="text-[9px] font-bold tracking-[0.15em] text-slate-500 hover:text-red-400 transition"
            >
              LOGOUT
            </button>

          </div>

        </div>

      </header>


      {/* =====================================================
          MAIN
      ===================================================== */}

      <main className="relative z-10 max-w-[1500px] mx-auto px-6 lg:px-8 py-8">


        {/* ===================================================
            COMMAND HEADER
        =================================================== */}

        <section className="mb-8">

          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-5">

            <div>

              <div className="flex items-center gap-3 mb-3">

                <span className="text-[8px] font-bold tracking-[0.3em] text-blue-500">
                  ADMINISTRATIVE CONTROL
                </span>

                <span className="text-[8px] text-slate-700">
                  //
                </span>

                <span className="text-[8px] tracking-[0.2em] text-slate-600">
                  NODE-01
                </span>

              </div>


              <h2 className="text-3xl lg:text-4xl font-black tracking-tight">
                Command Center
              </h2>


              <p className="text-sm text-slate-500 mt-2">
                Central monitoring and oversight of the
                CYBERFOXXX identity screening infrastructure.
              </p>

            </div>


            <Link
              to="/audit"
              className="group inline-flex items-center justify-center gap-3 px-5 py-3 border border-slate-800 bg-slate-900/50 hover:border-blue-500/40 hover:bg-blue-500/5 transition"
            >

              <span className="text-[9px] font-bold tracking-[0.2em] text-slate-400 group-hover:text-purple-400">
                OPEN AUDIT LOG
              </span>

              <span className="text-blue-500 group-hover:translate-x-1 transition-transform">
                →
              </span>

            </Link>

          </div>

        </section>


        {/* ===================================================
            ERROR
        =================================================== */}

        {error && (

          <div className="mb-6 border border-red-500/20 bg-red-500/5 px-5 py-4">

            <div className="flex items-center gap-3">

              <span className="text-red-400">
                !
              </span>

              <div>

                <p className="text-[9px] font-bold tracking-wider text-red-400">
                  SYSTEM DATA ERROR
                </p>

                <p className="text-[10px] text-red-400/60 mt-1">
                  {error}
                </p>

              </div>

            </div>

          </div>

        )}


        {/* ===================================================
            PRIMARY METRICS
        =================================================== */}

        <section className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">

          <MetricCard
            label="TOTAL SCREENINGS"
            value={
              loading
                ? "—"
                : String(
                    stats.total_screenings
                  ).padStart(2, "0")
            }
            code="SCR-ALL"
            icon="◎"
          />


          <MetricCard
            label="CLEARED"
            value={
              loading
                ? "—"
                : String(
                    stats.clear
                  ).padStart(2, "0")
            }
            code="DEC-CLEAR"
            icon="✓"
            accent="green"
          />


          <MetricCard
            label="UNDER REVIEW"
            value={
              loading
                ? "—"
                : String(
                    stats.review
                  ).padStart(2, "0")
            }
            code="DEC-REVIEW"
            icon="!"
            accent="yellow"
          />


          <MetricCard
            label="REJECTED"
            value={
              loading
                ? "—"
                : String(
                    stats.rejected
                  ).padStart(2, "0")
            }
            code="DEC-REJECT"
            icon="×"
            accent="red"
          />

        </section>


        {/* ===================================================
            CASE INTELLIGENCE LOOKUP
        =================================================== */}

        <section className="relative overflow-hidden border border-cyan-500/20 bg-[#06101c] p-6 lg:p-7 mb-6">

          {/* Decorative glow */}

          <div className="absolute top-0 right-0 w-72 h-72 bg-cyan-500/5 blur-[100px] pointer-events-none" />

          <div className="relative">

            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 mb-6">

              <div>

                <div className="flex items-center gap-3">

                  <span className="w-2 h-2 bg-cyan-400 rounded-full shadow-[0_0_10px_rgba(34,211,238,0.7)]" />

                  <p className="text-[8px] font-bold tracking-[0.3em] text-cyan-400">
                    SECURITY INVESTIGATION
                  </p>

                </div>

                <h3 className="text-lg font-black text-white mt-2">
                  Case Intelligence Lookup
                </h3>

                <p className="text-xs text-slate-500 mt-2">
                  Enter a Screening ID to retrieve the complete
                  screening intelligence record.
                </p>

              </div>


              <div className="hidden md:block text-right">

                <p className="text-[8px] tracking-[0.2em] text-slate-600">
                  AUTHORIZED ACCESS
                </p>

                <p className="text-[9px] text-emerald-400 font-bold mt-1">
                  ADMINISTRATOR ONLY
                </p>

              </div>

            </div>


            <form
              onSubmit={handleCaseLookup}
              className="flex flex-col md:flex-row gap-3"
            >

              <div className="relative flex-1">

                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan-500 font-mono text-sm">
                  #
                </span>

                <input
                  type="text"
                  value={screeningId}
                  onChange={(event) => {
                    setScreeningId(
                      event.target.value.toUpperCase()
                    );

                    if (lookupError) {
                      setLookupError("");
                    }
                  }}
                  placeholder="ENTER SCREENING ID  •  SCR-24D96249"
                  className="w-full h-14 pl-10 pr-4 bg-[#020617] border border-slate-800 focus:border-cyan-500/50 outline-none text-sm font-mono text-white placeholder:text-slate-700 transition"
                  autoComplete="off"
                  spellCheck="false"
                />

              </div>


              <button
                type="submit"
                className="h-14 px-7 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-400/50 transition font-black text-[10px] tracking-[0.2em]"
              >
                FETCH CASE →
              </button>

            </form>


            {lookupError && (

              <div className="mt-3 flex items-center gap-2 text-red-400">

                <span className="text-xs">
                  !
                </span>

                <span className="text-[9px] font-semibold tracking-wider">
                  {lookupError}
                </span>

              </div>

            )}


            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-5">

              <div className="flex items-center gap-2">

                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />

                <span className="text-[8px] text-slate-600 tracking-wider">
                  OCR
                </span>

              </div>

              <div className="flex items-center gap-2">

                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />

                <span className="text-[8px] text-slate-600 tracking-wider">
                  TAMPER
                </span>

              </div>

              <div className="flex items-center gap-2">

                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />

                <span className="text-[8px] text-slate-600 tracking-wider">
                  ANOMALY
                </span>

              </div>

              <div className="flex items-center gap-2">

                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />

                <span className="text-[8px] text-slate-600 tracking-wider">
                  IDENTITY
                </span>

              </div>

              <div className="flex items-center gap-2">

                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />

                <span className="text-[8px] text-slate-600 tracking-wider">
                  RISK
                </span>

              </div>

              <div className="flex items-center gap-2">

                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />

                <span className="text-[8px] text-slate-600 tracking-wider">
                  BLOCKCHAIN
                </span>

              </div>

            </div>

          </div>

        </section>


        {/* ===================================================
            ANALYTICS STRIP
        =================================================== */}

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">


          {/* Decision distribution */}

          <div className="lg:col-span-2 border border-slate-800 bg-[#070d18] p-6">

            <div className="flex items-center justify-between mb-6">

              <div>

                <p className="text-[8px] font-bold tracking-[0.25em] text-blue-500">
                  SCREENING ANALYTICS
                </p>

                <h3 className="text-sm font-bold text-white mt-1">
                  Decision Distribution
                </h3>

              </div>

              <span className="text-[8px] text-slate-600">
                LIVE DATA
              </span>

            </div>


            <div className="space-y-5">

              <ProgressRow
                label="CLEAR"
                value={stats.clear}
                total={stats.total_screenings}
                type="green"
              />

              <ProgressRow
                label="REVIEW"
                value={stats.review}
                total={stats.total_screenings}
                type="yellow"
              />

              <ProgressRow
                label="REJECTED"
                value={stats.rejected}
                total={stats.total_screenings}
                type="red"
              />

              <ProgressRow
                label="PENDING"
                value={pending}
                total={stats.total_screenings}
                type="blue"
              />

            </div>

          </div>


          {/* System overview */}

          <div className="border border-slate-800 bg-[#070d18] p-6">

            <div className="flex items-center justify-between mb-6">

              <div>

                <p className="text-[8px] font-bold tracking-[0.25em] text-blue-500">
                  SYSTEM METRICS
                </p>

                <h3 className="text-sm font-bold mt-1">
                  Operational Status
                </h3>

              </div>

              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />

            </div>


            <div className="space-y-4">

              <SystemLine
                name="OCR ENGINE"
                status="OPERATIONAL"
              />

              <SystemLine
                name="TAMPER DETECTION"
                status="OPERATIONAL"
              />

              <SystemLine
                name="IDENTITY VALIDATION"
                status="OPERATIONAL"
              />

              <SystemLine
                name="FACE & LIVENESS"
                status="OPERATIONAL"
              />

              <SystemLine
                name="RISK CALIBRATION"
                status="OPERATIONAL"
              />

              <SystemLine
                name="BLOCKCHAIN AUDIT"
                status="OPERATIONAL"
              />

            </div>

          </div>

        </section>


        {/* ===================================================
            LOWER COMMAND GRID
        =================================================== */}

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">


          {/* OFFICER ACTIVITY */}

          <div className="xl:col-span-2 border border-slate-800 bg-[#070d18]">

            <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between">

              <div>

                <p className="text-[8px] font-bold tracking-[0.25em] text-blue-500">
                  PERSONNEL MONITORING
                </p>

                <h3 className="text-sm font-bold mt-1">
                  Officer Activity
                </h3>

              </div>


              <Link
                to="/audit"
                className="text-[8px] tracking-[0.15em] text-slate-600 hover:text-blue-400 transition"
              >
                FULL AUDIT →
              </Link>

            </div>


            <div className="overflow-x-auto">

              <table className="w-full">

                <thead>

                  <tr className="border-b border-slate-800 text-left">

                    <th className="px-6 py-4 text-[8px] tracking-[0.15em] text-slate-600">
                      OFFICER
                    </th>

                    <th className="px-4 py-4 text-[8px] tracking-[0.15em] text-slate-600">
                      CASES
                    </th>

                    <th className="px-4 py-4 text-[8px] tracking-[0.15em] text-slate-600">
                      CLEAR
                    </th>

                    <th className="px-4 py-4 text-[8px] tracking-[0.15em] text-slate-600">
                      REVIEW
                    </th>

                    <th className="px-4 py-4 text-[8px] tracking-[0.15em] text-slate-600">
                      REJECT
                    </th>

                    <th className="px-6 py-4 text-[8px] tracking-[0.15em] text-slate-600">
                      STATUS
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {officerStats.length === 0 ? (

                    <tr>

                      <td
                        colSpan="6"
                        className="px-6 py-12 text-center"
                      >

                        <div className="text-slate-700 text-2xl mb-2">
                          ◌
                        </div>

                        <p className="text-xs text-slate-600">
                          No officer decisions recorded yet.
                        </p>

                      </td>

                    </tr>

                  ) : (

                    officerStats.map(
                      (officer) => (

                        <OfficerRow
                          key={officer.id}
                          id={officer.id}
                          cases={officer.cases}
                          clear={officer.clear}
                          review={officer.review}
                          reject={officer.reject}
                        />

                      )
                    )

                  )}

                </tbody>

              </table>

            </div>

          </div>


          {/* RECENT ACTIONS */}

          <div className="border border-slate-800 bg-[#070d18]">

            <div className="px-6 py-5 border-b border-slate-800">

              <p className="text-[8px] font-bold tracking-[0.25em] text-blue-500">
                ACTIVITY STREAM
              </p>

              <h3 className="text-sm font-bold mt-1">
                Recent Actions
              </h3>

            </div>


            <div className="px-6">

              {recentActions.length === 0 ? (

                <div className="py-12 text-center">

                  <p className="text-xs text-slate-600">
                    No recent officer actions.
                  </p>

                </div>

              ) : (

                recentActions.map(
                  (item, index) => {

                    const officer =
                      item?.officer_decision?.decided_by ||
                      item?.officer ||
                      item?.decided_by ||
                      "UNKNOWN";

                    const decision =
                      item?.officer_decision?.decision ||
                      item?.officer_decision ||
                      item?.decision ||
                      "-";

                    const screeningId =
                      item?.screening_id ||
                      item?.id ||
                      "-";

                    const timestamp =
                      item?.officer_decision?.decided_at ||
                      item?.timestamp ||
                      null;

                    return (

                      <Activity
                        key={`${screeningId}-${index}`}
                        officer={officer}
                        action={screeningId}
                        result={decision}
                        time={formatTime(timestamp)}
                      />

                    );

                  }
                )

              )}

            </div>

          </div>

        </section>


        {/* ===================================================
            SYSTEM SUMMARY
        =================================================== */}

        <section className="mt-4 border border-slate-800 bg-[#070d18] p-6">

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">

            <div>

              <p className="text-[8px] font-bold tracking-[0.25em] text-blue-500">
                INFRASTRUCTURE SUMMARY
              </p>

              <h3 className="text-sm font-bold mt-1">
                Screening Network Status
              </h3>

            </div>


            <div className="grid grid-cols-2 sm:grid-cols-4 gap-8">

              <MiniMetric
                label="FINALIZED"
                value={finalized}
              />

              <MiniMetric
                label="PENDING"
                value={pending}
              />

              <MiniMetric
                label="DECISIONS"
                value={officerStats.reduce(
                  (total, officer) =>
                    total + officer.cases,
                  0
                )}
              />

              <MiniMetric
                label="COMPLETION"
                value={`${decisionRate}%`}
                green
              />

            </div>

          </div>

        </section>

      </main>


      {/* =====================================================
          FOOTER
      ===================================================== */}

      <footer className="relative z-10 border-t border-white/[0.05] mt-10">

        <div className="max-w-[1500px] mx-auto px-6 lg:px-8 py-5 flex flex-col md:flex-row justify-between gap-2">

          <p className="text-[7px] tracking-[0.3em] text-slate-700">
            CYBERFOXXX SECURITY OPERATIONS
          </p>

          <p className="text-[7px] tracking-[0.25em] text-slate-700">
            IDENTITY • DOCUMENT • RISK • AUDIT • BLOCKCHAIN
          </p>

        </div>

      </footer>

    </div>
  );
}


/* =============================================================
   METRIC CARD
============================================================= */

function MetricCard({
  label,
  value,
  code,
  icon,
  accent = "blue",
}) {

  const accentClasses = {

    blue: {
      icon: "text-blue-400 bg-blue-500/10 border-blue-500/20",
      line: "bg-blue-500",
      number: "text-white",
    },

    green: {
      icon: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
      line: "bg-emerald-500",
      number: "text-emerald-400",
    },

    yellow: {
      icon: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
      line: "bg-yellow-500",
      number: "text-yellow-400",
    },

    red: {
      icon: "text-red-400 bg-red-500/10 border-red-500/20",
      line: "bg-red-500",
      number: "text-red-400",
    },

  };

  const theme =
    accentClasses[accent] ||
    accentClasses.blue;


  return (

    <div className="relative overflow-hidden border border-slate-800 bg-[#070d18] p-6 group hover:border-slate-700 transition">

      <div
        className={`absolute left-0 top-0 bottom-0 w-[2px] ${theme.line}`}
      />


      <div className="flex items-start justify-between">

        <div>

          <p className="text-[8px] tracking-[0.2em] text-slate-600 font-bold">
            {code}
          </p>

          <p className="text-[9px] tracking-[0.15em] text-slate-400 mt-4">
            {label}
          </p>

          <p
            className={`text-4xl font-black mt-1 ${theme.number}`}
          >
            {value}
          </p>

        </div>


        <div
          className={`w-10 h-10 border flex items-center justify-center text-lg ${theme.icon}`}
        >
          {icon}
        </div>

      </div>

    </div>

  );
}


/* =============================================================
   PROGRESS ROW
============================================================= */

function ProgressRow({
  label,
  value,
  total,
  type,
}) {

  const percentage =
    total > 0
      ? Math.round((value / total) * 100)
      : 0;


  const colors = {

    green: "bg-emerald-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
    blue: "bg-blue-500",

  };


  const textColors = {

    green: "text-emerald-400",
    yellow: "text-yellow-400",
    red: "text-red-400",
    blue: "text-blue-400",

  };


  return (

    <div>

      <div className="flex justify-between items-center mb-2">

        <div className="flex items-center gap-2">

          <span
            className={`w-1.5 h-1.5 rounded-full ${colors[type]}`}
          />

          <span className="text-[9px] font-bold tracking-wider text-slate-400">
            {label}
          </span>

        </div>


        <span
          className={`text-[9px] font-bold ${textColors[type]}`}
        >
          {value} / {total}
        </span>

      </div>


      <div className="h-1 bg-slate-900 overflow-hidden">

        <div
          className={`h-full ${colors[type]} transition-all duration-700`}
          style={{
            width: `${percentage}%`,
          }}
        />

      </div>

    </div>

  );
}


/* =============================================================
   SYSTEM LINE
============================================================= */

function SystemLine({
  name,
  status,
}) {

  return (

    <div className="flex items-center justify-between border-b border-slate-800/70 pb-3">

      <div className="flex items-center gap-3">

        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />

        <span className="text-[9px] font-medium tracking-wider text-slate-400">
          {name}
        </span>

      </div>


      <span className="text-[8px] font-bold text-emerald-500">
        {status}
      </span>

    </div>

  );
}


/* =============================================================
   OFFICER ROW
============================================================= */

function OfficerRow({
  id,
  cases,
  clear,
  review,
  reject,
}) {

  return (

    <tr className="border-b border-slate-800/70 hover:bg-blue-500/[0.025] transition">

      <td className="px-6 py-4">

        <div className="flex items-center gap-3">

          <div className="w-8 h-8 bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">

            <span className="text-[10px] text-blue-400 font-bold">
              {String(id).charAt(0).toUpperCase()}
            </span>

          </div>


          <div>

            <p className="text-xs font-semibold text-slate-300">
              {id}
            </p>

            <p className="text-[8px] text-slate-600">
              SCREENING OFFICER
            </p>

          </div>

        </div>

      </td>


      <td className="px-4 text-xs text-slate-400">
        {String(cases).padStart(2, "0")}
      </td>


      <td className="px-4 text-xs text-emerald-400 font-semibold">
        {String(clear).padStart(2, "0")}
      </td>


      <td className="px-4 text-xs text-yellow-400 font-semibold">
        {String(review).padStart(2, "0")}
      </td>


      <td className="px-4 text-xs text-red-400 font-semibold">
        {String(reject).padStart(2, "0")}
      </td>


      <td className="px-6">

        <span className="inline-flex items-center gap-2 text-[8px] font-bold tracking-wider text-emerald-400">

          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />

          ACTIVE

        </span>

      </td>

    </tr>

  );
}


/* =============================================================
   RECENT ACTIVITY
============================================================= */

function Activity({
  officer,
  action,
  result,
  time,
}) {

  const resultUpper =
    String(result || "").toUpperCase();


  let resultClass =
    "text-slate-500";


  if (resultUpper === "CLEAR") {
    resultClass = "text-emerald-400";
  }

  else if (resultUpper === "REVIEW") {
    resultClass = "text-yellow-400";
  }

  else if (
    resultUpper === "REJECT" ||
    resultUpper === "REJECTED"
  ) {

    resultClass =
      "text-red-400";

  }


  return (

    <div className="py-4 border-b border-slate-800/70">

      <div className="flex items-start gap-3">

        <div className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />


        <div className="flex-1 min-w-0">

          <div className="flex justify-between gap-3">

            <p className="text-[10px] font-semibold text-slate-300 truncate">
              {officer}
            </p>

            <span
              className={`text-[8px] font-bold ${resultClass}`}
            >
              {resultUpper}
            </span>

          </div>


          <p className="text-[9px] text-slate-600 mt-1">
            CASE {action}
          </p>


          <p className="text-[8px] text-slate-700 mt-1">
            {time}
          </p>

        </div>

      </div>

    </div>

  );
}


/* =============================================================
   MINI METRIC
============================================================= */

function MiniMetric({
  label,
  value,
  green = false,
}) {

  return (

    <div>

      <p className="text-[8px] tracking-[0.15em] text-slate-600">
        {label}
      </p>

      <p
        className={`text-xl font-black mt-1 ${
          green
            ? "text-emerald-400"
            : "text-white"
        }`}
      >
        {value}
      </p>

    </div>

  );
}


/* =============================================================
   BUILD OFFICER STATISTICS
============================================================= */

function buildOfficerStats(logs) {

  const map = {};

  if (!Array.isArray(logs)) {
    return [];
  }


  logs.forEach((item) => {

    const officer =
      item?.officer_decision?.decided_by ||
      item?.officer ||
      item?.decided_by ||
      null;


    if (!officer) {
      return;
    }


    if (!map[officer]) {

      map[officer] = {

        id: officer,

        cases: 0,

        clear: 0,

        review: 0,

        reject: 0,

      };

    }


    map[officer].cases += 1;


    const decision =
      String(
        item?.officer_decision?.decision ||
        item?.officer_decision ||
        item?.decision ||
        ""
      ).toUpperCase();


    if (decision === "CLEAR") {

      map[officer].clear += 1;

    }

    else if (decision === "REVIEW") {

      map[officer].review += 1;

    }

    else if (
      decision === "REJECT" ||
      decision === "REJECTED"
    ) {

      map[officer].reject += 1;

    }

  });


  return Object.values(map);
}


/* =============================================================
   TIME FORMATTER
============================================================= */

function formatTime(value) {

  if (!value) {
    return "-";
  }


  const date =
    new Date(value);


  if (Number.isNaN(date.getTime())) {
    return "-";
  }


  return date.toLocaleString([], {

    day: "2-digit",

    month: "short",

    hour: "2-digit",

    minute: "2-digit",

  });

}