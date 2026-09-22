import { useEffect, useState } from "react";
import { useParams, useLocation, Link } from "react-router-dom";

import { getScan, getRiskScore } from "../api/client";
import PipelineStageCard from "../components/PipelineStageCard";


/* =========================================================
   HELPERS
========================================================= */

function normalizeStatus(status) {
  const value = String(status || "PENDING").toUpperCase();

  if (value === "COMPLETED") {
    return "clear";
  }

  if (value === "FAILED") {
    return "flagged";
  }

  if (value === "PROCESSING" || value === "RUNNING") {
    return "warning";
  }

  return "pending";
}


function statusLabel(status) {
  const value = String(status || "PENDING").toUpperCase();

  if (value === "COMPLETED") return "COMPLETED";
  if (value === "FAILED") return "FAILED";
  if (value === "PROCESSING") return "PROCESSING";
  if (value === "RUNNING") return "RUNNING";

  return "PENDING";
}


function getRiskLevelColor(level) {
  switch (String(level || "").toUpperCase()) {
    case "LOW":
      return "text-clear";

    case "MEDIUM":
      return "text-yellow-600";

    case "HIGH":
    case "CRITICAL":
      return "text-reject";

    default:
      return "text-gray-500";
  }
}


function deriveDecision(riskLevel) {
  const level = String(riskLevel || "").toUpperCase();

  if (level === "LOW") return "CLEAR";
  if (level === "MEDIUM") return "REVIEW";
  if (level === "HIGH") return "REJECTED";
  if (level === "CRITICAL") return "REJECTED";

  return "-";
}


function formatRiskScore(value) {
  const number = Number(value);

  if (Number.isNaN(number)) {
    return "-";
  }

  /*
   * Backend stores calibrated_risk as 0-1.
   * Example:
   * 0.1298 -> 12.98 / 100
   */
  return `${(number * 100).toFixed(2)}/100`;
}


/* =========================================================
   RISK ASSESSMENT PAGE
========================================================= */

