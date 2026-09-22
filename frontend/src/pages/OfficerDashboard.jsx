import { Link, useNavigate } from "react-router-dom";

export default function OfficerDashboard() {
  const navigate = useNavigate();

  const user = JSON.parse(
    localStorage.getItem("cyberfoxxx_user") || "{}"
  );

  function logout() {
    localStorage.removeItem("cyberfoxxx_user");
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">

      {/* =========================================================
          TOP NAVIGATION
      ========================================================= */}

      <header className="bg-slate-950 text-white border-b border-slate-800 shadow-lg">

        <div className="max-w-7xl mx-auto px-6 py-4">

          <div className="flex items-center justify-between">

            {/* Brand */}

            <div className="flex items-center gap-4">

              <div className="relative">

                <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/30">

                  <span className="text-xl font-black">
                    C
                  </span>

                </div>

                <span className="absolute -right-1 -bottom-1 w-3 h-3 bg-emerald-400 border-2 border-slate-950 rounded-full" />

              </div>

              <div>

                <h1 className="text-lg font-bold tracking-wide">
                  CYBERFOXXX
                </h1>

                <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">
                  Identity & Document Screening
                </p>

              </div>

            </div>


            {/* System indicator */}

            <div className="hidden md:flex items-center gap-6">

              <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-900 border border-slate-800">

                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />

                <span className="text-xs font-medium text-slate-300">
                  SYSTEM OPERATIONAL
                </span>

              </div>


              <div className="h-8 w-px bg-slate-800" />


              <div className="text-right">

                <p className="text-sm font-semibold">
                  {user.name || "Screening Officer"}
                </p>

                <p className="text-[11px] text-slate-400">
                  Officer ID: {user.id || "OFFCB-001"}
                </p>

              </div>


              <button
                onClick={logout}
                className="px-4 py-2 rounded-lg border border-slate-700 text-xs font-semibold text-slate-300 hover:bg-red-500/10 hover:border-red-500/40 hover:text-red-400 transition"
              >
                LOGOUT
              </button>

            </div>

          </div>

        </div>

      </header>


      {/* =========================================================
          MAIN CONTENT
      ========================================================= */}

      <main className="max-w-7xl mx-auto px-6 py-10">


        {/* Welcome section */}

        <section className="mb-10">

          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">

            <div>

              <div className="flex items-center gap-2 mb-3">

                <span className="px-2.5 py-1 rounded-md bg-blue-100 text-blue-700 text-[10px] font-bold tracking-wider">
                  OFFICER CONSOLE
                </span>

                <span className="text-xs text-slate-400">
                  SECURE SESSION
                </span>

              </div>

              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900">
                Welcome, {user.name || "Officer"}
              </h2>

              <p className="mt-2 text-sm text-slate-500 max-w-2xl">
                Conduct identity document screening, review automated
                risk assessments, and maintain a complete verification
                audit trail.
              </p>

            </div>


            {/* Security status */}

            <div className="flex items-center gap-3 bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm">

              <div className="w-9 h-9 rounded-lg bg-emerald-50 flex items-center justify-center">

                <span className="text-emerald-600 text-lg">
                  ✓
                </span>

              </div>

              <div>

                <p className="text-xs font-bold text-slate-700">
                  SECURE CONNECTION
                </p>

                <p className="text-[11px] text-slate-400">
                  Authenticated officer session
                </p>

              </div>

            </div>

          </div>

        </section>


        {/* =========================================================
            PRIMARY ACTIONS
        ========================================================= */}

        <section className="mb-10">

          <div className="flex items-center justify-between mb-4">

            <div>

              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Screening Operations
              </h3>

              <p className="text-xs text-slate-400 mt-1">
                Select an operation to continue
              </p>

            </div>

          </div>


          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">


            {/* Upload Document */}

            <ActionCard
              icon="⌁"
              title="Document Screening"
              description="Upload a passport, visa, identity document, or supported file to initiate the CYBERFOXXX verification pipeline."
              to="/screen"
              primary
            />


            {/* Audit */}

            <ActionCard
              icon="≡"
              title="Audit & Decision History"
              description="Review screening activity, officer decisions, verification events, and system audit records."
              to="/audit"
            />

          </div>

        </section>


        {/* =========================================================
            SYSTEM OVERVIEW
        ========================================================= */}

        <section className="mb-10">

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">

            {/* Section header */}

            <div className="px-6 py-5 border-b border-slate-200 flex items-center justify-between">

              <div>

                <h3 className="font-bold text-slate-800">
                  CYBERFOXXX System Status
                </h3>

                <p className="text-xs text-slate-400 mt-1">
                  Real-time availability of core screening services
                </p>

              </div>

              <div className="flex items-center gap-2">

                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />

                <span className="text-xs font-semibold text-emerald-600">
                  ALL SYSTEMS NOMINAL
                </span>

              </div>

            </div>


            {/* Status cards */}

            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-slate-200">

              <SystemStatus
                title="Risk Engine"
                description="Risk calibration & decision analysis"
                code="RISK-ENGINE"
              />

              <SystemStatus
                title="OCR Engine"
                description="Document text & MRZ extraction"
                code="OCR-ENGINE"
              />

              <SystemStatus
                title="Tamper Detection"
                description="Document authenticity analysis"
                code="TAMPER-ENGINE"
              />

            </div>

          </div>

        </section>


        {/* =========================================================
            SECURITY NOTICE
        ========================================================= */}

        <section>

          <div className="bg-slate-950 rounded-2xl p-6 text-white shadow-xl relative overflow-hidden">

            {/* Decorative background */}

            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl" />

            <div className="relative flex flex-col md:flex-row md:items-center gap-5">

              <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-400/20 flex items-center justify-center flex-shrink-0">

                <span className="text-blue-400 text-xl">
                  !
                </span>

              </div>

              <div>

                <h3 className="font-semibold text-white">
                  Officer Security Notice
                </h3>

                <p className="text-sm text-slate-400 mt-1 leading-relaxed">
                  All screening operations, officer decisions, identity
                  verification events, and audit activities are recorded
                  within the CYBERFOXXX security workflow.
                </p>

              </div>

            </div>

          </div>

        </section>


        {/* Mobile logout */}

        <div className="md:hidden mt-6">

          <button
            onClick={logout}
            className="w-full py-3 rounded-xl border border-red-200 bg-white text-red-600 text-sm font-semibold hover:bg-red-50 transition"
          >
            Logout
          </button>

        </div>

      </main>


      {/* =========================================================
          FOOTER
      ========================================================= */}

      <footer className="border-t border-slate-200 bg-white">

        <div className="max-w-7xl mx-auto px-6 py-5 flex flex-col md:flex-row items-center justify-between gap-2">

          <p className="text-[11px] text-slate-400 uppercase tracking-wider">
            CYBERFOXXX • Identity & Document Screening Platform
          </p>

          <p className="text-[11px] text-slate-400">
            Authorized Officer Access
          </p>

        </div>

      </footer>

    </div>
  );
}


