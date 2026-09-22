export default function FieldTable({
  fields = {},
}) {
  return (
    <div className="bg-white rounded-xl shadow p-6">

      <h2 className="text-xl font-bold text-slate-800 mb-5">
        Extracted Document Fields
      </h2>

      <div className="divide-y">

        {Object.entries(fields).map(
          ([key, value]) => (
            <div
              key={key}
              className="grid grid-cols-2 py-3"
            >

              <span className="font-medium text-gray-600">
                {key}
              </span>

              <span className="text-gray-900">
                {value || "—"}
              </span>

            </div>
          )
        )}

      </div>

    </div>
  );
}