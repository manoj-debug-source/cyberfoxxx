import { useEffect, useState } from "react";
import { getAuditLogs } from "../api/client";

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadAuditLogs();
  }, []);

  async function loadAuditLogs() {
    try {
      setLoading(true);
      setError("");

      const data = await getAuditLogs();

      console.log("AUDIT LOG DATA:", data);

      // Backend returns { items: [...] }
      setLogs(data?.items || []);
    } catch (err) {
      console.error("AUDIT LOG ERROR:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to load audit logs."
      );
    } finally {
      setLoading(false);
    }
  }

  function getDecisionClass(decision) {
    if (decision === "CLEAR") {
      return "bg-green-100 text-green-700";
    }

    if (decision === "REVIEW") {
      return "bg-yellow-100 text-yellow-700";
    }

    if (
      decision === "REJECTED" ||
      decision === "REJECT"
    ) {
      return "bg-red-100 text-red-700";
    }

    return "bg-gray-100 text-gray-600";
  }

  function formatDate(value) {
    if (!value) return "—";

    try {
      return new Date(value).toLocaleString();
    } catch {
      return "—";
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-8">

      {/* HEADER */}
      <div className="max-w-7xl mx-auto mb-8">

        <div className="flex items-center justify-between">

          <div>
            <h1 className="text-3xl font-bold text-slate-800">
              Audit Log
            </h1>

            <p className="text-gray-500 mt-1">
              Complete screening history with AI and officer decisions
            </p>
          </div>

          <button
            onClick={loadAuditLogs}
            className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700"
          >
            Refresh
          </button>

        </div>

      </div>

      {/* ERROR */}
      {error && (
        <div className="max-w-7xl mx-auto mb-6">
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4">
            <p className="font-semibold">
              Failed to load audit log
            </p>

            <p className="text-sm mt-1">
              {error}
            </p>
          </div>
        </div>
      )}

      {/* LOADING */}
      {loading ? (

        <div className="max-w-7xl mx-auto">
          <div className="bg-white rounded-xl shadow p-10 text-center">

            <div className="text-gray-500">
              Loading audit logs...
            </div>

          </div>
        </div>

      ) : (

        <div className="max-w-7xl mx-auto">

          {/* SUMMARY */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">

            <div className="bg-white rounded-xl shadow p-5">
              <p className="text-sm text-gray-500">
                Total Screenings
              </p>

              <p className="text-2xl font-bold text-slate-800 mt-1">
                {logs.length}
              </p>
            </div>

            <div className="bg-white rounded-xl shadow p-5">
              <p className="text-sm text-gray-500">
                Clear
              </p>

              <p className="text-2xl font-bold text-green-600 mt-1">
                {
                  logs.filter(
                    (log) =>
                      log.officer_decision === "CLEAR"
                  ).length
                }
              </p>
            </div>

            <div className="bg-white rounded-xl shadow p-5">
              <p className="text-sm text-gray-500">
                Review
              </p>

              <p className="text-2xl font-bold text-yellow-600 mt-1">
                {
                  logs.filter(
                    (log) =>
                      log.officer_decision === "REVIEW"
                  ).length
                }
              </p>
            </div>

            <div className="bg-white rounded-xl shadow p-5">
              <p className="text-sm text-gray-500">
                Rejected
              </p>

              <p className="text-2xl font-bold text-red-600 mt-1">
                {
                  logs.filter(
                    (log) =>
                      log.officer_decision === "REJECTED" ||
                      log.officer_decision === "REJECT"
                  ).length
                }
              </p>
            </div>

          </div>

          {/* TABLE */}
          <div className="bg-white rounded-xl shadow overflow-hidden">

            <div className="overflow-x-auto">

              <table className="w-full text-sm">

                <thead className="bg-slate-100 border-b">

                  <tr>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      Screening ID
                    </th>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      Risk Score
                    </th>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      AI Decision
                    </th>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      Officer Decision
                    </th>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      Officer
                    </th>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      Blockchain
                    </th>

                    <th className="text-left px-5 py-4 font-semibold text-slate-700">
                      Time
                    </th>

                  </tr>

                </thead>

                <tbody>

                  {logs.length === 0 ? (

                    <tr>

                      <td
                        colSpan="7"
                        className="text-center px-5 py-12 text-gray-500"
                      >
                        No audit records found.
                      </td>

                    </tr>

                  ) : (

                    logs.map((log, index) => (

                      <tr
                        key={
                          log.screening_id || index
                        }
                        className="border-b hover:bg-gray-50"
                      >

                        {/* SCREENING ID */}
                        <td className="px-5 py-4">

                          <span className="font-mono font-semibold text-slate-700">
                            {log.screening_id || "—"}
                          </span>

                        </td>

                        {/* RISK SCORE */}
                        <td className="px-5 py-4">

                          {typeof log.risk_score ===
                          "number"
                            ? log.risk_score.toFixed(3)
                            : "—"}

                        </td>

                        {/* AI DECISION */}
                        <td className="px-5 py-4">

                          {log.decision ? (

                            <span
                              className={`px-3 py-1 rounded-full text-xs font-semibold ${getDecisionClass(
                                log.decision
                              )}`}
                            >
                              {log.decision}
                            </span>

                          ) : (

                            <span className="text-gray-400">
                              Pending
                            </span>

                          )}

                        </td>

                        {/* OFFICER DECISION */}
                        <td className="px-5 py-4">

                          {log.officer_decision ? (

                            <span
                              className={`px-3 py-1 rounded-full text-xs font-semibold ${getDecisionClass(
                                log.officer_decision
                              )}`}
                            >
                              {log.officer_decision}
                            </span>

                          ) : (

                            <span className="text-gray-400">
                              Pending
                            </span>

                          )}

                        </td>

                        {/* OFFICER */}
                        <td className="px-5 py-4">

                          {log.officer ? (
                            <span className="font-medium">
                              {log.officer}
                            </span>
                          ) : (
                            "—"
                          )}

                        </td>

                        {/* BLOCKCHAIN */}
                        <td className="px-5 py-4">

                          {log.on_chain ? (

                            <span className="text-green-600 font-semibold">
                              ✓ Recorded
                            </span>

                          ) : (

                            <span className="text-gray-400">
                              Pending
                            </span>

                          )}

                        </td>

                        {/* TIME */}
                        <td className="px-5 py-4 whitespace-nowrap text-gray-600">
                          {formatDate(log.timestamp)}
                        </td>

                      </tr>

                    ))

                  )}

                </tbody>

              </table>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}