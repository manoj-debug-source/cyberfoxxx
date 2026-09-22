import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  getTamperEnsemble,
  getRiskScore,
} from "../api/client";

import { useScreeningStore } from "../store/useScreeningStore";

import RiskBadge from "../components/RiskBadge";
import GradCamViewer from "../components/GradCamViewer";
import ElaHeatmap from "../components/ElaHeatmap";
import EnsembleAgreementCard from "../components/EnsembleAgreementCard";
import ConfidenceMeter from "../components/ConfidenceMeter";
import FieldTable from "../components/FieldTable";


/* =========================================================
   HELPERS
========================================================= */

function getAnomalyResult(scan) {
  if (!scan || typeof scan !== "object") {
    return null;
  }

  /*
   * Support the new teammate document-screening response.
   */

  if (
    scan.anomaly_result &&
    typeof scan.anomaly_result === "object"
  ) {
    return scan.anomaly_result;
  }

  /*
   * Support CYBERFOXXX stored document screening result.
   */

  if (
    scan.document_screening &&
    typeof scan.document_screening === "object"
  ) {
    return scan.document_screening;
  }

  /*
   * Support anomaly_analysis if present.
   */

  if (
    scan.anomaly_analysis &&
    typeof scan.anomaly_analysis === "object"
  ) {
    return scan.anomaly_analysis;
  }

  /*
   * Support pipeline.anomaly.result.
   */

  if (
    scan.pipeline?.anomaly?.result &&
    typeof scan.pipeline.anomaly.result === "object"
  ) {
    return scan.pipeline.anomaly.result;
  }

  return null;
}


function getAnomalyScore(scan) {
  const anomaly = getAnomalyResult(scan);

  if (anomaly) {
    const value =
      anomaly.anomaly_score ??
      anomaly.score;

    if (
      value !== undefined &&
      value !== null
    ) {
      const number = Number(value);

      if (!Number.isNaN(number)) {
        return number;
      }
    }
  }

  /*
   * Support pipeline.anomaly.score.
   */

  const pipelineScore =
    scan?.pipeline?.anomaly?.score;

  if (
    pipelineScore !== undefined &&
    pipelineScore !== null
  ) {
    const number = Number(pipelineScore);

    if (!Number.isNaN(number)) {
      return number;
    }
  }

  return null;
}


function formatPercentage(value) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return `${(
    Number(value) * 100
  ).toFixed(1)}%`;
}


function statusClass(isAnomaly) {
  if (isAnomaly === true) {
    return "bg-red-100 text-red-700 border-red-200";
  }

  if (isAnomaly === false) {
    return "bg-green-100 text-green-700 border-green-200";
  }

  return "bg-slate-100 text-slate-600 border-slate-200";
}


/* =========================================================
   COMPONENT
========================================================= */

