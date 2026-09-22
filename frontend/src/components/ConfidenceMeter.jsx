export default function ConfidenceMeter({
  score = 0,
  low = 0,
  high = 100,
}) {
  return (
    <div className="bg-white rounded-xl shadow p-6">

      <h2 className="text-xl font-bold text-slate-800">
        Calibrated Risk Range
      </h2>

      <p className="text-sm text-gray-500 mt-1">
        Risk estimate with uncertainty range
      </p>

      <div className="relative h-5 bg-gray-200 rounded-full mt-6">

        <div
          className="absolute h-full bg-slate-300 rounded-full"
          style={{
            left: `${low}%`,
            width: `${Math.max(high - low, 0)}%`,
          }}
        />

        <div
          className="absolute top-[-4px] w-1 h-7 bg-slate-900"
          style={{
            left: `${score}%`,
          }}
        />

      </div>

      <div className="flex justify-between text-xs text-gray-500 mt-2">
        <span>{low}%</span>
        <span>{high}%</span>
      </div>

      <p className="mt-4 text-sm font-medium">
        Estimated risk: {score}%
      </p>

    </div>
  );
}