/* =============================================================
   ACTION CARD
============================================================= */

function ActionCard({
  icon,
  title,
  description,
  to,
  primary = false,
}) {
  return (
    <Link
      to={to}
      className={`group relative rounded-2xl p-7 border transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${
        primary
          ? "bg-slate-950 border-slate-800 text-white hover:shadow-blue-900/20"
          : "bg-white border-slate-200 text-slate-800 hover:border-blue-200"
      }`}
    >

      {/* Accent line */}

      <div
        className={`absolute left-0 top-6 bottom-6 w-1 rounded-r-full ${
          primary ? "bg-blue-500" : "bg-slate-200 group-hover:bg-blue-500"
        } transition-colors`}
      />


      <div className="flex items-start gap-5">

        {/* Icon */}

        <div
          className={`w-14 h-14 rounded-xl flex items-center justify-center text-2xl font-bold flex-shrink-0 transition ${
            primary
              ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20"
              : "bg-slate-100 text-slate-600 group-hover:bg-blue-50 group-hover:text-blue-600"
          }`}
        >
          {icon}
        </div>


        <div className="flex-1">

          <div className="flex items-center justify-between gap-3">

            <h3
              className={`text-lg font-bold ${
                primary ? "text-white" : "text-slate-800"
              }`}
            >
              {title}
            </h3>

            <span
              className={`text-lg transition-transform group-hover:translate-x-1 ${
                primary ? "text-blue-400" : "text-slate-300"
              }`}
            >
              →
            </span>

          </div>

          <p
            className={`text-sm leading-relaxed mt-2 ${
              primary ? "text-slate-400" : "text-slate-500"
            }`}
          >
            {description}
          </p>


          <div
            className={`mt-5 text-[10px] font-bold tracking-[0.15em] ${
              primary ? "text-blue-400" : "text-blue-600"
            }`}
          >
            ACCESS MODULE
          </div>

        </div>

      </div>

    </Link>
  );
}


/* =============================================================
   SYSTEM STATUS
============================================================= */

function SystemStatus({
  title,
  description,
  code,
}) {
  return (
    <div className="p-6 group hover:bg-slate-50 transition">

      <div className="flex items-start justify-between">

        <div>

          <p className="text-[10px] font-bold tracking-wider text-slate-400">
            {code}
          </p>

          <h4 className="font-semibold text-slate-800 mt-1">
            {title}
          </h4>

        </div>


        <div className="flex items-center gap-2">

          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/40" />

          <span className="text-xs font-semibold text-emerald-600">
            ONLINE
          </span>

        </div>

      </div>


      <p className="text-xs text-slate-400 mt-3">
        {description}
      </p>


      <div className="mt-5 h-1 rounded-full bg-slate-100 overflow-hidden">

        <div className="h-full w-full bg-emerald-500 rounded-full" />

      </div>


      <p className="text-[10px] text-slate-400 mt-2">
        Service availability: Operational
      </p>

    </div>
  );
}