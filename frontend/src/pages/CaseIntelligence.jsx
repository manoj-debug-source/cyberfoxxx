import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getScreening } from "../api/client";


/* =========================================================
   SECTION
========================================================= */

function Section({ title, children, className = "" }) {
  return (
    <section
      className={`bg-slate-900/70 border border-slate-800 rounded-2xl p-6 shadow-xl ${className}`}
    >
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-bold tracking-[0.2em] text-slate-300 uppercase">
          {title}
        </h2>
      </div>

      {children}
    </section>
  );
}


/* =========================================================
   DATA ROW
========================================================= */

function DataRow({ label, value, mono = false }) {
  let displayValue = value;

  if (
    displayValue === null ||
    displayValue === undefined ||
    displayValue === ""
  ) {
    displayValue = "-";
  }

  if (typeof displayValue === "object") {
    displayValue = JSON.stringify(displayValue, null, 2);
  }

  return (
    <div className="py-3 border-b border-slate-800 last:border-b-0">
      <div className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wider text-slate-500">
          {label}
        </span>

        <span
          className={`text-sm text-slate-200 break-all ${
            mono ? "font-mono" : ""
          }`}
        >
          {String(displayValue)}
        </span>
      </div>
    </div>
  );
}


/* =========================================================
   STATUS BADGE
========================================================= */

function StatusBadge({ value }) {
  const status = String(value || "UNKNOWN").toUpperCase();

  let style =
    "bg-slate-800 text-slate-300 border-slate-700";

  if (
    status === "CLEAR" ||
    status === "COMPLETED" ||
    status === "VALID" ||
    status === "MATCHED" ||
    status === "PASS" ||
    status === "LOW" ||
    status === "NEW_IDENTITY"
  ) {
    style =
      "bg-green-500/10 text-green-400 border-green-500/30";
  }

  if (
    status === "REVIEW" ||
    status === "POSSIBLE_MATCH" ||
    status === "MEDIUM" ||
    status === "PENDING"
  ) {
    style =
      "bg-amber-500/10 text-amber-400 border-amber-500/30";
  }

  if (
    status === "REJECTED" ||
    status === "REJECT" ||
    status === "HIGH" ||
    status === "CRITICAL" ||
    status === "TAMPERED" ||
    status === "INVALID" ||
    status === "FAIL" ||
    status === "FAILED"
  ) {
    style =
      "bg-red-500/10 text-red-400 border-red-500/30";
  }

  return (
    <span
      className={`inline-flex px-3 py-1 rounded-full border text-xs font-bold tracking-wider ${style}`}
    >
      {status}
    </span>
  );
}


/* =========================================================
   SCORE CARD
========================================================= */

function ScoreCard({
  title,
  score,
  subtitle,
  suffix = "%",
}) {
  const numericScore =
    typeof score === "number"
      ? score
      : Number(score);

  const validScore =
    Number.isFinite(numericScore)
      ? numericScore
      : null;

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl p-5">
      <p className="text-xs uppercase tracking-widest text-slate-500">
        {title}
      </p>

      <div className="mt-3">
        <span className="text-3xl font-black text-white">
          {validScore !== null
            ? `${(validScore * 100).toFixed(2)}${suffix}`
            : "-"}
        </span>
      </div>

      {subtitle && (
        <p className="mt-2 text-xs text-slate-500">
          {subtitle}
        </p>
      )}
    </div>
  );
}


/* =========================================================
   PIPELINE STATUS
========================================================= */

function PipelineStatus({ title, stage, fallback }) {
  const status =
    stage?.status ||
    fallback ||
    "PENDING";

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm text-slate-300">
          {title}
        </span>

        <StatusBadge value={status} />
      </div>
    </div>
  );
}


/* =========================================================
   JSON VIEWER
========================================================= */

