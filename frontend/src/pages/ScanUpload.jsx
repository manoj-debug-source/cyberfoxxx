import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { runScreeningPipeline } from "../api/client";

import { useScreeningStore } from "../store/useScreeningStore";
import { createCase } from "../utils/caseStore";


export default function ScanUpload() {
  const navigate = useNavigate();

  /* =====================================================
     ZUSTAND
  ===================================================== */

  const setScan = useScreeningStore(
    (state) => state.setScan
  );

  const saveFile = useScreeningStore(
    (state) => state.setFile
  );


  /* =====================================================
     LOCAL STATE
  ===================================================== */

  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  /* =====================================================
     FILE SELECTION
  ===================================================== */

  function handleFileChange(event) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) return;

    /* Save file locally for this page */
    setFile(selectedFile);

    /* Save same file globally for Processing.jsx */
    saveFile(selectedFile);

    setError("");


    /* Preview only image files */

    if (
      selectedFile.type === "image/jpeg" ||
      selectedFile.type === "image/png"
    ) {
      setPreview(
        URL.createObjectURL(selectedFile)
      );
    } else {
      setPreview(null);
    }
  }


  /* =====================================================
     START VERIFICATION
  ===================================================== */

  async function handleSubmit() {
    if (!file) {
      setError(
        "Please select a document first."
      );
      return;
    }


    try {
      setLoading(true);
      setError("");


      /* -----------------------------------------------
         1. CREATE SCREENING
      ------------------------------------------------ */

      const result =
        await runScreeningPipeline(file);

      console.log(
        "Pipeline Result:",
        result
      );


      if (!result?.screening_id) {
        throw new Error(
          "Backend did not return a screening ID."
        );
      }


      const screeningId =
        result.screening_id;


      console.log(
        "Screening created:",
        screeningId
      );


      /* -----------------------------------------------
         2. SAVE ORIGINAL FILE
      ------------------------------------------------ */

      /*
       * Processing.jsx needs the actual File object
       * for anomaly/tamper analysis.
       */

      saveFile(file);


      /* -----------------------------------------------
         3. CREATE LOCAL CASE
      ------------------------------------------------ */

      createCase(
        screeningId,
        file.name
      );


      /* -----------------------------------------------
         4. STORE SCREENING
      ------------------------------------------------ */

      setScan(result);


      /* -----------------------------------------------
         5. GO TO PROCESSING
      ------------------------------------------------ */

      navigate(
        `/processing/${screeningId}`
      );

    } catch (err) {

      console.error(
        "Screening pipeline error:",
        err
      );

      setError(
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to start verification. Please check the backend."
      );

    } finally {
      setLoading(false);
    }
  }


  /* =====================================================
     UI
  ===================================================== */

  return (
    <div className="min-h-[75vh] flex items-center justify-center px-4 py-8">

      <div className="bg-white rounded-2xl shadow-lg p-6 md:p-8 max-w-2xl w-full">


        {/* HEADER */}

        <div className="text-center mb-8">

          <h1 className="text-2xl md:text-3xl font-bold text-brand">
            Document Verification
          </h1>

          <p className="text-gray-500 mt-2">
            Upload a document to begin CYBERFOXXX screening
          </p>

        </div>


        {/* ERROR */}

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">

            <strong>Error:</strong>{" "}

            {error}

          </div>
        )}


        {/* UPLOAD AREA */}

        <label
          htmlFor="document-upload"
          className="block cursor-pointer"
        >

          <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center hover:border-brand transition">

            <div className="text-4xl mb-4">
              📄
            </div>

            <h2 className="font-semibold text-gray-800">
              Upload Document
            </h2>

            <p className="text-sm text-gray-500 mt-2">
              Click to select a passport or identity document
            </p>

            <p className="text-xs text-gray-400 mt-2">
              PNG, JPG or PDF
            </p>

          </div>

        </label>


        <input
          id="document-upload"
          type="file"
          accept=".png,.jpg,.jpeg,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />


        {/* SELECTED FILE */}

        {file && (

          <div className="mt-6 rounded-xl border border-gray-200 bg-gray-50 p-4">

            <div className="flex items-center justify-between gap-4">

              <div className="min-w-0">

                <p className="text-sm font-semibold text-gray-800 truncate">
                  {file.name}
                </p>

                <p className="text-xs text-gray-500 mt-1">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>

              </div>


              <span className="text-xs font-semibold bg-green-100 text-green-700 px-3 py-1 rounded-full">
                READY
              </span>

            </div>


            {/* IMAGE PREVIEW */}

            {preview && (

              <div className="mt-4">

                <img
                  src={preview}
                  alt="Document preview"
                  className="max-h-64 mx-auto rounded-lg border border-gray-200 object-contain"
                />

              </div>

            )}

          </div>

        )}


        {/* START BUTTON */}

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!file || loading}
          className={`w-full mt-6 py-3 rounded-xl font-semibold transition ${
            !file || loading
              ? "bg-gray-300 text-gray-500 cursor-not-allowed"
              : "bg-brand text-white hover:opacity-90"
          }`}
        >

          {loading
            ? "Starting Verification..."
            : "Start Verification"}

        </button>


        {/* PROCESS DESCRIPTION */}

        <div className="mt-6 text-center">

          <p className="text-xs text-gray-400">
            CYBERFOXXX will analyze the document through
            multiple verification stages.
          </p>

        </div>

      </div>

    </div>
  );
}