import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getScreening } from "../api/client";

/* =========================================================
   PIPELINE STAGES
========================================================= */

const STAGES = [
  {
    key: "sha256",
    label: "SHA-256 Hash",
    description: "Generating secure document fingerprint",
  },
  {
    key: "ocr",
    label: "OCR Extraction",
    description: "Extracting identity information from document",
  },
  {
    key: "mrz",
    label: "MRZ Validation",
    description: "Validating machine-readable zone data",
  },
  {
    key: "tamper",
    label: "Tamper Detection",
    description: "Checking document authenticity and manipulation",
  },
  {
    key: "anomaly",
    label: "Anomaly Detection",
    description: "Detecting unusual identity or document patterns",
  },
  {
    key: "identity_validation",
    label: "Identity Validation",
    description: "Validating extracted identity information",
  },
  {
    key: "face",
    label: "Face + Liveness",
    description: "Checking face match and liveness",
  },
  {
    key: "identity_linkage",
    label: "Identity Linkage",
    description: "Performed after officer final decision",
  },
  {
    key: "risk",
    label: "Risk Calibration",
    description: "Calculating overall screening risk",
  },
  {
    key: "decision",
    label: "AI Recommendation",
    description: "Generating CLEAR / REVIEW / REJECT recommendation",
  },
];

/* =========================================================
   STATUS HELPERS
========================================================= */

function normalizeStatus(status) {
  if (!status) {
    return "PENDING";
  }

  return String(status).toUpperCase();
}

function getStatusClass(status) {
  const normalized = normalizeStatus(status);

  if (normalized === "COMPLETED") {
    return "bg-green-100 text-green-700 border-green-200";
  }

  if (normalized === "PROCESSING") {
    return "bg-blue-100 text-blue-700 border-blue-200";
  }

  if (normalized === "FAILED") {
    return "bg-red-100 text-red-700 border-red-200";
  }

  if (normalized === "SKIPPED") {
    return "bg-gray-100 text-gray-600 border-gray-200";
  }

  return "bg-yellow-100 text-yellow-700 border-yellow-200";
}

function getStatusLabel(status) {
  const normalized = normalizeStatus(status);

  if (normalized === "COMPLETED") {
    return "COMPLETED";
  }

  if (normalized === "PROCESSING") {
    return "PROCESSING";
  }

  if (normalized === "FAILED") {
    return "FAILED";
  }

  if (normalized === "SKIPPED") {
    return "SKIPPED";
  }

  return "PENDING";
}

/* =========================================================
   PERCENT FORMATTER
========================================================= */

function formatPercent(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const number = Number(value);

  if (Number.isNaN(number)) {
    return null;
  }

  const normalized =
    number <= 1
      ? number * 100
      : number;

  return `${normalized.toFixed(2)}%`;
}

/* =========================================================
   STAGE DATA RESOLVER
========================================================= */

/*
 * IMPORTANT:
 *
 * Backend may contain BOTH:
 *
 * screening.pipeline.anomaly
 *
 * AND
 *
 * screening.anomaly
 *
 * The pipeline object can contain an old PENDING placeholder
 * even though the real top-level result is already completed.
 *
 * Therefore:
 *
 * 1. Prefer a COMPLETED pipeline stage.
 * 2. Otherwise check the actual top-level result.
 * 3. Only then fall back to the pipeline PENDING state.
 */

