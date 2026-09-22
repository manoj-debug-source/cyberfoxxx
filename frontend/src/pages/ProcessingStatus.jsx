import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getScanStatus } from "../api/client";

const STAGES = [
  {
    key: "quality",
    label: "Image Quality Check",
  },
  {
    key: "ocr",
    label: "OCR + Field Extraction",
  },
  {
    key: "tamper",
    label: "Tamper Detection (CNN + Autoencoder)",
  },
  {
    key: "face",
    label: "Face Verification + Liveness",
  },
  {
    key: "linkage",
    label: "Identity Linkage Search",
  },
  {
    key: "risk",
    label: "Risk Fusion + Calibration",
  },
];

export default function ProcessingStatus() {
  const { scanId } = useParams();
  const navigate = useNavigate();

  const [completedStages, setCompletedStages] = useState([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("processing");
  const [error, setError] = useState("");

  useEffect(() => {
    let interval;

    async function checkStatus() {
      try {
        const data = await getScanStatus(scanId);

        setCompletedStages(
          data.completed_stages || []
        );

        setProgress(data.progress_pct || 0);
        setStatus(data.status);

        if (data.status === "complete") {
          clearInterval(interval);

          navigate(`/evidence/${scanId}`);
        }

      } catch (err) {
        console.error(err);
        setError("Unable to retrieve screening status.");
      }
    }

    checkStatus();

    interval = setInterval(checkStatus, 1200);

    return () => clearInterval(interval);
  }, [scanId, navigate]);

  return (
    <div className="max-w-2xl mx-auto px-6">

      <h1 className="text-3xl font-bold text-slate-800">
        Screening in Progress
      </h1>

      <p className="text-gray-500 mt-2 mb-6">
        The verification pipeline is analyzing the document.
      </p>

      <div className="bg-white rounded-xl shadow p-6">

        <div className="mb-6">

          <div className="flex justify-between text-sm mb-2">
            <span>Progress</span>
            <span>{progress}%</span>
          </div>

          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-slate-800 transition-all"
              style={{
                width: `${progress}%`,
              }}
            />
          </div>

        </div>

        <div className="space-y-4">

          {STAGES.map((stage) => {

            const done =
              completedStages.includes(stage.key);

            return (
              <div
                key={stage.key}
                className="flex items-center gap-3"
              >

                <span
                  className={
                    done
                      ? "text-green-600 text-xl"
                      : "text-gray-300 text-xl"
                  }
                >
                  {done ? "✓" : "○"}
                </span>

                <span
                  className={
                    done
                      ? "font-semibold text-gray-800"
                      : "text-gray-400"
                  }
                >
                  {stage.label}
                </span>

              </div>
            );
          })}

        </div>

        {status === "failed" && (
          <div className="mt-6 bg-red-50 text-red-700 p-4 rounded-lg">
            Screening failed. Please try again.
          </div>
        )}

        {error && (
          <div className="mt-6 bg-red-50 text-red-700 p-4 rounded-lg">
            {error}
          </div>
        )}

      </div>

    </div>
  );
}