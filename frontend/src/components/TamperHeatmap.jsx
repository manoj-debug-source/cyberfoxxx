export default function TamperHeatmap({
  tamperScore,
  tamperFlags,
  elaImageUrl,
  tamperAnalysis,
}) {
  /*
   * CYBERFOXXX Tamper Detection
   *
   * Supports the actual backend response:
   *
   * {
   *   prediction: "tampered",
   *   tamper_probability: 0.5192,
   *   genuine_probability: 0.4808,
   *   threshold: 0.5,
   *   raw_model_output: 0.5192
   * }
   */

  // --------------------------------------------------
  // Get tamper probability
  // --------------------------------------------------

  const backendTamperProbability =
    tamperAnalysis?.tamper_probability ??
    tamperAnalysis?.probability ??
    tamperAnalysis?.tampered_probability ??
    null;

  // Convert probability 0.5192 -> 51.92
  const calculatedTamperScore =
    backendTamperProbability !== null
      ? backendTamperProbability * 100
      : tamperScore ?? 0;

  const score = Number(calculatedTamperScore);

  // --------------------------------------------------
  // Prediction
  // --------------------------------------------------

  const prediction = String(
    tamperAnalysis?.prediction ?? ""
  )
    .toLowerCase()
    .trim();

  const isTampered = prediction === "tampered";

  const isHighRisk = isTampered || score >= 50;

  // --------------------------------------------------
  // Genuine probability
  // --------------------------------------------------

  const genuineProbability =
    tamperAnalysis?.genuine_probability;

  const genuineScore =
    genuineProbability !== undefined &&
    genuineProbability !== null
      ? Number(genuineProbability) * 100
      : null;

  // --------------------------------------------------
  // Threshold
  // --------------------------------------------------

  const threshold =
    tamperAnalysis?.threshold !== undefined
      ? Number(tamperAnalysis.threshold) * 100
      : 50;

  // --------------------------------------------------
  // Generate indicators from actual backend result
  // --------------------------------------------------

  const indicators = Array.isArray(tamperFlags)
    ? tamperFlags
    : [];

  if (isTampered && indicators.length === 0) {
    indicators.push(
      "Tampering model classified the document as tampered"
    );
  }

  if (score >= threshold && !indicators.includes(
    "Tampering probability exceeds the detection threshold"
  )) {
    indicators.push(
      "Tampering probability exceeds the detection threshold"
    );
  }

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div className="bg-white rounded-lg shadow p-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">

        <h3 className="font-semibold text-brand">
          Tampering Analysis
        </h3>

        <span
          className={`text-sm font-bold px-3 py-1 rounded-full ${
            isHighRisk
              ? "bg-red-100 text-reject"
              : "bg-green-100 text-clear"
          }`}
        >
          {score.toFixed(2)}/100 suspicion
        </span>

      </div>

      {/* Prediction */}
      <div
        className={`rounded-lg border p-3 mb-4 ${
          isTampered
            ? "bg-red-50 border-red-200"
            : "bg-green-50 border-green-200"
        }`}
      >

        <div className="flex items-center justify-between">

          <span className="text-sm font-medium text-gray-700">
            Model Prediction
          </span>

          <span
            className={`font-bold ${
              isTampered
                ? "text-reject"
                : "text-clear"
            }`}
          >
            {prediction
              ? prediction.toUpperCase()
              : "NOT AVAILABLE"}
          </span>

        </div>

      </div>

      {/* Probability details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">

        {/* Tamper probability */}
        <div className="bg-gray-50 rounded-lg p-3">

          <p className="text-xs text-gray-500">
            Tamper Probability
          </p>

          <p
            className={`text-xl font-bold ${
              score >= 50
                ? "text-reject"
                : "text-gray-700"
            }`}
          >
            {score.toFixed(2)}%
          </p>

        </div>

        {/* Genuine probability */}
        <div className="bg-gray-50 rounded-lg p-3">

          <p className="text-xs text-gray-500">
            Genuine Probability
          </p>

          <p className="text-xl font-bold text-clear">
            {genuineScore !== null
              ? `${genuineScore.toFixed(2)}%`
              : "—"}
          </p>

        </div>

      </div>

      {/* Probability bar */}
      <div className="mb-4">

        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Genuine</span>
          <span>Tampered</span>
        </div>

        <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">

          <div
            className={`h-full ${
              isTampered
                ? "bg-reject"
                : "bg-clear"
            }`}
            style={{
              width: `${Math.min(
                Math.max(score, 0),
                100
              )}%`,
            }}
          />

        </div>

      </div>

      {/* Detection threshold */}
      <div className="text-xs text-gray-500 mb-4">
        Detection threshold:{" "}
        <span className="font-semibold">
          {threshold.toFixed(2)}%
        </span>
      </div>

      {/* ELA image */}
      {elaImageUrl && (
        <div className="mb-4">

          <p className="text-sm font-medium text-gray-700 mb-2">
            Error Level Analysis
          </p>

          <img
            src={elaImageUrl}
            alt="Error Level Analysis heatmap"
            className="w-full rounded-md border"
          />

        </div>
      )}

      {/* Tampering indicators */}
      <div>

        <p className="text-sm font-semibold text-gray-700 mb-2">
          Tampering Indicators
        </p>

        {indicators.length > 0 ? (

          <ul className="text-sm space-y-2">

            {indicators.map((flag, i) => (

              <li
                key={i}
                className="flex items-start gap-2 text-reject"
              >

                <span>⚠️</span>

                <span>
                  {String(flag).replaceAll("_", " ")}
                </span>

              </li>

            ))}

          </ul>

        ) : (

          <p className="text-sm text-gray-500">
            No tampering indicators found.
          </p>

        )}

      </div>

    </div>
  );
}