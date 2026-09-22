import { useEffect, useState } from "react";
import {
  useParams,
  useLocation,
  Link,
  useNavigate,
} from "react-router-dom";

import {
  getScan,
  getRiskScore,
  getWatchlistResult,
  submitScreeningDecision,
} from "../api/client";

import FieldTable from "../components/FieldTable";
import TamperHeatmap from "../components/TamperHeatmap";
import FaceComparePanel from "../components/FaceComparePanel";


// =====================================================
// WATCHLIST / BLACKLIST CHECK
// =====================================================

function WatchlistCheck({ screeningId }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function loadWatchlist() {
      try {
        setLoading(true);

        const data = await getWatchlistResult(
          screeningId
        );

        console.log(
          "WATCHLIST RESULT:",
          data
        );

        if (mounted) {
          setResult(data);
        }

      } catch (error) {
        console.error(
          "WATCHLIST RESULT ERROR:",
          error?.response?.data || error
        );

        if (mounted) {
          setResult(null);
        }

      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    if (screeningId) {
      loadWatchlist();
    }

    return () => {
      mounted = false;
    };
  }, [screeningId]);


  // ===================================================
  // LOADING
  // ===================================================

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">

        <div className="flex items-center gap-4">

          <div className="text-4xl">
            ⏳
          </div>

          <div>

            <h3 className="text-xl font-bold text-slate-800">
              Watchlist Check
            </h3>

            <p className="mt-1 text-slate-500">
              Checking authorized databases...
            </p>

          </div>

        </div>

      </div>
    );
  }


  // ===================================================
  // NO RESULT
  // ===================================================

  if (!result) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">

        <div className="flex items-center gap-4">

          <div className="text-4xl">
            ⏳
          </div>

          <div>

            <h3 className="text-xl font-bold text-slate-800">
              Watchlist Check Pending
            </h3>

            <p className="mt-1 text-slate-500">
              Watchlist screening has not returned a result yet.
            </p>

          </div>

        </div>

      </div>
    );
  }


  // ===================================================
  // PENDING
  // ===================================================

  if (result.status === "PENDING") {
    return (
      <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">

        <div className="flex items-center gap-4">

          <div className="text-4xl">
            ⏳
          </div>

          <div>

            <h3 className="text-xl font-bold text-slate-800">
              Watchlist Check Pending
            </h3>

            <p className="mt-1 text-slate-500">
              Watchlist screening has not been performed yet.
            </p>

          </div>

        </div>

      </div>
    );
  }


  // ===================================================
  // NO MATCH
  // ===================================================

  if (result.status === "NO_MATCH") {
    return (
      <div className="rounded-2xl border border-green-200 bg-green-50 p-6">

        <div className="flex items-center gap-4">

          <div className="text-4xl">
            ✓
          </div>

          <div>

            <h3 className="text-xl font-bold text-green-800">
              No Watchlist Match
            </h3>

            <p className="mt-1 text-green-700">
              No matching record was found in the
              authorized screening database.
            </p>

          </div>

        </div>

      </div>
    );
  }


  // ===================================================
  // POTENTIAL MATCH
  // ===================================================

  if (result.status === "POTENTIAL_MATCH") {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">

        <div className="flex items-center gap-4">

          <div className="text-4xl">
            ⚠
          </div>

          <div>

            <h3 className="text-xl font-bold text-amber-800">
              Potential Watchlist Match
            </h3>

            <p className="mt-1 text-amber-700">
              A potential match was detected.
              Officer investigation is required.
            </p>

          </div>

        </div>


        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">

          <div>

            <p className="text-sm text-slate-500">
              Match Score
            </p>

            <p className="font-bold text-slate-800">

              {result.match_score !== undefined &&
              result.match_score !== null
                ? `${(
                    Number(result.match_score) * 100
                  ).toFixed(1)}%`
                : "—"}

            </p>

          </div>


          <div>

            <p className="text-sm text-slate-500">
              Matched Fields
            </p>

            <p className="font-bold text-slate-800">

              {Array.isArray(
                result.matched_fields
              )
                ? result.matched_fields.join(", ")
                : result.matched_fields || "—"}

            </p>

          </div>

        </div>

      </div>
    );
  }


  // ===================================================
  // MATCH
  // ===================================================

  if (result.status === "MATCH") {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6">

        <div className="flex items-center gap-4">

          <div className="text-4xl">
            !
          </div>

          <div>

            <h3 className="text-xl font-bold text-red-800">
              Watchlist Match Detected
            </h3>

            <p className="mt-1 text-red-700">
              A matching authorized database record
              was found. Follow your applicable
              officer-review procedure.
            </p>

          </div>

        </div>


        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">

          <div>

            <p className="text-sm text-slate-500">
              Match Score
            </p>

            <p className="font-bold text-slate-800">

              {result.match_score !== undefined &&
              result.match_score !== null
                ? `${(
                    Number(result.match_score) * 100
                  ).toFixed(1)}%`
                : "—"}

            </p>

          </div>


          <div>

            <p className="text-sm text-slate-500">
              Matched Fields
            </p>

            <p className="font-bold text-slate-800">

              {Array.isArray(
                result.matched_fields
              )
                ? result.matched_fields.join(", ")
                : result.matched_fields || "—"}

            </p>

          </div>

        </div>

      </div>
    );
  }


  // ===================================================
  // UNKNOWN STATUS
  // ===================================================

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6">

      <h3 className="text-xl font-bold text-slate-800">
        Watchlist Check
      </h3>

      <p className="mt-1 text-slate-500">
        Screening result received with status:
        {" "}
        {result.status || "UNKNOWN"}
      </p>

    </div>
  );
}


// =====================================================
// RESULTS PAGE
// =====================================================

