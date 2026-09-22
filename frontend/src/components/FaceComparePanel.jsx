export default function FaceComparePanel({ docPhotoUrl, livePhotoUrl, matchResult }) {
  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="font-semibold text-brand mb-3">Face Verification</h3>
      <div className="flex gap-4 mb-3">
        <div className="flex-1 text-center">
          <img
            src={docPhotoUrl}
            alt="Document photo"
            className="w-full h-40 object-cover rounded-md border"
          />
          <p className="text-xs text-gray-500 mt-1">Document Photo</p>
        </div>
        <div className="flex-1 text-center">
          <img
            src={livePhotoUrl}
            alt="Live capture"
            className="w-full h-40 object-cover rounded-md border"
          />
          <p className="text-xs text-gray-500 mt-1">Live Capture</p>
        </div>
      </div>

      {matchResult && (
        <div
          className={`text-center py-2 rounded-md font-semibold ${
            matchResult.match ? "bg-green-100 text-clear" : "bg-red-100 text-reject"
          }`}
        >
          {matchResult.match ? "✅ Face Match" : "⛔ Face Mismatch"} — {matchResult.score}% similarity
        </div>
      )}
    </div>
  );
}
