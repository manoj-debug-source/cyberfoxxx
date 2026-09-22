import { useEffect, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  getScan,
  getRiskScore,
  submitScreeningDecision,
} from "../api/client";

/* =========================================================
   HELPERS
========================================================= */

function formatRisk(value) {
  const number = Number(value);

  if (Number.isNaN(number)) {
    return "—";
  }

  /*
   * Backend calibrated_risk is normally 0–1.
   * Display as percentage out of 100.
   */
  return `${(number * 100).toFixed(2)}/100`;
}

function formatPercentage(value) {
  const number = Number(value);

  if (Number.isNaN(number)) {
    return "—";
  }

  /*
   * Backend probability is normally 0–1.
   */
  if (number <= 1) {
    return `${(number * 100).toFixed(2)}%`;
  }

  return `${number.toFixed(2)}%`;
}

function deriveDecision(riskLevel) {
  const level = String(riskLevel || "")
    .toUpperCase()
    .trim();

  if (level === "LOW") return "CLEAR";
  if (level === "MEDIUM") return "REVIEW";
  if (level === "HIGH") return "REJECTED";
  if (level === "CRITICAL") return "REJECTED";

  return "PENDING";
}

function decisionDescription(decision) {
  const normalized = String(decision || "")
    .toUpperCase()
    .trim();

  switch (normalized) {
    case "CLEAR":
      return "Low-risk document. No immediate concern identified.";

    case "REVIEW":
      return "Medium-risk document. Requires secondary inspection.";

    case "REJECT":
    case "REJECTED":
      return "High or critical risk. Significant concerns identified.";

    default:
      return "Automated decision is not available yet.";
  }
}

/* =========================================================
   OFFICER REVIEW
========================================================= */