export default function Results() {
  const { scanId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  // =====================================================
  // STATE
  // =====================================================

  const [scan, setScan] = useState(
    location.state?.scanResult || null
  );

  const [risk, setRisk] = useState(null);

  const [faceResult] = useState(
    location.state?.faceResult || null
  );

  const [livePhotoUrl] = useState(
    location.state?.livePhotoUrl || null
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [decisionLoading, setDecisionLoading] =
    useState(false);

  const [decisionError, setDecisionError] =
    useState(null);

  const [officerDecision, setOfficerDecision] =
    useState(
      normalizeOfficerDecision(
        location.state?.scanResult?.officer_decision
      )
    );


  // =====================================================
  // LOAD SCREENING
  // =====================================================

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        const scanData = await getScan(scanId);

        if (!mounted) return;

        console.log(
          "RESULTS: Complete screening data:",
          scanData
        );

        setScan(scanData);

        const existingOfficerDecision =
          normalizeOfficerDecision(
            scanData?.officer_decision
          );

        if (existingOfficerDecision) {
          setOfficerDecision(
            existingOfficerDecision
          );
        }


        // ===============================================
        // LOAD RISK
        // ===============================================

        try {
          const riskData =
            await getRiskScore(scanId);

          if (!mounted) return;

          console.log(
            "RESULTS: Risk response:",
            riskData
          );

          setRisk(riskData);

        } catch (riskErr) {
          console.warn(
            "RESULTS: Risk not available:",
            riskErr?.response?.data
          );

          if (
            riskErr?.response?.status === 404
          ) {
            setRisk(null);
          } else {
            throw riskErr;
          }
        }

      } catch (err) {
        console.error(
          "RESULTS ERROR:",
          err
        );

        if (!mounted) return;

        setError(
          err?.response?.data?.detail?.message ||
          err?.response?.data?.detail ||
          err?.message ||
          "Unable to load screening results."
        );

      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    if (scanId) {
      load();
    }

    return () => {
      mounted = false;
    };
  }, [scanId]);


  // =====================================================
  // OFFICER DECISION
  // =====================================================

  async function handleOfficerDecision(decision) {
    if (decisionLoading || officerDecision) {
      return;
    }

    try {
      setDecisionLoading(true);
      setDecisionError(null);

      console.log(
        "Submitting officer decision:",
        {
          screeningId: scanId,
          decision,
        }
      );

      const result =
        await submitScreeningDecision(
          scanId,
          {
            decision,
          }
        );

      console.log(
        "OFFICER DECISION RESPONSE:",
        result
      );

      const newDecision =
        normalizeOfficerDecision(
          result?.officer_decision ||
          result
        );

      if (!newDecision) {
        throw new Error(
          "Officer decision was saved, but the server returned an invalid decision response."
        );
      }

      setOfficerDecision(
        newDecision
      );

      setScan((previous) => ({
        ...(previous || {}),
        status:
          result?.status ||
          newDecision.decision,
        officer_decision:
          newDecision,
      }));


      // ===============================================
      // DIRECTLY TO IDENTITY LINKAGE
      // ===============================================

      navigate(
        `/identity-linkage/${encodeURIComponent(
          scanId
        )}`,
        {
          replace: true,
          state: {
            scanResult: {
              ...(scan || {}),
              ...(result || {}),
              officer_decision:
                newDecision,
            },
            officerDecision:
              newDecision,
          },
        }
      );

    } catch (err) {
      console.error(
        "OFFICER DECISION ERROR:",
        err
      );

      setDecisionError(
        err?.response?.data?.detail?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to save officer decision."
      );

    } finally {
      setDecisionLoading(false);
    }
  }


  // =====================================================
  // LOADING
  // =====================================================

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">

        <div className="text-center">

          <div className="text-3xl mb-3">
            🔍
          </div>

          <p className="text-gray-500">
            Loading screening results…
          </p>

        </div>

      </div>
    );
  }


  // =====================================================
  // ERROR
  // =====================================================

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">

        <div className="bg-white rounded-xl shadow p-8 max-w-md text-center">

          <div className="text-4xl mb-4">
            ⚠️
          </div>

          <h2 className="text-xl font-bold text-red-600 mb-2">
            Unable to Load Results
          </h2>

          <p className="text-gray-500 text-sm mb-6">
            {error}
          </p>

          <Link
            to="/"
            className="inline-block bg-brand text-white px-5 py-2 rounded-lg"
          >
            ← Scan another document
          </Link>

        </div>

      </div>
    );
  }


  // =====================================================
  // RISK RESULT
  // =====================================================

  const riskResult =
    risk?.risk ||
    scan?.risk ||
    null;

  const calibratedRisk =
    riskResult?.calibrated_risk !== undefined &&
    riskResult?.calibrated_risk !== null
      ? Number(
          riskResult.calibrated_risk
        )
      : null;

  const riskScorePercent =
    calibratedRisk !== null
      ? calibratedRisk * 100
      : null;

  const riskLevel =
    String(
      riskResult?.risk_level ||
      "PENDING"
    ).toUpperCase();


  // =====================================================
  // AI DECISION
  // =====================================================

  const rawAiDecision =
    scan?.ai_decision ??
    scan?.pipeline?.decision?.decision ??
    scan?.pipeline?.decision?.result?.decision ??
    riskResult?.decision ??
    null;

  const normalizedAiDecision =
    normalizeAiDecision(
      rawAiDecision
    );

  const aiDecision =
    normalizedAiDecision ||
    deriveAiDecisionFromRisk(
      riskLevel
    );


  // =====================================================
  // OCR
  // =====================================================

  const fields =
    scan?.fields ||
    scan?.ocr?.fields ||
    scan?.ocr_result?.fields ||
    scan?.ocr?.result?.fields ||
    {};


  // =====================================================
  // TAMPER
  // =====================================================

  const tamperData =
    scan?.tamper_analysis ||
    scan?.tamper ||
    scan?.pipeline?.tamper?.result ||
    null;

  const rawTamperProbability =
    tamperData?.tamper_probability ??
    tamperData?.probability ??
    tamperData?.tampered_probability ??
    scan?.pipeline?.tamper?.probability ??
    null;

  const tamperProbability =
    rawTamperProbability !== undefined &&
    rawTamperProbability !== null
      ? Number(
          rawTamperProbability
        )
      : null;

  const tamperScore =
    tamperProbability !== null
      ? tamperProbability <= 1
        ? tamperProbability * 100
        : tamperProbability
      : null;

  const tamperPrediction =
    String(
      tamperData?.prediction ||
      tamperData?.label ||
      ""
    ).toLowerCase() || null;

  const tamperFlags =
    Array.isArray(
      tamperData?.tamper_flags
    )
      ? tamperData.tamper_flags
      : Array.isArray(
          scan?.tamper_flags
        )
      ? scan.tamper_flags
      : [];

  const elaImageUrl =
    tamperData?.ela_image_url ||
    scan?.ela_image_url ||
    null;

  const tamperAvailable =
    tamperData !== null ||
    tamperProbability !== null ||
    scan?.pipeline?.tamper?.status ===
      "COMPLETED";


  // =====================================================
  // ANOMALY
  // =====================================================

  const anomalyData =
    scan?.anomaly ||
    scan?.anomaly_analysis ||
    scan?.pipeline?.anomaly?.result ||
    null;

  const anomalyPipeline =
    scan?.pipeline?.anomaly ||
    null;


  const rawAnomalyScore =
    anomalyData?.anomaly_score ??
    anomalyData?.score ??
    anomalyPipeline?.anomaly_score ??
    anomalyPipeline?.score ??
    scan?.anomaly_score ??
    null;

  let anomalyScore = null;

  if (
    rawAnomalyScore !== null &&
    rawAnomalyScore !== undefined
  ) {
    const numericValue =
      Number(rawAnomalyScore);

    if (!Number.isNaN(numericValue)) {
      anomalyScore =
        numericValue <= 1
          ? numericValue * 100
          : numericValue;
    }
  }


  const anomalyAvailable =
    anomalyScore !== null ||
    anomalyData !== null ||
    anomalyPipeline?.status ===
      "COMPLETED";


  const rawAnomalyDecision =
    anomalyData?.decision ??
    anomalyPipeline?.decision ??
    null;

  const anomalyDecision =
    normalizeAnomalyDecision(
      rawAnomalyDecision
    );


  const anomalyIsAnomaly =
    anomalyData?.is_anomaly ??
    null;

  const anomalySeverity =
    anomalyData?.severity ??
    null;

  const anomalyConfidence =
    anomalyData?.confidence !== undefined &&
    anomalyData?.confidence !== null
      ? normalizePercentage(
          anomalyData.confidence
        )
      : null;

  const anomalyTamperingDetected =
    anomalyData?.tampering_detected ??
    null;

  const anomalyValidationFailed =
    anomalyData?.validation_failed ??
    null;

  const anomalyFraudTypes =
    Array.isArray(
      anomalyData?.detected_fraud_types
    )
      ? anomalyData.detected_fraud_types
      : [];

  const anomalyEvidence =
    Array.isArray(
      anomalyData?.evidence
    )
      ? anomalyData.evidence
      : [];

  const anomalyRecommendedAction =
    anomalyData?.recommended_action ??
    null;


  // =====================================================
  // FACE
  // =====================================================

  const faceAvailable =
    !!faceResult ||
    !!livePhotoUrl;

  const rawFaceScore =
    faceResult?.similarity ??
    faceResult?.similarity_score ??
    risk?.face_similarity ??
    null;

  const faceScore =
    rawFaceScore !== null &&
    rawFaceScore !== undefined
      ? Number(rawFaceScore)
      : 0;


  // =====================================================
  // MRZ
  // =====================================================

  const mrzValid =
    scan?.mrz_valid ??
    scan?.mrz?.valid ??
    scan?.mrz?.is_valid ??
    scan?.ocr?.mrz_valid ??
    null;


  // =====================================================
  // EXPIRY
  // =====================================================

  const expiryAvailable =
    scan?.document_expired !== undefined ||
    scan?.document_expiry !== undefined ||
    scan?.expiry_date !== undefined ||
    scan?.ocr?.expiry_date !== undefined;

  const documentExpired =
    scan?.document_expired ??
    null;


  // =====================================================
  // FIELD CONSISTENCY
  // =====================================================

  const fieldMismatch =
    scan?.field_mismatch ??
    scan?.validation?.field_mismatch ??
    null;

  const fieldConsistencyAvailable =
    fieldMismatch !== null &&
    fieldMismatch !== undefined;


  // =====================================================
  // IDENTITY
  // =====================================================

  const identityAvailable =
    scan?.identity_conflict !== undefined ||
    scan?.identity_linkage !== undefined;

  const identityConflict =
    scan?.identity_conflict ??
    scan?.identity_linkage?.conflict ??
    false;


  // =====================================================
  // PIPELINE
  // =====================================================

  const pipeline =
    scan?.pipeline || {};


  // =====================================================
  // MAIN PAGE
  // =====================================================

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">

      {/* =================================================
          HEADER
      ================================================= */}

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-8">

        <div>

          <p className="text-xs uppercase tracking-wider text-gray-400 mb-1">
            CYBERFOXXX
          </p>

          <h1 className="text-2xl font-bold text-brand">
            Screening Results
          </h1>

          <p className="text-sm text-gray-500 mt-1">
            Scan ID: {scanId}
          </p>

        </div>

        <div className="flex items-center gap-4 flex-wrap">

          <Link
            to={`/risk-assessment/${encodeURIComponent(
              scanId
            )}`}
            state={{
              scanResult: scan,
              faceResult,
              livePhotoUrl,
            }}
            className="text-sm text-brand underline hover:text-blue-900"
          >
            View pipeline stages →
          </Link>

          <Link
            to="/"
            className="text-sm text-brand underline hover:text-blue-900"
          >
            ← Scan another document
          </Link>

        </div>

      </div>


      {/* =================================================
          DECISION + RISK
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mb-8">

        <h2 className="text-lg font-semibold text-brand text-center mb-6">
          Screening Decision & Risk
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

          <DecisionCard
            title="AI Recommendation"
            value={
              aiDecision || "PENDING"
            }
            subtitle="Advisory model output"
            type={
              aiDecision === "CLEAR"
                ? "clear"
                : aiDecision === "REVIEW"
                ? "review"
                : aiDecision === "REJECT"
                ? "reject"
                : "pending"
            }
          />


          <DecisionCard
            title="Calibrated Risk"
            value={
              calibratedRisk !== null
                ? `${riskScorePercent.toFixed(
                    2
                  )}/100`
                : "—"
            }
            subtitle={
              calibratedRisk !== null
                ? `Risk level: ${riskLevel}`
                : "Risk calculation pending"
            }
            type={
              riskLevel === "LOW"
                ? "clear"
                : riskLevel === "MEDIUM"
                ? "review"
                : riskLevel === "HIGH" ||
                  riskLevel === "CRITICAL"
                ? "reject"
                : "pending"
            }
          />


          <DecisionCard
            title="Officer Decision"
            value={
              officerDecision?.decision ||
              "PENDING"
            }
            subtitle={
              officerDecision?.decided_by
                ? `By ${officerDecision.decided_by}`
                : "Awaiting officer action"
            }
            type={
              officerDecision?.decision === "CLEAR"
                ? "clear"
                : officerDecision?.decision === "REVIEW"
                ? "review"
                : officerDecision?.decision === "REJECTED"
                ? "reject"
                : "pending"
            }
          />

        </div>


        {riskResult && (
          <div className="text-center mt-5">

            <p className="text-xs text-gray-400">
              Model:{" "}
              {riskResult.model_version ||
                "—"}
            </p>

            <p className="text-xs text-gray-400">
              Method:{" "}
              {riskResult.calibration_method ||
                "—"}
            </p>

          </div>
        )}

      </div>


      {/* =================================================
          DOCUMENT VALIDATION
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mb-6">

        <div className="flex items-center justify-between mb-5">

          <div>

            <h2 className="text-lg font-semibold text-brand">
              Document Validation
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              Verification against document rules and extracted data
            </p>

          </div>

          <span className="text-xl">
            📋
          </span>

        </div>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

          <ValidationCard
            title="MRZ Validation"
            status={
              mrzValid === true
                ? "PASS"
                : mrzValid === false
                ? "FLAGGED"
                : "PENDING"
            }
            description={
              mrzValid === true
                ? "MRZ structure and checksum are valid."
                : mrzValid === false
                ? "MRZ validation requires review."
                : "MRZ validation has not been performed yet."
            }
          />


          <ValidationCard
            title="Expiry Check"
            status={
              !expiryAvailable
                ? "PENDING"
                : documentExpired === true
                ? "FLAGGED"
                : documentExpired === false
                ? "PASS"
                : "PENDING"
            }
            description={
              !expiryAvailable
                ? "Expiry information is not available yet."
                : documentExpired === true
                ? "Document appears to be expired."
                : documentExpired === false
                ? "Document expiry check passed."
                : "Expiry validation is pending."
            }
          />


          <ValidationCard
            title="Field Consistency"
            status={
              !fieldConsistencyAvailable
                ? "PENDING"
                : fieldMismatch
                ? "FLAGGED"
                : "PASS"
            }
            description={
              !fieldConsistencyAvailable
                ? "Field consistency validation has not been performed yet."
                : fieldMismatch
                ? "Extracted fields contain inconsistencies."
                : "Extracted document fields are consistent."
            }
          />

        </div>

      </div>


      {/* =================================================
          WATCHLIST / BLACKLIST
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mb-6">

        <div className="flex items-center justify-between mb-5">

          <div>

            <h2 className="text-lg font-semibold text-brand">
              Watchlist / Blacklist Check
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              Authorized database screening
            </p>

          </div>

          <span className="text-xl">
            🛡️
          </span>

        </div>


        <WatchlistCheck
          screeningId={scanId}
        />

      </div>


      {/* =================================================
          OCR + TAMPER
      ================================================= */}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        <FieldTable
          fields={fields}
        />

        <TamperHeatmap
          tamperScore={
            tamperScore !== null
              ? tamperScore
              : 0
          }
          tamperFlags={tamperFlags}
          tamperAnalysis={tamperData}
          elaImageUrl={elaImageUrl}
        />

      </div>


      {/* =================================================
          TAMPER DETAIL
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mt-6">

        <div className="flex items-center justify-between mb-4">

          <div>

            <h2 className="text-lg font-semibold text-brand">
              Tampering Analysis
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              CNN-based document manipulation analysis
            </p>

          </div>

          <span className="text-xl">
            🔐
          </span>

        </div>


        {!tamperAvailable ? (

          <div className="border rounded-xl p-5 bg-gray-50">

            <div className="flex items-center gap-3">

              <span className="text-xl">
                ⏳
              </span>

              <div>

                <p className="font-semibold text-gray-700">
                  Tamper Detection Pending
                </p>

                <p className="text-sm text-gray-500 mt-1">
                  Tamper Detection has not returned a result yet.
                </p>

              </div>

            </div>

          </div>

        ) : (

          <div
            className={`border rounded-xl p-5 ${
              tamperPrediction === "tampered"
                ? "border-red-200 bg-red-50"
                : "border-green-200 bg-green-50"
            }`}
          >

            <div className="flex items-center justify-between">

              <div>

                <p className="text-sm text-gray-500">
                  Tamper Probability
                </p>

                <p className="text-3xl font-bold text-brand mt-1">

                  {tamperScore !== null
                    ? `${tamperScore.toFixed(
                        2
                      )}/100`
                    : "—"}

                </p>

              </div>


              <div className="text-right">

                {tamperPrediction === "tampered" ? (

                  <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-red-100 text-red-700">
                    ⚠ TAMPERED
                  </span>

                ) : tamperPrediction === "genuine" ? (

                  <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-green-100 text-green-700">
                    ✓ GENUINE
                  </span>

                ) : (

                  <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-gray-100 text-gray-600">
                    RESULT AVAILABLE
                  </span>

                )}

              </div>

            </div>


            {tamperScore !== null && (
              <div className="mt-4">

                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">

                  <div
                    className={`h-full rounded-full transition-all ${
                      tamperScore >= 50
                        ? "bg-red-500"
                        : "bg-green-500"
                    }`}
                    style={{
                      width: `${Math.min(
                        Math.max(
                          tamperScore,
                          0
                        ),
                        100
                      )}%`,
                    }}
                  />

                </div>

              </div>
            )}


            {tamperProbability !== null && (
              <p className="text-xs text-gray-400 mt-3">
                Model probability:{" "}
                {tamperProbability.toFixed(
                  4
                )}
              </p>
            )}

          </div>

        )}

      </div>


      {/* =================================================
          ANOMALY
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mt-6">

        <div className="flex items-center justify-between mb-4">

          <div>

            <h2 className="text-lg font-semibold text-brand">
              Anomaly Detection
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              Comparison against learned genuine-document patterns
            </p>

          </div>

          <span className="text-xl">
            🤖
          </span>

        </div>


        {!anomalyAvailable ? (

          <div className="border rounded-xl p-5 bg-gray-50">

            <div className="flex items-center gap-3">

              <span className="text-xl">
                ⏳
              </span>

              <div>

                <p className="font-semibold text-gray-700">
                  Anomaly Detection Pending
                </p>

                <p className="text-sm text-gray-500 mt-1">
                  The anomaly detection service has not returned a result yet.
                </p>

              </div>

            </div>

          </div>

        ) : (

          <div className="space-y-5">

            {/* ===========================================
                TOP ANOMALY STATUS
            =========================================== */}

            <div
              className={`border rounded-xl p-5 ${
                anomalyIsAnomaly === true
                  ? "border-red-200 bg-red-50"
                  : anomalyDecision === "CLEAR"
                  ? "border-green-200 bg-green-50"
                  : "border-gray-200 bg-gray-50"
              }`}
            >

              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">

                <div>

                  <p className="text-sm text-gray-500">
                    Detection Result
                  </p>

                  <p
                    className={`text-2xl font-bold mt-1 ${
                      anomalyIsAnomaly === true
                        ? "text-red-600"
                        : anomalyDecision === "CLEAR"
                        ? "text-green-600"
                        : "text-gray-700"
                    }`}
                  >

                    {anomalyDecision === "CLEAR"
                      ? "✓ CLEAR"
                      : anomalyDecision === "REVIEW"
                      ? "⚠ REVIEW"
                      : anomalyDecision === "REJECT"
                      ? "✕ REJECT"
                      : anomalyIsAnomaly === true
                      ? "⚠ ANOMALY DETECTED"
                      : "RESULT AVAILABLE"}

                  </p>

                </div>


                <div className="text-right">

                  {anomalySeverity && (

                    <span
                      className={`text-xs font-semibold px-3 py-1.5 rounded-full ${
                        anomalySeverity === "NORMAL"
                          ? "bg-green-100 text-green-700"
                          : anomalySeverity === "LOW"
                          ? "bg-blue-100 text-blue-700"
                          : anomalySeverity === "MEDIUM"
                          ? "bg-yellow-100 text-yellow-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {anomalySeverity}
                    </span>

                  )}

                </div>

              </div>

            </div>


            {/* ===========================================
                SCORE
            =========================================== */}

            <div>

              <div className="flex justify-between text-xs mb-2">

                <span className="text-gray-500">
                  Anomaly Score
                </span>

                <span className="font-semibold">

                  {anomalyScore !== null
                    ? `${anomalyScore.toFixed(
                        2
                      )}/100`
                    : "—"}

                </span>

              </div>


              <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">

                <div
                  className={`h-full rounded-full transition-all ${
                    anomalyScore >= 70
                      ? "bg-red-500"
                      : anomalyScore >= 40
                      ? "bg-yellow-500"
                      : "bg-green-500"
                  }`}
                  style={{
                    width: `${Math.min(
                      Math.max(
                        anomalyScore || 0,
                        0
                      ),
                      100
                    )}%`,
                  }}
                />

              </div>

            </div>


            {/* ===========================================
                ANOMALY DETAILS
            =========================================== */}

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

              <AnomalyDetailCard
                label="Score"
                value={
                  anomalyScore !== null
                    ? `${anomalyScore.toFixed(
                        2
                      )}%`
                    : "—"
                }
              />


              <AnomalyDetailCard
                label="Confidence"
                value={
                  anomalyConfidence !== null
                    ? `${anomalyConfidence.toFixed(
                        2
                      )}%`
                    : "—"
                }
              />


              <AnomalyDetailCard
                label="Severity"
                value={
                  anomalySeverity ||
                  "—"
                }
              />


              <AnomalyDetailCard
                label="Tampering"
                value={
                  anomalyTamperingDetected === null
                    ? "—"
                    : anomalyTamperingDetected
                    ? "Detected"
                    : "Not detected"
                }
              />

            </div>


            {/* ===========================================
                VALIDATION
            =========================================== */}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

              <ValidationCard
                title="Document Validation"
                status={
                  anomalyValidationFailed === true
                    ? "FLAGGED"
                    : anomalyValidationFailed === false
                    ? "PASS"
                    : "PENDING"
                }
                description={
                  anomalyValidationFailed === true
                    ? "Document validation reported a failure."
                    : anomalyValidationFailed === false
                    ? "Document validation checks passed."
                    : "Document validation result is unavailable."
                }
              />


              <ValidationCard
                title="Anomaly Classification"
                status={
                  anomalyIsAnomaly === true
                    ? "FLAGGED"
                    : anomalyIsAnomaly === false
                    ? "PASS"
                    : "PENDING"
                }
                description={
                  anomalyIsAnomaly === true
                    ? "The document differs from the learned genuine-document pattern."
                    : anomalyIsAnomaly === false
                    ? "The document matches the expected genuine-document pattern."
                    : "Anomaly classification is unavailable."
                }
              />

            </div>


            {/* ===========================================
                FRAUD TYPES
            =========================================== */}

            {anomalyFraudTypes.length > 0 && (

              <div>

                <p className="text-sm font-semibold text-gray-700 mb-2">
                  Detected Fraud Types
                </p>

                <div className="flex flex-wrap gap-2">

                  {anomalyFraudTypes.map(
                    (fraudType, index) => (

                      <span
                        key={`${fraudType}-${index}`}
                        className="text-xs font-medium px-3 py-1.5 rounded-full bg-red-100 text-red-700"
                      >
                        {fraudType}
                      </span>

                    )
                  )}

                </div>

              </div>

            )}


            {/* ===========================================
                EVIDENCE
            =========================================== */}

            {anomalyEvidence.length > 0 && (

              <div>

                <p className="text-sm font-semibold text-gray-700 mb-2">
                  Evidence
                </p>

                <div className="space-y-2">

                  {anomalyEvidence.map(
                    (item, index) => (

                      <div
                        key={index}
                        className="border rounded-lg px-4 py-3 bg-gray-50"
                      >

                        <p className="text-sm text-gray-700">

                          {typeof item === "string"
                            ? item
                            : item?.description ||
                              item?.message ||
                              JSON.stringify(
                                item
                              )}

                        </p>

                      </div>

                    )
                  )}

                </div>

              </div>

            )}


            {/* ===========================================
                RECOMMENDED ACTION
            =========================================== */}

            {anomalyRecommendedAction && (

              <div className="border rounded-xl p-4 bg-blue-50 border-blue-200">

                <p className="text-xs uppercase tracking-wide text-blue-600 font-semibold">
                  Recommended Action
                </p>

                <p className="text-sm text-blue-900 mt-1">
                  {anomalyRecommendedAction}
                </p>

              </div>

            )}

          </div>

        )}

      </div>


      {/* =================================================
          FACE
      ================================================= */}

      {(faceResult || livePhotoUrl) && (

        <div className="mt-6">

          <FaceComparePanel
            docPhotoUrl={
              scan?.doc_photo_url
            }
            livePhotoUrl={
              livePhotoUrl
            }
            matchResult={
              faceResult
            }
          />

        </div>

      )}


      {/* =================================================
          IDENTITY
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mt-6">

        <div className="flex items-center justify-between mb-4">

          <div>

            <h2 className="text-lg font-semibold text-brand">
              Identity Correlation
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              Screening for possible identity duplication
            </p>

          </div>

          <span className="text-xl">
            👤
          </span>

        </div>


        <div
          className={`border rounded-xl p-5 ${
            identityConflict
              ? "border-red-200 bg-red-50"
              : "border-gray-200 bg-gray-50"
          }`}
        >

          <div className="flex items-start gap-4">

            <div className="text-2xl">

              {identityConflict
                ? "⚠️"
                : identityAvailable
                ? "✓"
                : "⏳"}

            </div>


            <div>

              <p className="font-semibold text-gray-800">

                {identityConflict
                  ? "Possible Identity Conflict"
                  : identityAvailable
                  ? "No Suspicious Identity Overlap Detected"
                  : "Identity Correlation Pending"}

              </p>


              <p className="text-sm text-gray-500 mt-1">

                {identityConflict
                  ? "A similar identity record requires officer review."
                  : identityAvailable
                  ? "No suspicious duplicate identity was detected in the available records."
                  : "Identity linkage has not been performed yet."}

              </p>

            </div>

          </div>

        </div>

      </div>


      {/* =================================================
          EXPLAINABLE RISK EVIDENCE
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mt-6">

        <div className="flex items-center justify-between mb-5">

          <div>

            <h2 className="text-lg font-semibold text-brand">
              Explainable Risk Evidence
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              Key signals contributing to the screening decision
            </p>

          </div>

          <span className="text-xl">
            🔎
          </span>

        </div>


        <div className="space-y-3">

          <EvidenceRow
            label="Tampering Analysis"
            value={
              tamperAvailable &&
              tamperScore !== null
                ? tamperPrediction
                  ? `${tamperScore.toFixed(
                      2
                    )}/100 (${tamperPrediction})`
                  : `${tamperScore.toFixed(
                      2
                    )}/100`
                : "Pending"
            }
            flagged={
              tamperPrediction === "tampered"
            }
            pending={
              !tamperAvailable
            }
          />


          <EvidenceRow
            label="Anomaly Detection"
            value={
              anomalyAvailable &&
              anomalyScore !== null
                ? `${anomalyScore.toFixed(
                    2
                  )}/100 (${anomalyDecision || "RESULT"})`
                : "Pending"
            }
            flagged={
              anomalyDecision === "REJECT" ||
              anomalyIsAnomaly === true ||
              (anomalyScore !== null &&
                anomalyScore >= 70)
            }
            pending={
              !anomalyAvailable
            }
          />


          <EvidenceRow
            label="Face Verification"
            value={
              faceAvailable
                ? `${faceScore}% similarity`
                : "Not performed"
            }
            flagged={
              faceAvailable &&
              faceScore > 0 &&
              faceScore < 70
            }
            pending={
              !faceAvailable
            }
          />


          <EvidenceRow
            label="MRZ Validation"
            value={
              mrzValid === true
                ? "Valid"
                : mrzValid === false
                ? "Requires review"
                : "Pending"
            }
            flagged={
              mrzValid === false
            }
            pending={
              mrzValid === null
            }
          />


          <EvidenceRow
            label="Watchlist"
            value="See Watchlist Check"
            flagged={false}
            pending={true}
          />


          <EvidenceRow
            label="Identity Correlation"
            value={
              identityConflict
                ? "Possible conflict"
                : identityAvailable
                ? "No conflict detected"
                : "Pending"
            }
            flagged={
              identityConflict
            }
            pending={
              !identityAvailable
            }
          />


          <EvidenceRow
            label="Calibrated Risk"
            value={
              calibratedRisk !== null
                ? `${riskScorePercent.toFixed(
                    2
                  )}/100 (${riskLevel})`
                : "Pending"
            }
            flagged={
              riskLevel === "HIGH" ||
              riskLevel === "CRITICAL"
            }
            pending={
              calibratedRisk === null
            }
          />

        </div>

      </div>


      {/* =================================================
          SUMMARY
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mt-6">

        <h2 className="text-lg font-semibold text-brand mb-4">
          Screening Summary
        </h2>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

          <SummaryCard
            title="OCR Fields"
            value={
              Object.keys(fields).length
            }
            description="fields extracted"
          />


          <SummaryCard
            title="Tamper Score"
            value={
              tamperAvailable &&
              tamperScore !== null
                ? `${tamperScore.toFixed(
                    2
                  )}/100`
                : "—"
            }
            description="manipulation suspicion"
          />


          <SummaryCard
            title="Anomaly Result"
            value={
              anomalyAvailable
                ? anomalyDecision ||
                  "AVAILABLE"
                : "—"
            }
            description={
              anomalyAvailable
                ? anomalyScore !== null
                  ? `Score ${anomalyScore.toFixed(
                      2
                    )}/100`
                  : "Detection completed"
                : "anomaly screening"
            }
          />


          <SummaryCard
            title="AI Recommendation"
            value={
              aiDecision || "—"
            }
            description="model recommendation"
          />

        </div>

      </div>


      {/* =================================================
          OFFICER ACTION
      ================================================= */}

      <div className="bg-white rounded-xl shadow p-6 mt-6">

        <h2 className="text-lg font-semibold text-brand text-center mb-2">
          Officer Final Decision
        </h2>

        <p className="text-xs text-gray-500 text-center mb-5">
          The AI recommendation is advisory. The officer records the final screening decision.
        </p>


        {decisionError && (

          <div className="border border-red-200 bg-red-50 text-red-700 rounded-lg px-4 py-3 text-sm mb-5 text-center">
            ⚠️ {decisionError}
          </div>

        )}


        {officerDecision ? (

          <div className="border rounded-xl p-5 bg-gray-50 text-center">

            <p className="text-xs text-gray-500 uppercase tracking-wide">
              Officer Decision Recorded
            </p>

            <p
              className={`text-2xl font-bold mt-2 ${
                officerDecision.decision === "CLEAR"
                  ? "text-green-600"
                  : officerDecision.decision === "REVIEW"
                  ? "text-yellow-600"
                  : "text-red-600"
              }`}
            >

              {officerDecision.decision === "CLEAR"
                ? "✓ CLEARED"
                : officerDecision.decision === "REVIEW"
                ? "🔍 SECONDARY INSPECTION"
                : "✕ REJECTED"}

            </p>

          </div>

        ) : (

          <div className="flex flex-col sm:flex-row justify-center gap-4">

            <button
              type="button"
              disabled={decisionLoading}
              onClick={() =>
                handleOfficerDecision(
                  "CLEAR"
                )
              }
              className="px-8 py-3 rounded-lg border border-green-300 text-green-700 bg-green-50 hover:bg-green-100 disabled:opacity-50 disabled:cursor-not-allowed transition font-semibold"
            >
              {decisionLoading
                ? "Saving..."
                : "✓ CLEAR"}
            </button>


            <button
              type="button"
              disabled={decisionLoading}
              onClick={() =>
                handleOfficerDecision(
                  "REVIEW"
                )
              }
              className="px-8 py-3 rounded-lg bg-yellow-500 text-white hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition font-semibold"
            >
              {decisionLoading
                ? "Saving..."
                : "🔍 REVIEW"}
            </button>


            <button
              type="button"
              disabled={decisionLoading}
              onClick={() =>
                handleOfficerDecision(
                  "REJECTED"
                )
              }
              className="px-8 py-3 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition font-semibold"
            >
              {decisionLoading
                ? "Saving..."
                : "✕ REJECT"}
            </button>

          </div>

        )}

      </div>


      {/* =================================================
          PIPELINE
      ================================================= */}

      <div className="flex justify-center mt-8">

        <Link
          to={`/risk-assessment/${encodeURIComponent(
            scanId
          )}`}
          state={{
            scanResult: scan,
            faceResult,
            livePhotoUrl,
          }}
          className="bg-brand text-white px-6 py-3 rounded-lg font-medium hover:opacity-90 transition"
        >
          🔬 View Complete Risk Assessment Pipeline →
        </Link>

      </div>

    </div>
  );
}


// =====================================================
// NORMALIZE OFFICER DECISION
// =====================================================

function normalizeOfficerDecision(value) {
  if (!value) {
    return null;
  }

  if (typeof value === "string") {

    const decision =
      value.toUpperCase().trim();

    if (
      ![
        "CLEAR",
        "REVIEW",
        "REJECTED",
      ].includes(decision)
    ) {
      return null;
    }

    return {
      decision,
      decided_by: null,
      decided_at: null,
    };
  }


  if (typeof value === "object") {

    const decision =
      String(
        value.decision ||
        value.officer_decision ||
        ""
      )
        .toUpperCase()
        .trim();

    if (
      ![
        "CLEAR",
        "REVIEW",
        "REJECTED",
      ].includes(decision)
    ) {
      return null;
    }

    return {
      decision,
      decided_by:
        value.decided_by ||
        value.officer ||
        value.created_by ||
        null,
      decided_at:
        value.decided_at ||
        value.timestamp ||
        null,
      notes:
        value.notes ||
        value.note ||
        "",
    };
  }

  return null;
}


// =====================================================
// NORMALIZE AI DECISION
// =====================================================

function normalizeAiDecision(value) {
  if (!value) {
    return null;
  }

  const decision =
    String(
      typeof value === "object"
        ? value.decision ||
          value.ai_decision ||
          ""
        : value
    )
      .toUpperCase()
      .trim();

  if (decision === "CLEAR") {
    return "CLEAR";
  }

  if (decision === "REVIEW") {
    return "REVIEW";
  }

  if (
    decision === "REJECT" ||
    decision === "REJECTED"
  ) {
    return "REJECT";
  }

  return null;
}


// =====================================================
// NORMALIZE ANOMALY DECISION
// =====================================================

function normalizeAnomalyDecision(value) {
  if (!value) {
    return null;
  }

  const decision =
    String(value)
      .toUpperCase()
      .trim();

  if (
    decision.startsWith("CLEAR")
  ) {
    return "CLEAR";
  }

  if (
    decision.startsWith("REVIEW")
  ) {
    return "REVIEW";
  }

  if (
    decision.startsWith("REJECT")
  ) {
    return "REJECT";
  }

  return null;
}


// =====================================================
// NORMALIZE PERCENTAGE
// =====================================================

function normalizePercentage(value) {
  const number =
    Number(value);

  if (
    Number.isNaN(number)
  ) {
    return null;
  }

  return number <= 1
    ? number * 100
    : number;
}


// =====================================================
// DERIVE AI DECISION FROM RISK
// =====================================================

function deriveAiDecisionFromRisk(riskLevel) {
  switch (
    String(
      riskLevel || ""
    ).toUpperCase()
  ) {

    case "LOW":
      return "CLEAR";

    case "MEDIUM":
      return "REVIEW";

    case "HIGH":
    case "CRITICAL":
      return "REJECT";

    default:
      return null;
  }
}


// =====================================================
// FORMAT DATE
// =====================================================

function formatDate(value) {
  if (!value) {
    return "—";
  }

  try {
    return new Date(
      value
    ).toLocaleString();
  } catch {
    return "—";
  }
}


// =====================================================
// DECISION CARD
// =====================================================

function DecisionCard({
  title,
  value,
  subtitle,
  type,
}) {
  const styles = {

    clear:
      "bg-green-50 border-green-200 text-green-700",

    review:
      "bg-yellow-50 border-yellow-200 text-yellow-700",

    reject:
      "bg-red-50 border-red-200 text-red-700",

    pending:
      "bg-gray-50 border-gray-200 text-gray-500",
  };

  return (
    <div
      className={`border rounded-xl p-5 text-center ${
        styles[type] ||
        styles.pending
      }`}
    >

      <p className="text-xs uppercase tracking-wide opacity-70">
        {title}
      </p>

      <p className="text-2xl font-bold mt-2">
        {value}
      </p>

      {subtitle && (
        <p className="text-xs mt-2 opacity-75">
          {subtitle}
        </p>
      )}

    </div>
  );
}


// =====================================================
// VALIDATION CARD
// =====================================================

function ValidationCard({
  title,
  status,
  description,
}) {
  const isFlagged =
    status === "FLAGGED";

  const isPending =
    status === "PENDING";

  return (
    <div className="border rounded-xl p-4">

      <div className="flex items-center justify-between mb-3">

        <p className="font-medium text-gray-800">
          {title}
        </p>

        <span
          className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
            isFlagged
              ? "bg-red-100 text-red-700"
              : isPending
              ? "bg-gray-100 text-gray-600"
              : "bg-green-100 text-green-700"
          }`}
        >

          {isFlagged
            ? "⚠ FLAGGED"
            : isPending
            ? "PENDING"
            : "✓ PASS"}

        </span>

      </div>

      <p className="text-xs text-gray-500">
        {description}
      </p>

    </div>
  );
}


