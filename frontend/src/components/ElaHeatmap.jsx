export default function ElaHeatmap({
  originalUrl,
  elaUrl,
}) {
  return (
    <div className="bg-white rounded-xl shadow p-6">

      <h2 className="text-xl font-bold text-slate-800 mb-5">
        Error Level Analysis
      </h2>

      <div className="grid md:grid-cols-2 gap-5">

        <div>
          <img
            src={originalUrl}
            alt="Original document"
            className="w-full rounded-lg border"
          />

          <p className="text-sm text-gray-500 text-center mt-2">
            Original
          </p>
        </div>

        <div>
          <img
            src={elaUrl}
            alt="ELA heatmap"
            className="w-full rounded-lg border"
          />

          <p className="text-sm text-gray-500 text-center mt-2">
            ELA Heatmap
          </p>
        </div>

      </div>

    </div>
  );
}