export default function EvidenceAnalysis() {

  const { scanId } = useParams();

  const navigate = useNavigate();

  const scan = useScreeningStore(
    (state) => state.currentScan
  );

  const setRiskResult = useScreeningStore(
    (state) => state.setRiskResult
  );

  const [ensemble, setEnsemble] = useState(null);

  const [risk, setRisk] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");


  /* =======================================================
     LOAD EVIDENCE
  ======================================================= */

  useEffect(() => {

    async function load() {

      try {

        setLoading(true);

        setError("");


        /* ---------------------------------------------------
           Existing tamper ensemble
        --------------------------------------------------- */

        let ensembleData = null;

        try {

          ensembleData =
            await getTamperEnsemble(scanId);

          setEnsemble(ensembleData);

        } catch (tamperError) {

          /*
           * Tamper evidence is allowed to be unavailable
           * without hiding the anomaly result.
           */

          console.warn(
            "Tamper ensemble unavailable:",
            tamperError
          );

          setEnsemble(null);
        }


        /* ---------------------------------------------------
           Existing risk result
        --------------------------------------------------- */

        try {

          /*
           * Keep the existing risk endpoint compatibility.
           *
           * If the endpoint expects these values, provide
           * the real anomaly score when available.
           */

          const anomalyScore =
            getAnomalyScore(scan);

          const tamperScore =
            ensembleData?.cnn_score ?? 0;

          const riskData =
            await getRiskScore({

              scan_id:
                scanId,

              tamper_score:
                tamperScore,

              anomaly_score:
                anomalyScore ?? 0,

            });

          setRisk(riskData);

          setRiskResult(riskData);

        } catch (riskError) {

          console.warn(
            "Risk result unavailable:",
            riskError
          );

          setRisk(null);
        }

      } catch (loadError) {

        console.error(
          "Evidence analysis error:",
          loadError
        );

        setError(
          "Unable to load evidence analysis."
        );

      } finally {

        setLoading(false);
      }
    }

    load();

  }, [
    scanId,
    scan,
    setRiskResult,
  ]);


  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {

    return (
      <div className="max-w-6xl mx-auto px-6">

        <div className="text-center mt-20 text-slate-500">

          Loading evidence analysis...

        </div>

      </div>
    );
  }


  /* =======================================================
     ANOMALY DATA
  ======================================================= */

  const anomaly =
    getAnomalyResult(scan);

  const anomalyScore =
    getAnomalyScore(scan);

  const anomalyCompleted =
    anomaly !== null ||
    scan?.pipeline?.anomaly?.status ===
      "COMPLETED";


  const isAnomaly =
    anomaly?.is_anomaly ??
    null;


  const severity =
    anomaly?.severity ??
    "UNKNOWN";


  const confidence =
    anomaly?.confidence ??
    null;


  const tamperingDetected =
    anomaly?.tampering_detected ??
    null;


  const validationFailed =
    anomaly?.validation_failed ??
    null;


  const fraudTypes =
    Array.isArray(
      anomaly?.detected_fraud_types
    )
      ? anomaly.detected_fraud_types
      : [];


  const evidence =
    Array.isArray(
      anomaly?.evidence
    )
      ? anomaly.evidence
      : [];


  const recommendedAction =
    anomaly?.recommended_action ??
    null;


  /* =======================================================
     RENDER
  ======================================================= */

  return (

    <div className="max-w-6xl mx-auto px-6 space-y-6">


      {/* ===================================================
          HEADER
      =================================================== */}

      <div>

        <h1 className="text-3xl font-bold text-slate-800">

          Evidence & Tamper Analysis

        </h1>

        <p className="text-gray-500 mt-1">

          Screening ID: {scanId}

        </p>

      </div>


      {/* ===================================================
          ERROR
      =================================================== */}

      {error && (

        <div className="border border-red-200 bg-red-50 text-red-700 rounded-xl p-4">

          {error}

        </div>

      )}


      {/* ===================================================
          RISK
      =================================================== */}

      {risk && (

        <RiskBadge
          decision={
            risk.decision ??
            risk.risk_level
          }
          score={
            risk.risk_score ??
            risk.calibrated_risk
          }
        />

      )}


      {/* ===================================================
          DOCUMENT FIELDS
      =================================================== */}

      <FieldTable

        fields={
          scan?.fields ||
          scan?.ocr?.fields ||
          {

            Name:
              "Loading from backend",

            DOB:
              "Loading from backend",

            "ID Number":
              "Loading from backend",

          }
        }

      />


      {/* ===================================================
          ANOMALY DETECTION
      =================================================== */}

      <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">

        <div className="flex items-start justify-between gap-4">

          <div>

            <h2 className="text-2xl font-bold text-slate-800">

              Anomaly Detection

            </h2>

            <p className="text-slate-500 mt-1">

              Comparison against learned genuine-document
              patterns

            </p>

          </div>

          <div className="text-2xl">
            🤖
          </div>

        </div>


        {/* -------------------------------------------------
            COMPLETED
        ------------------------------------------------- */}

        {anomalyCompleted ? (

          <div className="mt-6 space-y-5">


            {/* STATUS */}

            <div
              className={`rounded-xl border p-5 ${statusClass(
                isAnomaly
              )}`}
            >

              <div className="flex items-center justify-between">

                <div>

                  <p className="font-semibold text-lg">

                    {isAnomaly === true
                      ? "Anomaly Detected"
                      : isAnomaly === false
                      ? "No Anomaly Detected"
                      : "Anomaly Analysis Completed"}

                  </p>

                  <p className="text-sm mt-1">

                    {isAnomaly === true
                      ? "The document contains indicators requiring further investigation."
                      : isAnomaly === false
                      ? "The document is consistent with the learned genuine-document patterns."
                      : "The anomaly detection service returned a result."}

                  </p>

                </div>

              </div>

            </div>


            {/* METRICS */}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">


              <div className="rounded-xl bg-slate-50 border border-slate-200 p-5">

                <p className="text-sm text-slate-500">

                  Anomaly Score

                </p>

                <p className="text-3xl font-bold text-slate-800 mt-2">

                  {formatPercentage(
                    anomalyScore
                  )}

                </p>

              </div>


              <div className="rounded-xl bg-slate-50 border border-slate-200 p-5">

                <p className="text-sm text-slate-500">

                  Severity

                </p>

                <p className="text-2xl font-bold text-slate-800 mt-2">

                  {severity}

                </p>

              </div>


              <div className="rounded-xl bg-slate-50 border border-slate-200 p-5">

                <p className="text-sm text-slate-500">

                  Confidence

                </p>

                <p className="text-3xl font-bold text-slate-800 mt-2">

                  {formatPercentage(
                    confidence
                  )}

                </p>

              </div>

            </div>


            {/* VALIDATION */}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">


              <div className="rounded-xl border border-slate-200 p-4">

                <p className="text-sm text-slate-500">

                  Tampering Detection

                </p>

                <p className="font-semibold text-slate-800 mt-1">

                  {tamperingDetected === true
                    ? "Tampering detected"
                    : tamperingDetected === false
                    ? "No tampering detected"
                    : "Not available"}

                </p>

              </div>


              <div className="rounded-xl border border-slate-200 p-4">

                <p className="text-sm text-slate-500">

                  Document Validation

                </p>

                <p className="font-semibold text-slate-800 mt-1">

                  {validationFailed === true
                    ? "Validation failed"
                    : validationFailed === false
                    ? "Validation passed"
                    : "Not available"}

                </p>

              </div>

            </div>


            {/* FRAUD TYPES */}

            {fraudTypes.length > 0 && (

              <div className="rounded-xl border border-red-200 bg-red-50 p-5">

                <p className="font-semibold text-red-800">

                  Detected Fraud Types

                </p>

                <div className="flex flex-wrap gap-2 mt-3">

                  {fraudTypes.map(
                    (fraudType, index) => (

                      <span
                        key={`${fraudType}-${index}`}
                        className="px-3 py-1 rounded-full bg-white border border-red-200 text-red-700 text-sm"
                      >

                        {fraudType}

                      </span>

                    )
                  )}

                </div>

              </div>

            )}


            {/* EVIDENCE */}

            {evidence.length > 0 && (

              <div className="rounded-xl border border-slate-200 p-5">

                <h3 className="font-semibold text-slate-800">

                  Detection Evidence

                </h3>

                <div className="mt-3 space-y-3">

                  {evidence.map(
                    (item, index) => (

                      <div
                        key={index}
                        className="rounded-lg bg-slate-50 p-4 text-sm text-slate-700"
                      >

                        {typeof item === "string"
                          ? item
                          : JSON.stringify(item)}

                      </div>

                    )
                  )}

                </div>

              </div>

            )}


            {/* RECOMMENDED ACTION */}

            {recommendedAction && (

              <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">

                <p className="font-semibold text-blue-900">

                  Recommended Action

                </p>

                <p className="text-blue-800 mt-2">

                  {recommendedAction}

                </p>

              </div>

            )}

          </div>

        ) : (

          /* ------------------------------------------------
             PENDING
          ------------------------------------------------- */

          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-6">

            <p className="font-semibold text-lg text-slate-700">

              Anomaly Detection Pending

            </p>

            <p className="text-slate-500 mt-1">

              The anomaly detection service has not returned
              a result yet.

            </p>

          </div>

        )}

      </section>


      {/* ===================================================
          OLD LOCAL ENSEMBLE
      =================================================== */}

      {ensemble && (

        <EnsembleAgreementCard

          cnnScore={
            ensemble.cnn_score
          }

          autoencoderScore={
            ensemble.autoencoder_score
          }

          agree={
            ensemble.agree
          }

        />

      )}


      {/* ===================================================
          GRAD-CAM
      =================================================== */}

      {ensemble && (

        <GradCamViewer

          originalUrl={
            scan?.original_url
          }

          gradcamUrl={
            scan?.gradcam_url
          }

          cnnScore={
            ensemble.cnn_score
          }

        />

      )}


      {/* ===================================================
          ELA
      =================================================== */}

      {ensemble && (

        <ElaHeatmap

          originalUrl={
            scan?.original_url
          }

          elaUrl={
            scan?.ela_url
          }

        />

      )}


      {/* ===================================================
          CONFIDENCE
      =================================================== */}

      {risk && (

        <ConfidenceMeter

          score={
            risk.risk_score ??
            risk.calibrated_risk
          }

          low={
            risk.confidence_low
          }

          high={
            risk.confidence_high
          }

        />

      )}


      {/* ===================================================
          NAVIGATION
      =================================================== */}

      <div className="flex gap-4 pb-8">

        <button

          onClick={() =>
            navigate(
              `/identity-linkage/${encodeURIComponent(
                scanId
              )}`
            )
          }

          className="bg-slate-900 text-white px-5 py-3 rounded-lg hover:bg-slate-800 transition"

        >

          View Identity Linkage

        </button>

      </div>


    </div>

  );
}