// =====================================================
// ANOMALY DETAIL CARD
// =====================================================

function AnomalyDetailCard({
  label,
  value,
}) {
  return (
    <div className="border rounded-lg p-4 bg-gray-50">

      <p className="text-xs text-gray-500">
        {label}
      </p>

      <p className="text-lg font-bold text-brand mt-1">
        {value}
      </p>

    </div>
  );
}


// =====================================================
// EVIDENCE ROW
// =====================================================

function EvidenceRow({
  label,
  value,
  flagged,
  pending,
}) {
  return (
    <div className="flex items-center justify-between border rounded-lg px-4 py-3">

      <div className="flex items-center gap-3">

        <span>
          {flagged
            ? "⚠️"
            : pending
            ? "⏳"
            : "✓"}
        </span>

        <span className="text-sm text-gray-700">
          {label}
        </span>

      </div>

      <span
        className={`text-sm font-medium ${
          flagged
            ? "text-red-600"
            : pending
            ? "text-gray-500"
            : "text-green-600"
        }`}
      >
        {value}
      </span>

    </div>
  );
}


// =====================================================
// SUMMARY CARD
// =====================================================

function SummaryCard({
  title,
  value,
  description,
}) {
  return (
    <div className="border rounded-lg p-4">

      <p className="text-xs text-gray-500">
        {title}
      </p>

      <p className="text-2xl font-bold text-brand mt-1">
        {value}
      </p>

      <p className="text-xs text-gray-400 mt-1">
        {description}
      </p>

    </div>
  );
}