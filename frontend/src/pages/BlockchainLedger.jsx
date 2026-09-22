import { useEffect, useState } from "react";

import {
  verifyChain,
  getLedgerEvents,
} from "../api/client";

import ChainStatusBadge from "../components/ChainStatusBadge";

export default function BlockchainLedger() {

  const [chainStatus, setChainStatus] =
    useState(null);

  const [events, setEvents] =
    useState([]);

  const [loading, setLoading] =
    useState(true);

  async function refresh() {

    try {

      setLoading(true);

      const [status, eventList] =
        await Promise.all([
          verifyChain(),
          getLedgerEvents(),
        ]);

      setChainStatus(status);
      setEvents(eventList);

    } catch (error) {

      console.error(error);

    } finally {

      setLoading(false);

    }

  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6">

      <div className="flex justify-between items-center mb-6">

        <div>
          <h1 className="text-3xl font-bold text-slate-800">
            Blockchain Audit Ledger
          </h1>

          <p className="text-gray-500 mt-1">
            Integrity verification and audit events
          </p>
        </div>

        <button
          onClick={refresh}
          className="border px-4 py-2 rounded-lg"
        >
          Re-verify
          
        </button>

      </div>

      {!loading && chainStatus && (
        <ChainStatusBadge
          status={chainStatus}
        />
      )}

      <div className="bg-white rounded-xl shadow mt-6 divide-y">

        {events.map((event, index) => (

          <div
            key={index}
            className="p-5 flex justify-between"
          >

            <div>

              <p className="font-semibold">
                {event.event_type}
              </p>

              <p className="text-xs text-gray-500">
                Screening ID: {event.screening_id}
              </p>

            </div>

            <div className="text-right">

              <p className="font-mono text-xs">
                {event.event_hash?.slice(0, 18)}...
              </p>

              <p className="text-xs text-gray-400">
                {event.timestamp
                  ? new Date(
                      event.timestamp
                    ).toLocaleString()
                  : ""}
              </p>

            </div>

          </div>

        ))}

      </div>

    </div>
  );
}