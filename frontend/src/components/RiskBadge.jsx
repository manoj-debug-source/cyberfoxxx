export default function RiskBadge({
  decision,
  score,
}) {
  const config = {
    CLEAR: {
      label: "CLEAR",
      icon: "✓",
      classes:
        "bg-green-50 text-green-700 border-green-300",
    },

    REVIEW: {
      label: "REVIEW REQUIRED",
      icon: "!",
      classes:
        "bg-amber-50 text-amber-700 border-amber-300",
    },

    REJECT: {
      label: "HIGH RISK",
      icon: "×",
      classes:
        "bg-red-50 text-red-700 border-red-300",
    },
  };

  const current =
    config[decision] || config.REVIEW;

  return (
    <div
      className={`border rounded-xl p-5 ${current.classes}`}
    >

      <div className="flex items-center gap-3">

        <div className="text-2xl font-bold">
          {current.icon}
        </div>

        <div>

          <p className="font-bold text-lg">
            {current.label}
          </p>

          {score !== undefined && (
            <p className="text-sm">
              Risk Score: {score}/100
            </p>
          )}

        </div>

      </div>

    </div>
  );
}