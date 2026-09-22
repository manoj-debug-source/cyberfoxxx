const STATUS_STYLES = {
  clear: "bg-green-100 text-clear border-clear",
  flagged: "bg-red-100 text-reject border-reject",
  warning: "bg-amber-100 text-review border-review",
  pending: "bg-gray-100 text-gray-400 border-gray-300",
  skipped: "bg-gray-100 text-gray-400 border-gray-300",
};

const STATUS_LABELS = {
  clear: "Clear",
  flagged: "Flagged",
  warning: "Review",
  pending: "Pending",
  skipped: "Skipped",
};

export default function PipelineStageCard({
  index,
  icon,
  title,
  subtitle,
  status = "pending",
  metric,
  details = [],
  isLast = false,
}) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.pending;

  return (
    <div className="flex gap-4">
      {/* Step marker + connecting line */}
      <div className="flex flex-col items-center">
        <div
          className={`w-10 h-10 shrink-0 rounded-full border-2 flex items-center justify-center text-lg font-bold ${style}`}
        >
          {icon || index}
        </div>
        {!isLast && <div className="w-0.5 flex-1 bg-gray-200 my-1" />}
      </div>

      {/* Card body */}
      <div className="bg-white rounded-lg shadow p-4 flex-1 mb-6">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div>
            <h3 className="font-semibold text-brand">{title}</h3>
            {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
          </div>
          <span
            className={`shrink-0 text-xs font-bold px-2 py-1 rounded-full border ${style}`}
          >
            {STATUS_LABELS[status] || status}
          </span>
        </div>

        {metric && (
          <p className="text-sm text-gray-700 mt-2 font-medium">{metric}</p>
        )}

        {details.length > 0 && (
          <ul className="mt-2 space-y-1">
            {details.map((d, i) => (
              <li key={i} className="text-xs text-gray-500 flex items-center gap-2">
                <span>{d.flag ? "⚠️" : "•"}</span>
                <span className={d.flag ? "text-reject" : ""}>{d.text}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}