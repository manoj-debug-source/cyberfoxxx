export default function EnsembleAgreementCard({
  cnnScore,
  autoencoderScore,
  agree,
}) {
  return (
    <div
      className={`rounded-xl border-2 p-6 ${
        agree
          ? "border-green-400 bg-green-50"
          : "border-amber-400 bg-amber-50"
      }`}
    >

      <h2 className="text-xl font-bold text-slate-800 mb-5">
        Dual-Model Tamper Detection
      </h2>

      <div className="grid grid-cols-2 gap-5 text-center">

        <div className="bg-white rounded-lg p-4">

          <p className="text-3xl font-bold">
            {Math.round(cnnScore || 0)}%
          </p>

          <p className="text-sm text-gray-500">
            Supervised CNN
          </p>

        </div>

        <div className="bg-white rounded-lg p-4">

          <p className="text-3xl font-bold">
            {Math.round(autoencoderScore || 0)}%
          </p>

          <p className="text-sm text-gray-500">
            Autoencoder Anomaly
          </p>

        </div>

      </div>

      <div className="mt-5 text-center font-semibold">

        {agree ? (
          <p className="text-green-700">
            ✓ Both models agree
          </p>
        ) : (
          <p className="text-amber-700">
            ! Models disagree — manual review recommended
          </p>
        )}

      </div>

    </div>
  );
}