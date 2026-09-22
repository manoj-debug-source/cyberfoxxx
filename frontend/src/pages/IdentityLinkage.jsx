import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getScreening,
  linkIdentityToLedger,
} from "../api/client";

export default function IdentityLinkage() {
  const { scanId } = useParams();
  const navigate = useNavigate();

  const [screening, setScreening] = useState(null);

  const [name, setName] = useState("");
  const [contactNumber, setContactNumber] = useState("");

  const [result, setResult] = useState(null);
  const [loadingScreening, setLoadingScreening] = useState(true);
  const [loading, setLoading] = useState(false);

  // =====================================================
  // LOAD SCREENING
  // =====================================================

  useEffect(() => {
    async function loadScreening() {
      if (!scanId) {
        setResult({
          type: "error",
          error: "No Screening ID was provided.",
        });

        setLoadingScreening(false);
        return;
      }

      try {
        setLoadingScreening(true);
        setResult(null);

        const data = await getScreening(scanId);

        setScreening(data);
      } catch (error) {
        console.error(
          "Failed to load screening:",
          error
        );

        setResult({
          type: "error",
          error:
            error.response?.data?.detail ||
            "Unable to load screening information.",
        });
      } finally {
        setLoadingScreening(false);
      }
    }

    loadScreening();
  }, [scanId]);

  // =====================================================
  // LINK IDENTITY
  // =====================================================

  async function handleLink() {
    setResult(null);

    const trimmedName = name.trim();
    const cleanedNumber = contactNumber.replace(/\s+/g, "");

    if (!trimmedName) {
      setResult({
        type: "error",
        error: "Please enter the person's full name.",
      });
      return;
    }

    if (!cleanedNumber) {
      setResult({
        type: "error",
        error: "Please enter the contact number.",
      });
      return;
    }

    if (!/^[+]?[0-9]{10,15}$/.test(cleanedNumber)) {
      setResult({
        type: "error",
        error:
          "Please enter a valid contact number containing 10–15 digits.",
      });
      return;
    }

    if (!screening) {
      setResult({
        type: "error",
        error:
          "Screening information has not loaded yet.",
      });
      return;
    }

    try {
      setLoading(true);

      /*
       * Only officer-entered identity information
       * is sent from the frontend.
       *
       * Backend obtains:
       * - screening_id
       * - document_number
       * - document_hash
       * - created_by
       *
       * from the authenticated screening record.
       */

      const response = await linkIdentityToLedger({
        screening_id:
          screening.screening_id || scanId,

        identity_data: {
          name: trimmedName,
          contact_number: cleanedNumber,
        },
      });

      setResult({
        type: "success",
        ...response,
      });
    } catch (error) {
      console.error(
        "Identity linkage failed:",
        error
      );

      setResult({
        type: "error",
        error:
          error.response?.data?.detail ||
          error.response?.data?.message ||
          "Failed to link identity.",
      });
    } finally {
      setLoading(false);
    }
  }

  // =====================================================
  // LOADING SCREEN
  // =====================================================

  if (loadingScreening) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center px-6">
        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-10 text-center">

          <div className="text-4xl mb-4">
            🔗
          </div>

          <h2 className="text-xl font-bold text-slate-800">
            Loading Identity Record
          </h2>

          <p className="text-slate-500 mt-2">
            Retrieving screening information...
          </p>

        </div>
      </div>
    );
  }

  // =====================================================
  // SCREENING LOAD FAILURE
  // =====================================================

  if (!screening) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-10">

        <div className="bg-white rounded-2xl shadow-lg border border-red-200 p-8">

          <div className="text-4xl mb-4">
            ⚠️
          </div>

          <h1 className="text-2xl font-bold text-red-600">
            Identity Linkage
          </h1>

          <p className="text-red-600 mt-3">
            {result?.error ||
              "Screening information unavailable."}
          </p>

          <button
            type="button"
            onClick={() => navigate("/officer")}
            className="mt-6 px-5 py-3 rounded-lg bg-slate-800 text-white font-semibold hover:bg-slate-900"
          >
            Back to Officer Dashboard
          </button>

        </div>

      </div>
    );
  }

  // =====================================================
  // AUTO-LOADED DATA
  // =====================================================

  const screeningId =
    screening.screening_id || scanId;

  const documentNumber =
    screening.identity_data?.document_number ||
    screening.document_number ||
    screening.ocr?.document_number ||
    screening.pipeline?.ocr?.document_number ||
    screening.pipeline?.ocr?.result?.document_number ||
    screening.pipeline?.ocr?.result?.fields?.document_number ||
    "Not available";

  const documentHash =
    screening.document_hash ||
    screening.pipeline?.sha256?.document_hash ||
    "Not available";

  // =====================================================
  // LINKAGE RESULT
  // =====================================================

  const linkage =
    result?.identity_linkage || null;

  const linkageStatus =
    linkage?.status || null;

  const linkageScore =
    typeof linkage?.linkage_score === "number"
      ? linkage.linkage_score
      : null;

  const scorePercentage =
    linkageScore !== null
      ? (linkageScore * 100).toFixed(2)
      : null;

  const isMatched =
    linkageStatus === "MATCHED";

  const isPossibleMatch =
    linkageStatus === "POSSIBLE_MATCH";

  // =====================================================
  // UI
  // =====================================================

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">

      {/* ================================================= */}
      {/* HEADER */}
      {/* ================================================= */}

      <div className="mb-7">

        <div className="flex items-center gap-4">

          <div className="w-12 h-12 rounded-xl bg-slate-800 text-white flex items-center justify-center text-2xl shadow">
            🔗
          </div>

          <div>

            <h1 className="text-3xl font-bold text-slate-800">
              Identity Linkage
            </h1>

            <p className="text-slate-500 mt-1">
              Associate the verified identity with the secure audit ledger.
            </p>

          </div>

        </div>

      </div>

      {/* ================================================= */}
      {/* NOTICE */}
      {/* ================================================= */}

      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">

        <div className="flex gap-3">

          <div className="text-blue-600 text-lg">
            ℹ️
          </div>

          <div>

            <p className="font-semibold text-blue-900">
              Officer verification required
            </p>

            <p className="text-sm text-blue-800 mt-1">
              Verify the person's name and contact number before linking
              the identity to the ledger.
            </p>

          </div>

        </div>

      </div>

      {/* ================================================= */}
      {/* SCREENING INFORMATION */}
      {/* ================================================= */}

      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6 mb-6">

        <div className="flex items-center justify-between mb-6">

          <div>

            <h2 className="text-xl font-bold text-slate-800">
              Screening Information
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Retrieved automatically from the screening pipeline.
            </p>

          </div>

          <span className="text-xs font-bold px-3 py-1.5 rounded-full bg-green-100 text-green-700">
            AUTO-LOADED
          </span>

        </div>

        <div className="space-y-5">

          {/* Screening ID */}

          <div>

            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Screening ID
            </label>

            <input
              type="text"
              value={screeningId}
              readOnly
              className="w-full border border-slate-200 rounded-lg p-3 bg-slate-50 text-slate-600 font-mono"
            />

          </div>

          {/* Document Number */}

          <div>

            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Document Number
            </label>

            <input
              type="text"
              value={documentNumber}
              readOnly
              className="w-full border border-slate-200 rounded-lg p-3 bg-slate-50 text-slate-600 font-mono"
            />

            <p className="text-xs text-slate-400 mt-1">
              Retrieved automatically from OCR/screening data.
            </p>

          </div>

          {/* Document Hash */}

          <div>

            <label className="block text-sm font-semibold text-slate-700 mb-2">
              SHA-256 Document Hash
            </label>

            <textarea
              value={documentHash}
              readOnly
              rows={3}
              className="w-full border border-slate-200 rounded-lg p-3 bg-slate-50 text-slate-600 font-mono text-xs break-all resize-none"
            />

            <p className="text-xs text-slate-400 mt-1">
              Cryptographic hash generated from the uploaded document.
            </p>

          </div>

          {/* Filename */}

          {screening.filename && (
            <div>

              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Uploaded Document
              </label>

              <div className="border border-slate-200 rounded-lg p-3 bg-slate-50 text-slate-600">
                {screening.filename}
              </div>

            </div>
          )}

        </div>

      </div>

      {/* ================================================= */}
      {/* OFFICER INPUT */}
      {/* ================================================= */}

      <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-6">

        <div className="flex items-center gap-3 mb-6">

          <div>

            <h2 className="text-xl font-bold text-slate-800">
              Officer Identity Input
            </h2>

            <p className="text-sm text-slate-500 mt-1">
              Only these two fields require manual entry.
            </p>

          </div>

          <span className="text-xs font-bold px-2.5 py-1 rounded bg-amber-100 text-amber-700">
            REQUIRED
          </span>

        </div>

        <div className="space-y-5">

          {/* Name */}

          <div>

            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Full Name
            </label>

            <input
              type="text"
              placeholder="Enter person's full name"
              value={name}
              onChange={(e) =>
                setName(e.target.value)
              }
              disabled={
                loading ||
                result?.type === "success"
              }
              className="w-full border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-slate-500 disabled:bg-slate-100"
            />

          </div>

          {/* Contact */}

          <div>

            <label className="block text-sm font-semibold text-slate-700 mb-2">
              Contact Number
            </label>

            <input
              type="tel"
              placeholder="Enter contact number"
              value={contactNumber}
              onChange={(e) =>
                setContactNumber(e.target.value)
              }
              disabled={
                loading ||
                result?.type === "success"
              }
              className="w-full border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-slate-500 disabled:bg-slate-100"
            />

            <p className="text-xs text-slate-400 mt-1">
              Enter 10–15 digits. Spaces are automatically removed.
            </p>

          </div>

          {/* LINK */}

          <button
            type="button"
            onClick={handleLink}
            disabled={
              loading ||
              result?.type === "success"
            }
            className="w-full bg-slate-800 text-white rounded-lg p-3.5 font-semibold hover:bg-slate-900 disabled:opacity-50 transition"
          >
            {loading
              ? "Linking Identity..."
              : result?.type === "success"
              ? "✓ Identity Linked"
              : "🔗 Link Identity to Ledger"}
          </button>

        </div>

      </div>

      {/* ================================================= */}
      {/* ERROR */}
      {/* ================================================= */}

      {result?.type === "error" && (
        <div className="mt-6 bg-red-50 border border-red-200 rounded-2xl p-6">

          <div className="flex gap-3">

            <div className="text-red-600 text-xl">
              ✕
            </div>

            <div>

              <h2 className="font-bold text-red-700">
                Identity Linkage Failed
              </h2>

              <p className="text-red-600 mt-2">
                {result.error}
              </p>

            </div>

          </div>

        </div>
      )}

      {/* ================================================= */}
      {/* SUCCESS */}
      {/* ================================================= */}

      {result?.type === "success" && (
        <div className="mt-6 bg-white rounded-2xl shadow-lg border border-green-200 p-6">

          {/* Success header */}

          <div className="flex items-center gap-4 mb-6">

            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center text-green-700 text-xl font-bold">
              ✓
            </div>

            <div>

              <h2 className="text-xl font-bold text-green-700">
                Identity Linked Successfully
              </h2>

              <p className="text-sm text-slate-500 mt-1">
                The identity linkage has been recorded in the secure ledger.
              </p>

            </div>

          </div>

          {/* Match status */}

          {linkageStatus && (
            <div
              className={`rounded-xl p-5 mb-6 border ${
                isMatched
                  ? "bg-green-50 border-green-200"
                  : isPossibleMatch
                  ? "bg-amber-50 border-amber-200"
                  : "bg-slate-50 border-slate-200"
              }`}
            >

              <p className="text-sm font-semibold text-slate-500">
                Identity Match Result
              </p>

              <p
                className={`text-2xl font-bold mt-1 ${
                  isMatched
                    ? "text-green-700"
                    : isPossibleMatch
                    ? "text-amber-700"
                    : "text-slate-700"
                }`}
              >
                {linkageStatus}
              </p>

              {scorePercentage !== null && (
                <p className="text-sm text-slate-600 mt-2">
                  Linkage Score:{" "}
                  <strong>
                    {scorePercentage}%
                  </strong>
                </p>
              )}

            </div>
          )}

          {/* Backend information */}

          <div className="space-y-4 text-sm">

            <div className="flex justify-between gap-4">
              <strong className="text-slate-600">
                Screening ID
              </strong>

              <span className="font-mono text-slate-800">
                {result.screening_id || screeningId}
              </span>
            </div>

            <div className="flex justify-between gap-4">
              <strong className="text-slate-600">
                Event
              </strong>

              <span className="font-semibold text-green-700">
                {result.event_type || "IDENTITY_LINKED"}
              </span>
            </div>

            <div>
              <strong className="text-slate-600">
                Identity Hash
              </strong>

              <p className="font-mono text-xs text-slate-700 break-all mt-1">
                {result.identity_hash || "Generated"}
              </p>
            </div>

            <div>
              <strong className="text-slate-600">
                Document Hash
              </strong>

              <p className="font-mono text-xs text-slate-700 break-all mt-1">
                {result.document_hash || documentHash}
              </p>
            </div>

            <div>
              <strong className="text-slate-600">
                Created By
              </strong>

              <p className="text-slate-800 mt-1">
                {result.created_by || "Authenticated officer"}
              </p>
            </div>

          </div>

          {/* Navigation */}

          <div className="flex flex-col sm:flex-row gap-3 mt-7">

            <button
              type="button"
              onClick={() => navigate("/audit")}
              className="flex-1 bg-slate-800 text-white rounded-lg p-3 font-semibold hover:bg-slate-900"
            >
              🔐 View Audit Ledger
            </button>

            <button
              type="button"
              onClick={() => navigate("/officer")}
              className="flex-1 border border-slate-300 rounded-lg p-3 font-semibold text-slate-700 hover:bg-slate-50"
            >
              Officer Dashboard
            </button>

          </div>

        </div>
      )}

    </div>
  );
}