function getStageData(screening, stageKey) {
  const pipelineStage =
    screening?.pipeline?.[stageKey];

  const pipelineStatus =
    normalizeStatus(
      pipelineStage?.status
    );

  /* =======================================================
     SHA-256
  ======================================================= */

  if (stageKey === "sha256") {
    if (screening?.document_hash) {
      return {
        status: "COMPLETED",
        document_hash:
          screening.document_hash,
        result: screening.document_hash,
      };
    }
  }

  /* =======================================================
     ANOMALY
  ======================================================= */

  if (stageKey === "anomaly") {
    const anomaly =
      screening?.anomaly ||
      screening?.anomaly_analysis ||
      pipelineStage?.result;

    if (anomaly) {
      return {
        status: "COMPLETED",

        score:
          anomaly.anomaly_score ??
          anomaly.score,

        confidence:
          anomaly.confidence,

        severity:
          anomaly.severity,

        decision:
          anomaly.decision,

        is_anomaly:
          anomaly.is_anomaly,

        tampering_detected:
          anomaly.tampering_detected,

        validation_failed:
          anomaly.validation_failed,

        detected_fraud_types:
          anomaly.detected_fraud_types,

        evidence:
          anomaly.evidence,

        recommended_action:
          anomaly.recommended_action,

        result: anomaly,
      };
    }
  }

  /* =======================================================
     OCR
  ======================================================= */

  if (stageKey === "ocr") {
    if (screening?.ocr) {
      return {
        status: "COMPLETED",
        result: screening.ocr,
      };
    }

    if (screening?.ocr_result) {
      return {
        status: "COMPLETED",
        result: screening.ocr_result,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     MRZ
  ======================================================= */

  if (stageKey === "mrz") {
    if (screening?.mrz) {
      return {
        status: "COMPLETED",
        result: screening.mrz,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     TAMPER
  ======================================================= */

  if (stageKey === "tamper") {
    const tamper =
      screening?.tamper_analysis ||
      screening?.tamper;

    if (tamper) {
      return {
        status: "COMPLETED",
        result: tamper,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     IDENTITY VALIDATION
  ======================================================= */

  if (stageKey === "identity_validation") {
    if (screening?.identity_validation) {
      return {
        status: "COMPLETED",
        result:
          screening.identity_validation,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     FACE
  ======================================================= */

  if (stageKey === "face") {
    const face =
      screening?.face_analysis ||
      screening?.face;

    if (face) {
      return {
        status: "COMPLETED",
        result: face,
        confidence:
          face.confidence ??
          face.face_match_probability ??
          face.match_probability,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     IDENTITY LINKAGE
  ======================================================= */

  if (stageKey === "identity_linkage") {
    if (screening?.identity_linkage) {
      return {
        status: "COMPLETED",
        result:
          screening.identity_linkage,
      };
    }

    /*
     * Identity linkage intentionally remains PENDING
     * until the officer makes the final decision.
     */
  }

  /* =======================================================
     RISK
  ======================================================= */

  if (stageKey === "risk") {
    if (screening?.risk) {
      return {
        status: "COMPLETED",
        result: screening.risk,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     AI DECISION
  ======================================================= */

  if (stageKey === "decision") {
    const aiDecision =
      screening?.ai_decision;

    if (aiDecision) {
      return {
        status: "COMPLETED",
        decision: aiDecision,
        result: aiDecision,
      };
    }

    if (
      pipelineStage?.result &&
      pipelineStatus === "COMPLETED"
    ) {
      return pipelineStage;
    }
  }

  /* =======================================================
     FALLBACK TO PIPELINE
  ======================================================= */

  if (pipelineStage) {
    return pipelineStage;
  }

  /* =======================================================
     DEFAULT
  ======================================================= */

  return {
    status: "PENDING",
  };
}

/* =========================================================
   TAMPER PROBABILITY
========================================================= */

function extractTamperProbability(screening) {
  const probability =
    screening?.tamper_analysis
      ?.tamper_probability ??
    screening?.tamper
      ?.tamper_probability ??
    screening?.pipeline
      ?.tamper
      ?.result
      ?.tamper_probability;

  return formatPercent(probability);
}

/* =========================================================
   ANOMALY SCORE
========================================================= */

function extractAnomalyScore(screening) {
  const anomaly =
    screening?.anomaly ||
    screening?.anomaly_analysis ||
    screening?.pipeline
      ?.anomaly
      ?.result;

  if (!anomaly) {
    return null;
  }

  return formatPercent(
    anomaly.anomaly_score ??
      anomaly.score
  );
}

/* =========================================================
   RISK
========================================================= */

function extractRisk(screening) {
  const risk =
    screening?.risk
      ?.calibrated_risk ??
    screening?.risk
      ?.risk_score ??
    screening?.risk
      ?.score;

  if (
    risk === null ||
    risk === undefined
  ) {
    return null;
  }

  const number = Number(risk);

  if (Number.isNaN(number)) {
    return null;
  }

  return number <= 1
    ? `${(
        number * 100
      ).toFixed(2)}/100`
    : `${number.toFixed(2)}/100`;
}

function extractRiskLevel(screening) {
  return (
    screening?.risk
      ?.risk_level ||
    screening?.risk?.level ||
    null
  );
}

/* =========================================================
   PIPELINE STAGE COMPONENT
========================================================= */

function PipelineStage({
  stage,
  stageData,
}) {
  const status =
    normalizeStatus(
      stageData?.status
    );

  const anomalyResult =
    stage.key === "anomaly"
      ? stageData?.result
      : null;

  return (
    <div className="flex items-start gap-4">

      {/* ICON */}

      <div className="flex flex-col items-center">

        <div
          className={`w-10 h-10 rounded-full border flex items-center justify-center font-bold ${getStatusClass(
            status
          )}`}
        >
          {status === "COMPLETED" && "✓"}
          {status === "PROCESSING" && "…"}
          {status === "FAILED" && "!"}
          {status === "SKIPPED" && "—"}
          {status === "PENDING" && "○"}
        </div>

        {stage.key !== "decision" && (
          <div className="w-px h-10 bg-gray-200 mt-2" />
        )}

      </div>

      {/* CONTENT */}

      <div className="flex-1 pb-8">

        <div className="flex items-center justify-between gap-4">

          <div>

            <h3 className="font-semibold text-gray-900">
              {stage.label}
            </h3>

            <p className="text-sm text-gray-500 mt-1">
              {stage.description}
            </p>

          </div>

          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold border whitespace-nowrap ${getStatusClass(
              status
            )}`}
          >
            {getStatusLabel(status)}
          </span>

        </div>

        {/* CONFIDENCE */}

        {stageData?.confidence !==
          undefined &&
          stageData?.confidence !==
            null && (

          <div className="mt-2 text-sm text-gray-600">

            Confidence:{" "}

            <span className="font-semibold">
              {formatPercent(
                stageData.confidence
              )}
            </span>

          </div>
        )}

        {/* DOCUMENT NUMBER */}

        {stageData?.result
          ?.document_number && (

          <div className="mt-2 text-sm text-gray-600">

            Document Number:{" "}

            <span className="font-semibold">
              {
                stageData.result
                  .document_number
              }
            </span>

          </div>
        )}

        {/* ANOMALY DETAILS */}

        {stage.key ===
          "anomaly" &&
          anomalyResult && (

          <div className="mt-3 space-y-2">

            {anomalyResult.anomaly_score !==
              undefined && (

              <div className="text-sm text-gray-600">

                Anomaly Score:{" "}

                <strong>
                  {formatPercent(
                    anomalyResult.anomaly_score
                  )}
                </strong>

              </div>
            )}

            {anomalyResult.severity && (

              <div className="text-sm text-gray-600">

                Severity:{" "}

                <strong>
                  {anomalyResult.severity}
                </strong>

              </div>
            )}

            {anomalyResult.decision && (

              <div className="text-sm text-gray-600">

                Decision:{" "}

                <strong>
                  {anomalyResult.decision}
                </strong>

              </div>
            )}

            {anomalyResult.tampering_detected !==
              undefined && (

              <div className="text-sm text-gray-600">

                Tampering:{" "}

                <strong>
                  {anomalyResult.tampering_detected
                    ? "Detected"
                    : "Not detected"}
                </strong>

              </div>
            )}

          </div>
        )}

        {/* TAMPER */}

        {stage.key === "tamper" &&
          stageData?.result
            ?.tamper_probability !==
            undefined && (

          <div className="mt-2 text-sm text-gray-600">

            Tamper Probability:{" "}

            <span className="font-semibold">

              {formatPercent(
                stageData.result
                  .tamper_probability
              )}

            </span>

          </div>
        )}

        {/* RISK */}

        {stage.key === "risk" &&
          stageData?.result && (

          <div className="mt-2 flex gap-4 text-sm text-gray-600">

            {stageData.result
              .calibrated_risk !==
              undefined && (

              <span>

                Risk:{" "}

                <strong>

                  {Number(
                    stageData.result
                      .calibrated_risk
                  ).toFixed(4)}

                </strong>

              </span>
            )}

            {stageData.result
              .risk_level && (

              <span>

                Level:{" "}

                <strong>

                  {
                    stageData.result
                      .risk_level
                  }

                </strong>

                </span>
            )}

          </div>
        )}

      </div>
    </div>
  );
}

/* =========================================================
   PROCESSING PAGE
========================================================= */

export default function Processing() {

  const { scanId } =
    useParams();

  const navigate =
    useNavigate();

  const [screening, setScreening] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  const hasNavigated =
    useRef(false);

  useEffect(() => {

    let cancelled = false;
    let interval = null;

    const loadScreening =
      async () => {

        try {

          const response =
            await getScreening(
              scanId
            );

          if (cancelled) {
            return;
          }

          const data =
            response?.data ||
            response;

          console.log(
            "CYBERFOXXX Screening:",
            data
          );

          setScreening(data);
          setLoading(false);
          setError("");

          /* =================================================
             RISK
          ================================================= */

          const riskStage =
            getStageData(
              data,
              "risk"
            );

          const riskCompleted =
            normalizeStatus(
              riskStage?.status
            ) === "COMPLETED";

          /* =================================================
             AI DECISION
          ================================================= */

          const decisionStage =
            getStageData(
              data,
              "decision"
            );

          const aiDecision =
            data?.ai_decision ||
            decisionStage?.decision ||
            decisionStage?.result;

          const hasAIDecision =
            aiDecision !==
              null &&
            aiDecision !==
              undefined &&
            aiDecision !== "";

          /* =================================================
             AUTOMATED PIPELINE COMPLETE
          ================================================= */

          const automatedProcessingComplete =
            riskCompleted &&
            hasAIDecision;

          /* =================================================
             REDIRECT TO RESULTS
          ================================================= */

          if (
            automatedProcessingComplete &&
            !hasNavigated.current
          ) {

            hasNavigated.current =
              true;

            if (interval) {
              clearInterval(interval);
              interval = null;
            }

            console.log(
              "Automated screening complete. Opening Results..."
            );

            navigate(
              `/results/${encodeURIComponent(
                scanId
              )}`,
              {
                replace: true,
              }
            );
          }

        } catch (err) {

          if (cancelled) {
            return;
          }

          console.error(
            "Failed to load screening:",
            err
          );

          setLoading(false);

          setError(
            err?.response
              ?.data
              ?.detail ||
              err?.message ||
              "Unable to load screening status."
          );
        }
      };

    /* =======================================================
       VALIDATE ID
    ======================================================= */

    if (!scanId) {

      setLoading(false);

      setError(
        "Missing screening ID."
      );

      return;
    }

    loadScreening();

    /* =======================================================
       POLLING
    ======================================================= */

    interval = setInterval(
      loadScreening,
      1500
    );

    return () => {

      cancelled = true;

      if (interval) {
        clearInterval(interval);
      }

    };

  }, [
    scanId,
    navigate,
  ]);

  /* =========================================================
     LOADING
  ========================================================= */

  if (
    loading &&
    !screening
  ) {

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">

        <div className="text-center">

          <div className="w-12 h-12 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin mx-auto" />

          <p className="mt-4 text-gray-600 font-medium">
            Loading screening pipeline...
          </p>

        </div>

      </div>
    );
  }

  /* =========================================================
     ERROR
  ========================================================= */

  if (
    error &&
    !screening
  ) {

    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">

        <div className="bg-white border border-red-200 rounded-xl shadow-sm p-8 max-w-lg w-full text-center">

          <div className="w-14 h-14 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-2xl font-bold mx-auto">
            !
          </div>

          <h2 className="text-xl font-bold text-gray-900 mt-4">
            Unable to load screening
          </h2>

          <p className="text-gray-600 mt-2">
            {error}
          </p>

          <button
            onClick={() =>
              window.location.reload()
            }
            className="mt-6 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold"
          >
            Retry
          </button>

        </div>

      </div>
    );
  }

  /* =========================================================
     DATA
  ========================================================= */

  const pipeline =
    screening?.pipeline || {};

  const anomalyData =
    getStageData(
      screening,
      "anomaly"
    );

  const anomalyScore =
    extractAnomalyScore(
      screening
    );

  const tamperProbability =
    extractTamperProbability(
      screening
    );

  const riskScore =
    extractRisk(
      screening
    );

  const riskLevel =
    extractRiskLevel(
      screening
    );

  const aiDecision =
    screening?.ai_decision ||
    pipeline?.decision?.result ||
    pipeline?.decision?.decision ||
    null;

  /* =========================================================
     UI
  ========================================================= */

  return (
    <div className="min-h-screen bg-gray-50">

      {/* =====================================================
         HEADER
      ===================================================== */}

      <div className="bg-white border-b">

        <div className="max-w-6xl mx-auto px-6 py-6">

          <div className="flex items-center justify-between gap-6">

            <div>

              <p className="text-sm text-gray-500">
                CYBERFOXXX
              </p>

              <h1 className="text-2xl font-bold text-gray-900 mt-1">
                Automated Screening
              </h1>

              <p className="text-sm text-gray-500 mt-1">

                Screening ID:{" "}

                <span className="font-mono font-semibold text-gray-700">
                  {scanId}
                </span>

              </p>

            </div>

            <div className="text-right">

              <p className="text-xs uppercase tracking-wide text-gray-400">
                Status
              </p>

              <p className="text-sm font-semibold text-blue-600 mt-1">
                Processing
              </p>

            </div>

          </div>

        </div>

      </div>

      {/* =====================================================
         MAIN
      ===================================================== */}

      <main className="max-w-6xl mx-auto px-6 py-8">

        {/* INTRO */}

        <div className="bg-white rounded-xl border shadow-sm p-6 mb-8">

          <div className="flex items-start gap-4">

            <div className="w-12 h-12 bg-blue-100 text-blue-700 rounded-xl flex items-center justify-center text-xl">
              🔐
            </div>

            <div>

              <h2 className="text-lg font-bold text-gray-900">
                Document screening in progress
              </h2>

              <p className="text-sm text-gray-600 mt-1">
                CYBERFOXXX is executing the automated
                screening pipeline. Results will open
                automatically when all required automated
                stages are complete.
              </p>

            </div>

          </div>

        </div>

        {/* ===================================================
           ANOMALY RESULT NOTICE
        =================================================== */}

        {normalizeStatus(
          anomalyData?.status
        ) === "COMPLETED" && (

          <div className="bg-green-50 border border-green-200 rounded-xl p-5 mb-8">

            <div className="flex items-start gap-4">

              <div className="w-10 h-10 bg-green-100 text-green-700 rounded-full flex items-center justify-center font-bold">
                ✓
              </div>

              <div className="flex-1">

                <h3 className="font-bold text-green-800">
                  Anomaly Detection Completed
                </h3>

                <p className="text-sm text-green-700 mt-1">
                  The document screening module has
                  successfully returned an anomaly analysis.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">

                  <div className="bg-white rounded-lg border border-green-200 p-3">

                    <p className="text-xs text-gray-500 uppercase">
                      Anomaly Score
                    </p>

                    <p className="text-xl font-bold text-gray-900 mt-1">
                      {anomalyScore || "—"}
                    </p>

                  </div>

                  <div className="bg-white rounded-lg border border-green-200 p-3">

                    <p className="text-xs text-gray-500 uppercase">
                      Severity
                    </p>

                    <p className="text-xl font-bold text-gray-900 mt-1">
                      {anomalyData?.severity ||
                        "NORMAL"}
                    </p>

                  </div>

                  <div className="bg-white rounded-lg border border-green-200 p-3">

                    <p className="text-xs text-gray-500 uppercase">
                      Confidence
                    </p>

                    <p className="text-xl font-bold text-gray-900 mt-1">
                      {formatPercent(
                        anomalyData?.confidence
                      ) || "—"}
                    </p>

                  </div>

                </div>

              </div>

            </div>

          </div>
        )}

        {/* ===================================================
           PIPELINE + SUMMARY
        =================================================== */}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* PIPELINE */}

          <div className="lg:col-span-2 bg-white rounded-xl border shadow-sm p-6">

            <div className="mb-6">

              <h2 className="text-lg font-bold text-gray-900">
                Screening Pipeline
              </h2>

              <p className="text-sm text-gray-500 mt-1">
                Automated verification stages
              </p>

            </div>

            {STAGES.map(
              (stage) => (

                <PipelineStage
                  key={stage.key}
                  stage={stage}
                  stageData={getStageData(
                    screening,
                    stage.key
                  )}
                />

              )
            )}

          </div>

          {/* SUMMARY */}

          <div className="space-y-6">

            {/* ANOMALY */}

            <div className="bg-white rounded-xl border shadow-sm p-6">

              <p className="text-xs uppercase tracking-wide text-gray-400">
                Anomaly Score
              </p>

              <p className="text-3xl font-bold text-gray-900 mt-2">
                {anomalyScore || "—"}
              </p>

              <p className="text-sm text-gray-500 mt-1">
                Document anomaly signal
              </p>

            </div>

            {/* TAMPER */}

            <div className="bg-white rounded-xl border shadow-sm p-6">

              <p className="text-xs uppercase tracking-wide text-gray-400">
                Tamper Probability
              </p>

              <p className="text-3xl font-bold text-gray-900 mt-2">
                {tamperProbability || "—"}
              </p>

              <p className="text-sm text-gray-500 mt-1">
                Document authenticity signal
              </p>

            </div>

            {/* RISK */}

            <div className="bg-white rounded-xl border shadow-sm p-6">

              <p className="text-xs uppercase tracking-wide text-gray-400">
                Risk Score
              </p>

              <p className="text-3xl font-bold text-gray-900 mt-2">
                {riskScore || "—"}
              </p>

              {riskLevel && (

                <span className="inline-block mt-3 px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-xs font-semibold">

                  {String(
                    riskLevel
                  ).toUpperCase()}

                </span>

              )}

            </div>

            {/* AI */}

            <div className="bg-white rounded-xl border shadow-sm p-6">

              <p className="text-xs uppercase tracking-wide text-gray-400">
                AI Recommendation
              </p>

              <p
                className={`text-2xl font-bold mt-2 ${
                  aiDecision === "CLEAR"
                    ? "text-green-600"
                    : aiDecision === "REVIEW"
                    ? "text-yellow-600"
                    : aiDecision === "REJECT"
                    ? "text-red-600"
                    : "text-gray-400"
                }`}
              >
                {aiDecision ||
                  "PROCESSING"}
              </p>

              <p className="text-sm text-gray-500 mt-2">
                Automated recommendation.
                Officer makes the final decision
                on the Results page.
              </p>

            </div>

          </div>

        </div>

      </main>

    </div>
  );
}