function JsonViewer({ title, data }) {
  if (
    data === null ||
    data === undefined ||
    (typeof data === "object" &&
      Object.keys(data).length === 0)
  ) {
    return null;
  }

  return (
    <div className="mt-5">
      <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">
        {title}
      </p>

      <pre className="bg-black/40 border border-slate-800 rounded-xl p-4 text-xs text-slate-300 overflow-x-auto whitespace-pre-wrap break-all">
        {typeof data === "string"
          ? data
          : JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}


/* =========================================================
   FORMAT DATE
========================================================= */

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}


/* =========================================================
   MAIN
========================================================= */

export default function CaseIntelligence() {

  const { screeningId } = useParams();

  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");


  /* =======================================================
     LOAD CASE
  ======================================================= */

  useEffect(() => {

    async function loadCase() {

      try {

        setLoading(true);
        setError("");

        const result =
          await getScreening(screeningId);

        setScan(result);

      } catch (err) {

        console.error(
          "Case intelligence error:",
          err
        );

        setError(
          err?.response?.data?.detail ||
          "Unable to load this screening case."
        );

      } finally {

        setLoading(false);

      }
    }

    if (screeningId) {
      loadCase();
    }

  }, [screeningId]);


  /* =======================================================
     LOADING
  ======================================================= */

  if (loading) {

    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">

        <div className="text-center">

          <div className="w-12 h-12 border-2 border-slate-700 border-t-cyan-400 rounded-full animate-spin mx-auto mb-5" />

          <p className="text-sm tracking-[0.25em] text-slate-400 uppercase">
            Loading case intelligence
          </p>

        </div>

      </div>
    );
  }


  /* =======================================================
     ERROR
  ======================================================= */

  if (error || !scan) {

    return (
      <div className="min-h-screen bg-[#020617] text-white p-8">

        <div className="max-w-3xl mx-auto">

          <Link
            to="/admin"
            className="inline-flex mb-8 text-sm text-slate-400 hover:text-white"
          >
            ← Back to Command Center
          </Link>

          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8">

            <h1 className="text-2xl font-bold text-red-400">
              CASE NOT FOUND
            </h1>

            <p className="mt-3 text-slate-400">
              {error ||
                "No screening data was returned."}
            </p>

            <p className="mt-5 font-mono text-sm text-slate-500">
              {screeningId}
            </p>

          </div>

        </div>

      </div>
    );
  }


  /* =======================================================
     EXTRACT DATA
  ======================================================= */

  const pipeline =
    scan.pipeline || {};


  /* -------------------------------------------------------
     OCR
  ------------------------------------------------------- */

  const ocr =
    scan.ocr ||
    pipeline.ocr?.result ||
    {};


  /* -------------------------------------------------------
     MRZ
  ------------------------------------------------------- */

  const mrz =
    scan.mrz ||
    pipeline.mrz?.result ||
    {};


  /* -------------------------------------------------------
     TAMPER
  ------------------------------------------------------- */

  const tamper =
    scan.tamper_analysis ||
    scan.tamper ||
    pipeline.tamper?.result ||
    {};


  /* -------------------------------------------------------
     ANOMALY
  ------------------------------------------------------- */

  const anomaly =
    scan.anomaly ||
    pipeline.anomaly?.result ||
    {};


  /* -------------------------------------------------------
     IDENTITY
  ------------------------------------------------------- */

  const identity =
    scan.identity_data ||
    {};


  /* -------------------------------------------------------
     IDENTITY LINKAGE
  ------------------------------------------------------- */

  const identityLinkage =
    scan.identity_linkage ||
    pipeline.identity_linkage?.result ||
    {};


  /* -------------------------------------------------------
     FACE
  ------------------------------------------------------- */

  const face =
    scan.face ||
    pipeline.face?.result ||
    {};


  /* -------------------------------------------------------
     IDENTITY VALIDATION
  ------------------------------------------------------- */

  const identityValidation =
    scan.identity_validation ||
    pipeline.identity_validation?.result ||
    {};


  /* -------------------------------------------------------
     RISK
  ------------------------------------------------------- */

  const risk =
    scan.risk ||
    pipeline.risk?.result ||
    {};


  /* -------------------------------------------------------
     OFFICER DECISION
  ------------------------------------------------------- */

  const officerDecision =
    scan.officer_decision ||
    pipeline.decision?.officer_decision ||
    null;


  /* -------------------------------------------------------
     AI DECISION
  ------------------------------------------------------- */

  const aiDecision =
    scan.ai_decision ||
    pipeline.decision?.decision ||
    "-";


  /* =======================================================
     DOCUMENT NUMBER
  ======================================================= */

  const documentNumber =
    scan.document_number ||
    identity.document_number ||
    pipeline.ocr?.document_number ||
    ocr.document_number ||
    ocr.fields?.document_number ||
    "-";


  /* =======================================================
     OCR CONFIDENCE
  ======================================================= */

  const ocrConfidence =
    pipeline.ocr?.confidence ??
    ocr.confidence ??
    null;


  /* =======================================================
     RISK SCORE
  ======================================================= */

  const calibratedRisk =
    typeof risk.calibrated_risk === "number"
      ? risk.calibrated_risk
      : Number(risk.calibrated_risk);

  const validRisk =
    Number.isFinite(calibratedRisk)
      ? calibratedRisk
      : null;


  /* =======================================================
     TAMPER SCORE
  ======================================================= */

  const tamperProbability =
    typeof tamper.tamper_probability === "number"
      ? tamper.tamper_probability
      : Number(tamper.tamper_probability);

  const genuineProbability =
    typeof tamper.genuine_probability === "number"
      ? tamper.genuine_probability
      : Number(tamper.genuine_probability);


  /* =======================================================
     ANOMALY SCORE
  ======================================================= */

  const anomalyScore =
    typeof anomaly.anomaly_score === "number"
      ? anomaly.anomaly_score
      : Number(anomaly.anomaly_score);


  /* =======================================================
     LINKAGE SCORE
  ======================================================= */

  const linkageScore =
    typeof identityLinkage.linkage_score === "number"
      ? identityLinkage.linkage_score
      : Number(identityLinkage.linkage_score);


  /* =======================================================
     PREVIOUS MATCHES
  ======================================================= */

  const previousMatches =
    Array.isArray(
      identityLinkage.previous_matches
    )
      ? identityLinkage.previous_matches
      : [];


  /* =======================================================
     OCR FIELDS
  ======================================================= */

  const ocrFields =
    ocr.fields ||
    ocr.extracted_fields ||
    ocr.extracted_data ||
    {};


  /* =======================================================
     MRZ DATA
  ======================================================= */

  const mrzData =
    mrz.mrz ||
    mrz.data ||
    mrz.raw ||
    mrz.lines ||
    mrz;


  return (
    <div className="min-h-screen bg-[#020617] text-white">

      {/* ===================================================
          HEADER
      =================================================== */}

      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">

        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">

          <div>

            <div className="flex items-center gap-3">

              <div className="w-3 h-3 bg-cyan-400 rounded-full shadow-lg shadow-cyan-400/50" />

              <span className="text-sm font-black tracking-[0.25em]">
                CYBERFOXXX
              </span>

            </div>

            <p className="mt-2 text-xs text-slate-500 tracking-widest uppercase">
              Case Intelligence Console
            </p>

          </div>


          <Link
            to="/admin"
            className="px-4 py-2 rounded-lg border border-slate-700 text-sm text-slate-300 hover:bg-slate-800 hover:text-white transition"
          >
            ← Command Center
          </Link>

        </div>

      </header>


      {/* ===================================================
          MAIN
      =================================================== */}

      <main className="max-w-7xl mx-auto px-6 py-8">


        {/* =================================================
            CASE HEADER
        ================================================= */}

        <div className="mb-8">

          <p className="text-xs tracking-[0.3em] text-cyan-400 uppercase">
            Administrative Investigation
          </p>

          <h1 className="mt-2 text-3xl md:text-4xl font-black tracking-tight">
            Case Intelligence
          </h1>

          <div className="mt-4 flex flex-wrap items-center gap-3">

            <span className="font-mono text-sm text-slate-400">
              {scan.screening_id ||
                screeningId}
            </span>

            <StatusBadge
              value={scan.status}
            />

          </div>

        </div>


        {/* =================================================
            DECISION OVERVIEW
        ================================================= */}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">


          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5">

            <p className="text-xs uppercase tracking-widest text-slate-500">
              AI Decision
            </p>

            <div className="mt-3">
              <StatusBadge value={aiDecision} />
            </div>

          </div>


          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5">

            <p className="text-xs uppercase tracking-widest text-slate-500">
              Officer Decision
            </p>

            <div className="mt-3">

              <StatusBadge
                value={
                  officerDecision?.decision ||
                  "NOT RECORDED"
                }
              />

            </div>

          </div>


          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5">

            <p className="text-xs uppercase tracking-widest text-slate-500">
              Calibrated Risk
            </p>

            <p className="mt-2 text-3xl font-black">

              {validRisk !== null
                ? `${(
                    validRisk * 100
                  ).toFixed(2)}%`
                : "-"}

            </p>

          </div>


          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5">

            <p className="text-xs uppercase tracking-widest text-slate-500">
              Risk Level
            </p>

            <div className="mt-3">

              <StatusBadge
                value={
                  risk.risk_level ||
                  "UNKNOWN"
                }
              />

            </div>

          </div>

        </div>


        {/* =================================================
            DOCUMENT INFORMATION
        ================================================= */}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Section title="Document Information">

            <DataRow
              label="Screening ID"
              value={scan.screening_id}
              mono
            />

            <DataRow
              label="Filename"
              value={scan.filename}
            />

            <DataRow
              label="Document Number"
              value={documentNumber}
              mono
            />

            <DataRow
              label="Document SHA-256"
              value={scan.document_hash}
              mono
            />

            <DataRow
              label="Created By"
              value={scan.created_by}
            />

            <DataRow
              label="Created At"
              value={formatDate(scan.created_at)}
            />

          </Section>


          {/* =================================================
              OFFICER INFORMATION
          ================================================= */}

          <Section title="Officer Decision">

            <DataRow
              label="Officer"
              value={
                officerDecision?.decided_by ||
                scan.created_by ||
                "-"
              }
            />

            <DataRow
              label="Decision"
              value={
                officerDecision?.decision ||
                "NOT RECORDED"
              }
            />

            <DataRow
              label="Decision Time"
              value={formatDate(
                officerDecision?.decided_at
              )}
            />

          </Section>


          {/* =================================================
              OCR
          ================================================= */}

          <Section title="OCR Extraction">

            <PipelineStatus
              title="OCR Module"
              stage={pipeline.ocr}
              fallback={
                scan.ocr
                  ? "COMPLETED"
                  : "PENDING"
              }
            />

            <DataRow
              label="Document Number"
              value={documentNumber}
              mono
            />

            <DataRow
              label="OCR Confidence"
              value={
                ocrConfidence !== null &&
                Number.isFinite(
                  Number(ocrConfidence)
                )
                  ? `${(
                      Number(ocrConfidence) * 100
                    ).toFixed(2)}%`
                  : "-"
              }
            />

            <JsonViewer
              title="Extracted OCR Fields"
              data={ocrFields}
            />

            <JsonViewer
              title="Raw OCR Result"
              data={ocr}
            />

          </Section>


          {/* =================================================
              MRZ
          ================================================= */}

          <Section title="MRZ Validation">

            <PipelineStatus
              title="MRZ Module"
              stage={pipeline.mrz}
              fallback={
                scan.mrz
                  ? "COMPLETED"
                  : "PENDING"
              }
            />

            <DataRow
              label="MRZ Status"
              value={
                mrz.valid !== undefined
                  ? mrz.valid
                    ? "VALID"
                    : "INVALID"
                  : mrz.status ||
                    "-"
              }
            />

            <DataRow
              label="MRZ Checksum"
              value={
                mrz.checksum_valid !== undefined
                  ? mrz.checksum_valid
                    ? "VALID"
                    : "INVALID"
                  : "-"
              }
            />

            <JsonViewer
              title="MRZ Data"
              data={mrzData}
            />

          </Section>


          {/* =================================================
              TAMPER
          ================================================= */}

          <Section title="Tamper Detection">

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">

              <ScoreCard
                title="Tamper Probability"
                score={tamperProbability}
                subtitle="Forgery probability"
              />

              <ScoreCard
                title="Genuine Probability"
                score={genuineProbability}
                subtitle="Authenticity probability"
              />

            </div>

            <DataRow
              label="Prediction"
              value={
                tamper.prediction
                  ? tamper.prediction.toUpperCase()
                  : "-"
              }
            />

            <DataRow
              label="Decision Threshold"
              value={
                typeof tamper.threshold === "number"
                  ? `${(
                      tamper.threshold * 100
                    ).toFixed(2)}%`
                  : "-"
              }
            />

            <DataRow
              label="Raw Model Output"
              value={
                typeof tamper.raw_model_output ===
                "number"
                  ? tamper.raw_model_output.toFixed(4)
                  : "-"
              }
            />

          </Section>


          {/* =================================================
              ANOMALY
          ================================================= */}

          <Section title="Anomaly Detection">

            <PipelineStatus
              title="Anomaly Module"
              stage={pipeline.anomaly}
              fallback={
                scan.anomaly
                  ? "COMPLETED"
                  : "PENDING"
              }
            />

            <DataRow
              label="Anomaly Score"
              value={
                Number.isFinite(anomalyScore)
                  ? `${(
                      anomalyScore * 100
                    ).toFixed(2)}%`
                  : "-"
              }
            />

            <DataRow
              label="Prediction"
              value={
                anomaly.prediction ||
                anomaly.result ||
                anomaly.status ||
                "-"
              }
            />

            <JsonViewer
              title="Anomaly Result"
              data={anomaly}
            />

          </Section>


          {/* =================================================
              IDENTITY VALIDATION
          ================================================= */}

          <Section title="Identity Validation">

            <PipelineStatus
              title="Validation Module"
              stage={
                pipeline.identity_validation
              }
              fallback={
                scan.identity_validation
                  ? "COMPLETED"
                  : "PENDING"
              }
            />

            <DataRow
              label="Validation Status"
              value={
                identityValidation.status ||
                identityValidation.result ||
                "-"
              }
            />

            <DataRow
              label="Validation Risk"
              value={
                identityValidation.risk !==
                undefined
                  ? identityValidation.risk
                  : "-"
              }
            />

            <JsonViewer
              title="Validation Evidence"
              data={identityValidation}
            />

          </Section>


          {/* =================================================
              FACE & LIVENESS
          ================================================= */}

          <Section title="Face & Liveness">

            <PipelineStatus
              title="Face Module"
              stage={pipeline.face}
              fallback={
                scan.face
                  ? "COMPLETED"
                  : "PENDING"
              }
            />

            <DataRow
              label="Face Match Score"
              value={
                typeof face.match_score ===
                "number"
                  ? `${(
                      face.match_score * 100
                    ).toFixed(2)}%`
                  : "-"
              }
            />

            <DataRow
              label="Liveness"
              value={
                face.liveness ||
                face.liveness_status ||
                "-"
              }
            />

            <JsonViewer
              title="Face Analysis"
              data={face}
            />

          </Section>


          {/* =================================================
              IDENTITY LINKAGE
          ================================================= */}

          <Section title="Identity Linkage">

            <PipelineStatus
              title="Linkage Module"
              stage={
                pipeline.identity_linkage
              }
              fallback={
                scan.identity_linkage
                  ? "COMPLETED"
                  : "PENDING"
              }
            />

            <DataRow
              label="Officer-Entered Name"
              value={identity.name}
            />

            <DataRow
              label="Officer-Entered Contact"
              value={identity.contact_number}
              mono
            />

            <DataRow
              label="Document Number"
              value={identity.document_number}
              mono
            />

            <DataRow
              label="Linkage Status"
              value={
                identityLinkage.status ||
                "-"
              }
            />

            <DataRow
              label="Match Found"
              value={
                identityLinkage.match_found !==
                undefined
                  ? identityLinkage.match_found
                    ? "YES"
                    : "NO"
                  : "-"
              }
            />

            <DataRow
              label="Linkage Score"
              value={
                Number.isFinite(linkageScore)
                  ? `${(
                      linkageScore * 100
                    ).toFixed(2)}%`
                  : "-"
              }
            />

            <DataRow
              label="Identity SHA-256"
              value={scan.identity_hash}
              mono
            />

          </Section>


          {/* =================================================
              RISK CALIBRATION
          ================================================= */}

          <Section title="Risk Calibration">

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-6 mb-5">

              <p className="text-xs uppercase tracking-widest text-slate-500">
                Calibrated Risk
              </p>

              <p className="mt-2 text-5xl font-black">

                {validRisk !== null
                  ? `${(
                      validRisk * 100
                    ).toFixed(2)}`
                  : "-"}

                <span className="text-lg text-slate-500 ml-2">
                  / 100
                </span>

              </p>

              <div className="mt-4">

                <StatusBadge
                  value={
                    risk.risk_level ||
                    "UNKNOWN"
                  }
                />

              </div>

            </div>

            <DataRow
              label="Model Version"
              value={
                risk.model_version
              }
            />

            <DataRow
              label="Calibration Method"
              value={
                risk.calibration_method
              }
            />

          </Section>

        </div>


        {/* =================================================
            PREVIOUS IDENTITY MATCHES
        ================================================= */}

        {previousMatches.length > 0 && (

          <div className="mt-8">

            <Section title="Previous Identity Matches">

              <div className="overflow-x-auto">

                <table className="w-full text-left">

                  <thead>

                    <tr className="border-b border-slate-800">

                      <th className="py-3 pr-4 text-xs uppercase tracking-widest text-slate-500">
                        Screening ID
                      </th>

                      <th className="py-3 px-4 text-xs uppercase tracking-widest text-slate-500">
                        Match Score
                      </th>

                      <th className="py-3 pl-4 text-xs uppercase tracking-widest text-slate-500">
                        Evidence
                      </th>

                    </tr>

                  </thead>

                  <tbody>

                    {previousMatches.map(
                      (match, index) => {

                        const score =
                          typeof match.score ===
                          "number"
                            ? match.score
                            : Number(match.score);

                        return (

                          <tr
                            key={`${match.screening_id || "match"}-${index}`}
                            className="border-b border-slate-800 last:border-b-0"
                          >

                            <td className="py-4 pr-4 font-mono text-sm text-cyan-400">
                              {match.screening_id ||
                                "-"}
                            </td>

                            <td className="py-4 px-4 text-sm text-slate-200">

                              {Number.isFinite(score)
                                ? `${(
                                    score * 100
                                  ).toFixed(2)}%`
                                : "-"}

                            </td>

                            <td className="py-4 pl-4 text-sm text-slate-400">

                              {Array.isArray(
                                match.evidence
                              )
                                ? match.evidence.join(
                                    ", "
                                  )
                                : JSON.stringify(
                                    match.evidence ||
                                      "-"
                                  )}

                            </td>

                          </tr>

                        );

                      }
                    )}

                  </tbody>

                </table>

              </div>

            </Section>

          </div>

        )}


        {/* =================================================
            SCREENING PIPELINE
        ================================================= */}

        <div className="mt-8">

          <Section title="Screening Pipeline">

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">

              <PipelineStatus
                title="SHA-256"
                stage={pipeline.sha256}
                fallback={
                  scan.document_hash
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="OCR"
                stage={pipeline.ocr}
                fallback={
                  scan.ocr
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="MRZ"
                stage={pipeline.mrz}
                fallback={
                  scan.mrz
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="Tamper Detection"
                stage={pipeline.tamper}
                fallback={
                  scan.tamper_analysis ||
                  scan.tamper
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="Anomaly Detection"
                stage={pipeline.anomaly}
                fallback={
                  scan.anomaly
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="Identity Validation"
                stage={
                  pipeline.identity_validation
                }
                fallback={
                  scan.identity_validation
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="Face & Liveness"
                stage={pipeline.face}
                fallback={
                  scan.face
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="Identity Linkage"
                stage={
                  pipeline.identity_linkage
                }
                fallback={
                  scan.identity_linkage
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="Risk Calibration"
                stage={pipeline.risk}
                fallback={
                  scan.risk
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

              <PipelineStatus
                title="AI Decision"
                stage={pipeline.decision}
                fallback={
                  scan.ai_decision
                    ? "COMPLETED"
                    : "PENDING"
                }
              />

            </div>

          </Section>

        </div>


        {/* =================================================
            BLOCKCHAIN / CRYPTOGRAPHIC EVIDENCE
        ================================================= */}

        <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">

          <Section title="Blockchain / Audit Evidence">

            <DataRow
              label="Document SHA-256"
              value={scan.document_hash}
              mono
            />

            <DataRow
              label="Identity SHA-256"
              value={scan.identity_hash}
              mono
            />

            <DataRow
              label="Screening Created"
              value={
                pipeline.sha256?.status ||
                "-"
              }
            />

            <DataRow
              label="Identity Linked"
              value={
                pipeline.identity_linkage?.status ||
                (
                  scan.identity_linkage
                    ? "COMPLETED"
                    : "PENDING"
                )
              }
            />

          </Section>


          <Section title="Case Metadata">

            <DataRow
              label="Screening ID"
              value={
                scan.screening_id ||
                screeningId
              }
              mono
            />

            <DataRow
              label="Current Status"
              value={scan.status}
            />

            <DataRow
              label="AI Decision"
              value={aiDecision}
            />

            <DataRow
              label="Officer Decision"
              value={
                officerDecision?.decision ||
                "NOT RECORDED"
              }
            />

            <DataRow
              label="Officer"
              value={
                officerDecision?.decided_by ||
                scan.created_by ||
                "-"
              }
            />

            <DataRow
              label="Decision Timestamp"
              value={formatDate(
                officerDecision?.decided_at
              )}
            />

          </Section>

        </div>


        {/* =================================================
            RAW PIPELINE DATA
        ================================================= */}

        <div className="mt-8">

          <Section title="Complete Pipeline Evidence">

            <JsonViewer
              title="Pipeline Object"
              data={pipeline}
            />

          </Section>

        </div>


        {/* =================================================
            CRYPTOGRAPHIC FOOTER
        ================================================= */}

        <div className="mt-8 bg-slate-950 border border-slate-800 rounded-2xl p-6">

          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
            Cryptographic Evidence
          </p>


          <div className="mt-5">

            <p className="text-xs text-slate-500 mb-2">
              Document SHA-256
            </p>

            <p className="font-mono text-xs md:text-sm text-cyan-400 break-all">
              {scan.document_hash || "-"}
            </p>

          </div>


          <div className="mt-5">

            <p className="text-xs text-slate-500 mb-2">
              Identity SHA-256
            </p>

            <p className="font-mono text-xs md:text-sm text-purple-400 break-all">
              {scan.identity_hash || "-"}
            </p>

          </div>

        </div>


        {/* =================================================
            BACK BUTTON
        ================================================= */}

        <div className="mt-8 pb-10">

          <Link
            to="/admin"
            className="inline-flex px-5 py-3 rounded-xl border border-slate-700 text-sm font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition"
          >
            ← Return to Command Center
          </Link>

        </div>

      </main>

    </div>
  );
}