export default function OfficerReview() {
  const { scanId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  /* =======================================================
     STATE
  ======================================================= */

  const [scan, setScan] = useState(
    location.state?.scanResult || null
  );

  const [risk, setRisk] = useState(
    location.state?.riskResult?.risk ||
      location.state?.riskResult ||
      null
  );

  const [decision, setDecision] = useState("");

  const [remarks, setRemarks] = useState("");

  const [loading, setLoading] = useState(
    !location.state?.scanResult
  );

  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState("");

  /* =======================================================
     LOAD CURRENT SCREENING
  ======================================================= */

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      try {
        setLoading(true);
        setError("");

        const scanData = await getScan(scanId);

        if (!mounted) return;

        setScan(scanData);

        try {
          const riskData = await getRiskScore(scanId);

          if (!mounted) return;

          setRisk(
            riskData?.risk ||
              scanData?.risk ||
              scanData?.pipeline?.risk?.result ||
              null
          );
        } catch (riskError) {
          console.warn(
            "Risk endpoint unavailable:",
            riskError
          );

          if (mounted) {
            setRisk(
              scanData?.risk ||
                scanData?.pipeline?.risk?.result ||
                null
            );
          }
        }
      } catch (err) {
        console.error(
          "OFFICER REVIEW LOAD ERROR:",
          err
        );

        if (mounted) {
          setError(
            err?.response?.data?.detail ||
              err?.response?.data?.message ||
              err?.message ||
              "Could not load screening information."
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    if (!scanId) {
      setError("Missing screening ID.");
      setLoading(false);
      return;
    }

    loadData();

    return () => {
      mounted = false;
    };
  }, [scanId]);

  /* =======================================================
     EXTRACT BACKEND DATA
  ======================================================= */

  const pipeline = scan?.pipeline || {};

  const tamper =
    pipeline?.tamper?.result ||
    scan?.tamper_analysis ||
    scan?.tamper ||
    null;

  const calibratedRisk =
    risk?.calibrated_risk ??
    risk?.risk_score ??
    pipeline?.risk?.result?.calibrated_risk ??
    null;

  const riskLevel = String(
    risk?.risk_level ||
      risk?.level ||
      pipeline?.risk?.result?.risk_level ||
      "-"
  ).toUpperCase();

  const rawAiDecision =
    scan?.ai_decision ??
    pipeline?.decision?.decision ??
    pipeline?.decision?.result?.decision ??
    risk?.decision ??
    "";

  const aiDecision =
    typeof rawAiDecision === "string"
      ? rawAiDecision.trim().toUpperCase()
      : "";

  const tamperProbability =
    tamper?.tamper_probability ??
    tamper?.probability ??
    null;

  const tamperPrediction =
    tamper?.prediction ||
    tamper?.tamper_prediction ||
    "-";

  const officerDecision =
    scan?.officer_decision || null;

  /* =======================================================
     EXISTING DECISION
  ======================================================= */

  const normalizedOfficerDecision =
    typeof officerDecision === "string"
      ? {
          decision: officerDecision,
        }
      : officerDecision;

  const alreadyDecided =
    !!normalizedOfficerDecision?.decision;

  /* =======================================================
     SUBMIT OFFICER DECISION
  ======================================================= */

  async function handleSubmit() {
    if (!decision) {
      setError(
        "Please select CLEAR, REVIEW, or REJECT."
      );
      return;
    }

    /*
     * Backend stores REJECT as REJECTED.
     */

    const backendDecision =
      decision === "REJECT"
        ? "REJECTED"
        : decision;

    try {
      setSubmitting(true);
      setError("");

      console.log(
        "SUBMITTING OFFICER DECISION:",
        {
          screeningId: scanId,
          decision: backendDecision,
          remarks,
        }
      );

      /*
       * IMPORTANT:
       *
       * submitScreeningDecision expects:
       *
       * submitScreeningDecision(
       *   screeningId,
       *   { decision: "CLEAR" }
       * )
       *
       * Do NOT pass the decision string directly.
       */

      await submitScreeningDecision(
        scanId,
        {
          decision: backendDecision,
          notes: remarks,
        }
      );

      /*
       * Officer decision is now complete.
       *
       * Next:
       *
       * Officer Decision
       *       ↓
       * Identity Linkage
       */

      navigate(
        `/identity-linkage/${encodeURIComponent(
          scanId
        )}`,
        {
          replace: true,
        }
      );
    } catch (err) {
      console.error(
        "OFFICER DECISION ERROR:",
        err
      );

      setError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "Could not submit officer decision."
      );
    } finally {
      setSubmitting(false);
    }
  }

  /* =========================================================
     LOADING
  ========================================================= */

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center px-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="mx-auto mb-5 w-12 h-12 rounded-full border-4 border-gray-200 border-t-blue-600 animate-spin" />

          <p className="text-gray-500">
            Loading screening assessment…
          </p>
        </div>
      </div>
    );
  }

  /* =========================================================
     ERROR
  ========================================================= */

  if (error && !scan) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center px-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center max-w-lg w-full">
          <h2 className="text-xl font-bold text-slate-900">
            Unable to Load Review
          </h2>

          <p className="text-red-600 mt-3">
            {error}
          </p>

          <button
            type="button"
            onClick={() =>
              navigate("/officer")
            }
            className="mt-6 bg-slate-900 text-white px-5 py-3 rounded-xl font-semibold"
          >
            ← Back to Officer Dashboard
          </button>
        </div>
      </div>
    );
  }

  /* =========================================================
     PAGE
  ========================================================= */

  return (
    <div className="min-h-screen bg-slate-100 py-8">
      <div className="max-w-5xl mx-auto px-4 md:px-6">

        {/* =================================================
            HEADER
        ================================================= */}

        <div className="mb-8">
          <p className="text-xs uppercase tracking-wider text-gray-400">
            CYBERFOXXX AI SYSTEM
          </p>

          <h1 className="text-2xl md:text-3xl font-bold text-blue-800 mt-1">
            Officer Review
          </h1>

          <p className="text-sm text-gray-500 mt-1">
            Final authorized review for screening case{" "}
            <strong>{scanId}</strong>
          </p>
        </div>

        {/* =================================================
            ERROR BANNER
        ================================================= */}

        {error && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4">
            <p className="text-sm font-medium text-red-700">
              ⚠ {error}
            </p>
          </div>
        )}

        {/* =================================================
            AUTOMATED ASSESSMENT
        ================================================= */}

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-6">

          <h2 className="font-semibold text-blue-800 mb-5">
            Automated Screening Assessment
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">

            <Info
              label="Calibrated Risk"
              value={formatRisk(calibratedRisk)}
            />

            <Info
              label="Risk Level"
              value={riskLevel}
            />

            <Info
              label="AI Decision"
              value={aiDecision || "PENDING"}
            />

            <Info
              label="Tamper Probability"
              value={formatPercentage(
                tamperProbability
              )}
            />

          </div>

          {/* =================================================
              TAMPER PREDICTION
          ================================================= */}

          <div className="mt-5 rounded-xl bg-slate-50 border border-slate-200 p-4">

            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">

              <div>
                <p className="text-xs text-gray-500">
                  Tamper Detection
                </p>

                <p
                  className={`font-bold mt-1 ${
                    String(
                      tamperPrediction
                    ).toLowerCase() === "tampered"
                      ? "text-red-600"
                      : "text-green-600"
                  }`}
                >
                  {String(
                    tamperPrediction
                  ).toUpperCase()}
                </p>
              </div>

              <div className="text-left sm:text-right">
                <p className="text-xs text-gray-500">
                  Model confidence
                </p>

                <p className="font-semibold text-gray-800 mt-1">
                  {tamperProbability !== null
                    ? formatPercentage(
                        tamperProbability
                      )
                    : "—"}
                </p>
              </div>

            </div>
          </div>

          {/* =================================================
              AI EXPLANATION
          ================================================= */}

          <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50 p-4">

            <p className="text-sm font-semibold text-blue-800">
              AI Decision Explanation
            </p>

            <p className="text-sm text-gray-600 mt-1">
              {decisionDescription(
                aiDecision
              )}
            </p>

          </div>
        </div>

        {/* =================================================
            EXISTING OFFICER DECISION
        ================================================= */}

        {alreadyDecided && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-6">

            <h2 className="font-semibold text-blue-800">
              Officer Decision Already Recorded
            </h2>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">

              <Info
                label="Decision"
                value={
                  normalizedOfficerDecision.decision
                }
              />

              <Info
                label="Officer"
                value={
                  normalizedOfficerDecision.decided_by ||
                  "Unknown"
                }
              />

              <Info
                label="Status"
                value="RECORDED"
              />

            </div>

            <p className="text-sm text-gray-500 mt-5">
              This decision cannot be changed through
              the current officer workflow.
            </p>

            <button
              type="button"
              onClick={() =>
                navigate(
                  `/identity-linkage/${encodeURIComponent(
                    scanId
                  )}`
                )
              }
              className="mt-5 bg-blue-800 text-white px-5 py-3 rounded-xl font-semibold hover:bg-blue-900"
            >
              Continue to Identity Linkage →
            </button>
          </div>
        )}

        {/* =================================================
            FINAL DECISION
        ================================================= */}

        {!alreadyDecided && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">

            <h2 className="font-semibold text-blue-800 mb-2">
              Final Officer Decision
            </h2>

            <p className="text-sm text-gray-500 mb-6">
              The automated system provides decision support.
              The authorized officer makes the final decision.
            </p>

            {/* =================================================
                DECISION BUTTONS
            ================================================= */}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              <DecisionButton
                active={
                  decision === "CLEAR"
                }
                onClick={() =>
                  setDecision("CLEAR")
                }
                title="CLEAR"
                description="Document appears valid and does not require further action."
                activeClass="border-green-500 bg-green-50"
                titleClass="text-green-600"
              />

              <DecisionButton
                active={
                  decision === "REVIEW"
                }
                onClick={() =>
                  setDecision("REVIEW")
                }
                title="REVIEW"
                description="Send the document for secondary inspection."
                activeClass="border-yellow-500 bg-yellow-50"
                titleClass="text-yellow-600"
              />

              <DecisionButton
                active={
                  decision === "REJECT"
                }
                onClick={() =>
                  setDecision("REJECT")
                }
                title="REJECT"
                description="Reject the document because of significant concerns."
                activeClass="border-red-500 bg-red-50"
                titleClass="text-red-600"
              />

            </div>

            {/* =================================================
                REMARKS
            ================================================= */}

            <div className="mt-6">

              <label className="block text-sm font-medium text-gray-700 mb-2">
                Officer Remarks
              </label>

              <textarea
                value={remarks}
                onChange={(e) =>
                  setRemarks(e.target.value)
                }
                rows={5}
                placeholder="Enter your observations and reason for the decision..."
                className="w-full border border-gray-300 rounded-xl p-3 outline-none focus:ring-2 focus:ring-blue-200"
              />

            </div>

            {/* =================================================
                SUBMIT
            ================================================= */}

            <button
              type="button"
              onClick={handleSubmit}
              disabled={
                submitting ||
                !decision
              }
              className="mt-6 w-full bg-blue-800 text-white py-3 rounded-xl font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-900 transition"
            >
              {submitting
                ? "Submitting Decision..."
                : "SUBMIT OFFICER DECISION"}
            </button>

          </div>
        )}

        {/* =================================================
            FOOTER
        ================================================= */}

        <div className="flex justify-center mt-6">

          <Link
            to={`/results/${scanId}`}
            className="text-sm text-blue-800 underline"
          >
            ← Back to Results
          </Link>

        </div>

      </div>
    </div>
  );
}

/* =========================================================
   INFO
========================================================= */

function Info({
  label,
  value,
}) {
  return (
    <div className="border rounded-xl p-4 bg-white">

      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="text-lg font-bold text-gray-800 mt-1 break-words">
        {value}
      </p>

    </div>
  );
}

/* =========================================================
   DECISION BUTTON
========================================================= */

function DecisionButton({
  active,
  onClick,
  title,
  description,
  activeClass,
  titleClass,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left border-2 rounded-xl p-5 transition ${
        active
          ? activeClass
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >

      <div
        className={`font-bold ${
          active
            ? titleClass
            : "text-blue-800"
        }`}
      >
        {title}
      </div>

      <p className="text-xs text-gray-500 mt-2 leading-relaxed">
        {description}
      </p>

    </button>
  );
}