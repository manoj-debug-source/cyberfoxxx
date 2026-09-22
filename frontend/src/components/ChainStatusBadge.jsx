export default function ChainStatusBadge({
  status,
}) {
  if (!status) return null;

  if (status.valid) {
    return (
      <div className="bg-blue-50 border-2 border-blue-400
      rounded-xl p-6 text-center">

        <p className="text-2xl font-bold text-blue-600">
          Chain Verified
        </p>

        <p className="text-sm text-gray-500 mt-2">
          {status.chain_length} events verified.
          No integrity failure detected.
        </p>

      </div>
    );
  }

  return (
    <div className="bg-red-50 border-2 border-red-700
    rounded-xl p-6 text-center">

      <p className="text-2xl font-bold text-red-700">
        Chain Integrity Broken
      </p>

      <p className="text-sm text-gray-600 mt-2">
        Tampering detected at event #
        {status.broken_at_index}
      </p>

      <p className="text-sm text-gray-600">
        {status.reason}
      </p>

    </div>
  );
}