export default function RiskAssessment() {
  const { scanId } = useParams();
  const location = useLocation();

  const [scan, setScan] = useState(
    location.state?.scanResult || null
  );

  const [risk, setRisk] = useState(null);

  const [loading, setLoading] = useState(
    !location.state?.scanResult
  );

  const [error, setError] = useState(null);


  /* =======================================================
     LOAD BACKEND DATA
  ======================================================= */

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        /*
         * Always refresh the scan from backend.
         *
         * This is important because the pipeline can contain
         * newer data than the object passed through navigation.
         */

        const scanData = await getScan(scanId);

        if (!mounted) return;

        setScan(scanData);

        /*
         * Risk endpoint returns:
         *
         * {
         *   success: true,
         *   screening_id: "...",
         *   risk: {
         *      calibrated_risk: 0.1298,
         *      risk_level: "LOW"
         *   }
         * }
         */

        try {
          const riskData = await getRiskScore(scanId);

          if (mounted) {
            setRisk(riskData?.risk || scanData?.risk || null);
          }
        } catch (riskError) {
          console.warn(
            "Risk endpoint unavailable. Using screening risk.",
            riskError
          );

          if (mounted) {
            setRisk(scanData?.risk || null);
          }
        }
      } catch (err) {
        console.error(err);

        if (mounted) {
          setError(
            err?.response?.data?.detail ||
              err?.message ||
              "Could not load pipeline data."
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, [scanId]);


  /* =======================================================
     LOADING
========================================================= */

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center px-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center">
          <div className="mx-auto mb-5 w-12 h-12 rounded-full border-4 border-gray-200 border-t-brand animate-spin" />

          <p className="text-gray-500">
            Loading risk assessment pipeline…
          </p>
        </div>
      </div>
    );
  }


  /* =======================================================
     ERROR
========================================================= */

  if (error) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center px-6">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 text-center max-w-lg w-full">

          <h2 className="text-xl font-bold text-slate-900">
            Pipeline Error
          </h2>

          <p className="text-reject mt-3">
            {error}
          </p>

          <Link
            to={`/results/${scanId}`}
            className="inline-block mt-6 bg-slate-900 text-white px-5 py-3 rounded-xl font-semibold"
          >
            ← Back to Results
          </Link>

        </div>
      </div>
    );
  }


  /* =======================================================
     PIPELINE DATA
========================================================= */

  const pipeline = scan?.pipeline || {};

  const sha256 = pipeline?.sha256 || {};
  const ocr = pipeline?.ocr || {};
  const mrz = pipeline?.mrz || {};
  const tamper = pipeline?.tamper || {};
  const anomaly = pipeline?.anomaly || {};
  const identityValidation =
    pipeline?.identity_validation || {};
  const face = pipeline?.face || {};
  const identityLinkage =
    pipeline?.identity_linkage || {};
  const riskPipeline = pipeline?.risk || {};
  const decisionPipeline =
    pipeline?.decision || {};


  /* =======================================================
     RISK RESULT
========================================================= */

  const riskResult =
    risk ||
    scan?.risk ||
    riskPipeline?.result ||
    null;

  const calibratedRisk =
    riskResult?.calibrated_risk;

  const riskLevel =
    riskResult?.risk_level ||
    "-";

  const aiDecision =
    scan?.ai_decision ||
    decisionPipeline?.decision ||
    deriveDecision(riskLevel);


  /* =======================================================
     TAMPER
========================================================= */

  const tamperResult =
    tamper?.result ||
    scan?.tamper_analysis ||
    scan?.tamper ||
    null;

  const tamperProbability =
    tamperResult?.tamper_probability;

  const tamperPercentage =
    tamperProbability !== undefined &&
    tamperProbability !== null
      ? Number(tamperProbability) * 100
      : null;

  const tamperPrediction =
    tamperResult?.prediction || "-";


  /* =======================================================
     OCR
========================================================= */

  const ocrResult = ocr?.result || null;

  const extractedFields =
    ocrResult?.fields ||
    scan?.fields ||
    {};

  const fieldCount =
    extractedFields &&
    typeof extractedFields === "object"
      ? Object.keys(extractedFields).length
      : 0;


  /* =======================================================
     STAGE DETAILS
========================================================= */

  const sha256Status =
    sha256?.status || "PENDING";

  const ocrStatus =
    ocr?.status || "PENDING";

  const mrzStatus =
    mrz?.status || "PENDING";

  const tamperStatus =
    tamper?.status || "PENDING";

  const anomalyStatus =
    anomaly?.status || "PENDING";

  const identityValidationStatus =
    identityValidation?.status || "PENDING";

  const faceStatus =
    face?.status || "PENDING";

  const identityLinkageStatus =
    identityLinkage?.status || "PENDING";

  const riskStatus =
    riskPipeline?.status || "PENDING";

  const decisionStatus =
    decisionPipeline?.status || "PENDING";


  /* =======================================================
     PAGE
========================================================= */

  return (
    <div className="min-h-screen bg-slate-100 py-8">

      <div className="max-w-4xl mx-auto px-4 md:px-6">

        {/* =================================================
            HEADER
        ================================================= */}

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">

          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-brand">
              Risk Assessment Pipeline
            </h1>

            <p className="text-sm text-gray-500 mt-1">
              Live backend screening analysis
            </p>
          </div>

          <Link
            to={`/results/${scanId}`}
            className="text-sm text-brand underline"
          >
            View full results →
          </Link>

        </div>


        {/* =================================================
            FINAL RISK SUMMARY
        ================================================= */}

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-7">

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">

            <div>
              <p className="text-sm text-gray-500">
                Calibrated Risk
              </p>

              <p className="text-4xl font-bold text-brand mt-1">
                {formatRiskScore(calibratedRisk)}
              </p>

              <p
                className={`text-lg font-bold mt-2 ${getRiskLevelColor(
                  riskLevel
                )}`}
              >
                {String(riskLevel).toUpperCase()}
              </p>
            </div>


            <div className="text-left md:text-right">

              <p className="text-sm text-gray-500">
                AI Decision
              </p>

              <p
                className={`text-2xl font-bold mt-1 ${
                  aiDecision === "CLEAR"
                    ? "text-clear"
                    : aiDecision === "REVIEW"
                    ? "text-yellow-600"
                    : aiDecision === "REJECTED" ||
                      aiDecision === "REJECT"
                    ? "text-reject"
                    : "text-gray-500"
                }`}
              >
                {aiDecision}
              </p>

              <p className="text-xs text-gray-400 mt-1">
                Status: {statusLabel(decisionStatus)}
              </p>

            </div>

          </div>


          {/* Risk progress bar */}

          {calibratedRisk !== undefined &&
            calibratedRisk !== null && (
              <div className="mt-6">

                <div className="flex justify-between text-xs text-gray-500 mb-2">
                  <span>Risk level</span>

                  <span>
                    {(Number(calibratedRisk) * 100).toFixed(2)}%
                  </span>
                </div>

                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">

                  <div
                    className={`h-full rounded-full ${
                      String(riskLevel).toUpperCase() === "LOW"
                        ? "bg-green-500"
                        : String(riskLevel).toUpperCase() ===
                          "MEDIUM"
                        ? "bg-yellow-500"
                        : "bg-red-500"
                    }`}
                    style={{
                      width: `${Math.min(
                        Math.max(
                          Number(calibratedRisk) * 100,
                          0
                        ),
                        100
                      )}%`,
                    }}
                  />

                </div>

              </div>
            )}

        </div>


        {/* =================================================
            PIPELINE STAGES
        ================================================= */}

        <div className="space-y-3">

          {/* =================================================
              SHA-256
          ================================================= */}

          <PipelineStageCard
            index={1}
            icon="🔐"
            title="SHA-256 Document Hash"
            subtitle="Cryptographic fingerprint generated for the uploaded document"
            status={normalizeStatus(sha256Status)}
            metric={
              sha256?.document_hash
                ? "Document hash generated"
                : "Hashing status from backend"
            }
            details={
              sha256?.document_hash
                ? [
                    {
                      text: `SHA-256: ${sha256.document_hash}`,
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              OCR
          ================================================= */}

          <PipelineStageCard
            index={2}
            icon="🔎"
            title="OCR Extraction"
            subtitle="PaddleOCR / Tesseract document text extraction"
            status={normalizeStatus(ocrStatus)}
            metric={
              ocrStatus === "COMPLETED"
                ? `${fieldCount} fields extracted`
                : "OCR stage not completed"
            }
            details={
              ocr?.error
                ? [
                    {
                      text: ocr.error,
                      flag: true,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              MRZ
          ================================================= */}

          <PipelineStageCard
            index={3}
            icon="🪪"
            title="MRZ Validation"
            subtitle="ICAO 9303 machine-readable zone checksum validation"
            status={normalizeStatus(mrzStatus)}
            metric={
              mrzStatus === "COMPLETED"
                ? "MRZ validation completed"
                : "MRZ stage not completed"
            }
            details={
              mrz?.result
                ? [
                    {
                      text: "MRZ validation result available",
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              TAMPER
          ================================================= */}

          <PipelineStageCard
            index={4}
            icon="🧬"
            title="Tamper Detection"
            subtitle="CNN-based document authenticity analysis"
            status={normalizeStatus(tamperStatus)}
            metric={
              tamperPercentage !== null
                ? `${tamperPercentage.toFixed(
                    2
                  )}% tamper probability`
                : "Tamper result not available"
            }
            details={
              tamperResult
                ? [
                    {
                      text: `Model prediction: ${tamperPrediction}`,
                      flag:
                        String(tamperPrediction).toLowerCase() ===
                        "tampered",
                    },
                    {
                      text: `Genuine probability: ${(
                        Number(
                          tamperResult.genuine_probability || 0
                        ) * 100
                      ).toFixed(2)}%`,
                      flag: false,
                    },
                    {
                      text: `Detection threshold: ${(
                        Number(
                          tamperResult.threshold || 0.5
                        ) * 100
                      ).toFixed(2)}%`,
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              ANOMALY
          ================================================= */}

          <PipelineStageCard
            index={5}
            icon="🧩"
            title="Anomaly Detection"
            subtitle="Detection of unusual document patterns"
            status={normalizeStatus(anomalyStatus)}
            metric={
              anomalyStatus === "COMPLETED"
                ? "Anomaly analysis completed"
                : "Anomaly stage not completed"
            }
            details={
              anomaly?.result
                ? [
                    {
                      text: "Anomaly result available",
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              IDENTITY VALIDATION
          ================================================= */}

          <PipelineStageCard
            index={6}
            icon="🆔"
            title="Identity Validation"
            subtitle="Validation of extracted identity information"
            status={normalizeStatus(
              identityValidationStatus
            )}
            metric={
              identityValidationStatus === "COMPLETED"
                ? "Identity validation completed"
                : "Identity validation not completed"
            }
            details={
              identityValidation?.result
                ? [
                    {
                      text: "Identity validation result available",
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              FACE
          ================================================= */}

          <PipelineStageCard
            index={7}
            icon="🧑"
            title="Face & Liveness Verification"
            subtitle="Face matching and liveness verification"
            status={normalizeStatus(faceStatus)}
            metric={
              faceStatus === "COMPLETED"
                ? "Face verification completed"
                : "Face verification not completed"
            }
            details={
              face?.result
                ? [
                    {
                      text: "Face verification result available",
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              IDENTITY LINKAGE
          ================================================= */}

          <PipelineStageCard
            index={8}
            icon="🔗"
            title="Identity Linkage"
            subtitle="Cross-checking identity relationships and duplicate identities"
            status={normalizeStatus(identityLinkageStatus)}
            metric={
              identityLinkageStatus === "COMPLETED"
                ? "Identity linkage completed"
                : "Identity linkage not completed"
            }
            details={
              identityLinkage?.result
                ? [
                    {
                      text: "Identity linkage result available",
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              RISK
          ================================================= */}

          <PipelineStageCard
            index={9}
            icon="⚖️"
            title="Risk Calibration"
            subtitle="Weighted calibration of available screening signals"
            status={normalizeStatus(riskStatus)}
            metric={
              riskResult
                ? `Calibrated risk: ${formatRiskScore(
                    calibratedRisk
                  )} • ${String(
                    riskLevel
                  ).toUpperCase()}`
                : "Risk result not available"
            }
            details={
              riskResult
                ? [
                    {
                      text: `Model: ${
                        riskResult.model_version ||
                        "risk-calibrator-v1"
                      }`,
                      flag: false,
                    },
                    {
                      text: `Calibration: ${
                        riskResult.calibration_method ||
                        "prototype-weighted-aggregation"
                      }`,
                      flag: false,
                    },
                  ]
                : []
            }
          />


          {/* =================================================
              AI DECISION
          ================================================= */}

          <PipelineStageCard
            index={10}
            icon="🤖"
            title="AI Decision"
            subtitle="Decision-support classification derived from calibrated risk"
            status={normalizeStatus(decisionStatus)}
            metric={
              aiDecision !== "-"
                ? `AI decision: ${aiDecision}`
                : "Decision not available"
            }
            details={[
              {
                text:
                  aiDecision === "CLEAR"
                    ? "Low calibrated risk — document classified as CLEAR."
                    : aiDecision === "REVIEW"
                    ? "Medium risk — secondary officer review required."
                    : aiDecision === "REJECTED" ||
                      aiDecision === "REJECT"
                    ? "High/critical risk — document classified as REJECTED."
                    : "Waiting for risk calibration.",
                flag:
                  aiDecision === "REJECTED" ||
                  aiDecision === "REJECT",
              },
            ]}
            isLast
          />

        </div>


        {/* =================================================
            OFFICER DECISION
        ================================================= */}

        {scan?.officer_decision && (
          <div className="mt-6 bg-white rounded-2xl shadow-sm border border-slate-200 p-6">

            <h2 className="text-lg font-bold text-brand">
              Officer Decision
            </h2>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">

              <div>
                <p className="text-xs text-gray-500">
                  Decision
                </p>

                <p className="font-bold mt-1">
                  {scan.officer_decision.decision}
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-500">
                  Officer
                </p>

                <p className="font-bold mt-1">
                  {scan.officer_decision.decided_by}
                </p>
              </div>

              <div>
                <p className="text-xs text-gray-500">
                  Status
                </p>

                <p className="font-bold mt-1 text-clear">
                  RECORDED
                </p>
              </div>

            </div>

          </div>
        )}


        {/* =================================================
            NAVIGATION
        ================================================= */}

        <div className="flex flex-col sm:flex-row justify-center gap-3 mt-8">

          <Link
            to={`/results/${scanId}`}
            className="text-center bg-white border border-slate-200 text-slate-800 px-5 py-3 rounded-xl font-semibold hover:bg-slate-50 transition"
          >
            ← Back to Results
          </Link>

          <Link
            to="/audit"
            className="text-center bg-slate-900 text-white px-5 py-3 rounded-xl font-semibold hover:bg-slate-800 transition"
          >
            View Audit Log →
          </Link>

        </div>


        {/* =================================================
            SCAN ID
        ================================================= */}

        <p className="text-center text-xs text-gray-400 mt-6">
          Scan ID: {scanId}
        </p>

      </div>
    </div>
  );
}