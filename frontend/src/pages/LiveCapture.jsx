import { useRef, useState } from "react";
import { useParams } from "react-router-dom";

export default function LiveCapture() {
  const { scanId } = useParams();

  const videoRef = useRef(null);

  const [cameraActive, setCameraActive] =
    useState(false);

  const [error, setError] = useState("");

  async function startCamera() {

    try {

      const stream =
        await navigator.mediaDevices.getUserMedia({
          video: true,
        });

      videoRef.current.srcObject = stream;

      setCameraActive(true);

    } catch (err) {

      console.error(err);

      setError(
        "Camera permission was denied or unavailable."
      );

    }

  }

  return (
    <div className="max-w-xl mx-auto px-6">

      <h1 className="text-3xl font-bold text-slate-800">
        Live Face Capture
      </h1>

      <p className="text-gray-500 mt-2 mb-6">
        Screening ID: {scanId}
      </p>

      <div className="bg-white rounded-xl shadow p-6">

        <video
          ref={videoRef}
          autoPlay
          playsInline
          className="w-full rounded-lg bg-black"
        />

        {!cameraActive && (
          <button
            onClick={startCamera}
            className="w-full mt-5 bg-slate-900
            text-white py-3 rounded-lg"
          >
            Start Camera
          </button>
        )}

        {error && (
          <div className="mt-4 bg-red-50 text-red-700 p-4 rounded-lg">
            {error}
          </div>
        )}

      </div>

    </div>
  );
}