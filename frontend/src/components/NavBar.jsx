import { Link } from "react-router-dom";

export default function NavBar() {
  return (
    <nav className="bg-slate-900 text-white shadow">
      <div className="max-w-7xl mx-auto px-6 py-4">

        <div className="flex items-center justify-between">

         <Link
  to="/scan"
  className="text-xl font-bold"
>
  CYBERFOXXX
</Link>

          <div className="flex gap-6 text-sm">

            <Link
              to="/scan"
              className="hover:text-blue-300"
            >
              Scan
            </Link>

            <Link
              to="/audit"
              className="hover:text-blue-300"
            >
              Audit Logs
            </Link>

            <Link
              to="/ledger"
              className="hover:text-blue-300"
            >
              Blockchain
            </Link>

          </div>

        </div>

      </div>
    </nav>
  );
}