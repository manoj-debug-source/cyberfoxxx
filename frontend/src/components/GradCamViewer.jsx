export default function GradCamViewer({
  originalUrl,
  gradcamUrl,
  cnnScore,
}) {
  return (
    <div className="bg-white rounded-xl shadow p-6">

      <div className="flex justify-between items-center mb-5">

        <h2 className="text-xl font-bold text-slate-800">
          CNN Attention — Grad-CAM
        </h2>

        <span className="bg-gray-100 px-3 py-2 rounded-lg text-sm font-semibold">
          {Math.round(cnnScore || 0)}% tamper probability
        </span>

      </div>

      <div className="grid md:grid-cols-2 gap-5">

        <div>

          <img
            src={originalUrl}
            alt="Original document"
            className="w-full rounded-lg border"
          />

          <p className="text-sm text-gray-500 text-center mt-2">
            Original Document
          </p>

        </div>

        <div>

          <img
            src={gradcamUrl}
            alt="Grad-CAM"
            className="w-full rounded-lg border"
          />

          <p className="text-sm text-gray-500 text-center mt-2">
            CNN Attention
          </p>

        </div>

      </div>

      <p className="text-xs text-gray-500 mt-4">
        The highlighted regions indicate areas that
        influenced the CNN's tampering prediction.
      </p>

    </div>
  );
}