import { Routes, Route, Navigate } from "react-router-dom";

import BlockchainLedger from "./pages/BlockchainLedger";
import IdentityLinkage from "./pages/IdentityLinkage";
import Login from "./pages/Login";
import OfficerDashboard from "./pages/OfficerDashboard";
import AdminDashboard from "./pages/AdminDashboard";
import ScanUpload from "./pages/ScanUpload";
import Processing from "./pages/Processing";
import Results from "./pages/Results";
import RiskAssessment from "./pages/RiskAssessment";
import OfficerReview from "./pages/OfficerReview";
import AuditLog from "./pages/AuditLog";
import CaseIntelligence from "./pages/CaseIntelligence";


/* =========================================================
   PROTECTED ROUTE
========================================================= */

function ProtectedRoute({ children, role }) {

  const token = localStorage.getItem("access_token");
  const storedUser = localStorage.getItem("cyberfoxxx_user");

  /* -------------------------------------------------------
     Not logged in
  ------------------------------------------------------- */

  if (!token || !storedUser) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  /* -------------------------------------------------------
     Safely read logged-in user
  ------------------------------------------------------- */

  let user;

  try {
    user = JSON.parse(storedUser);
  } catch (error) {

    console.error(
      "Invalid cyberfoxxx_user in localStorage:",
      error
    );

    localStorage.removeItem("cyberfoxxx_user");
    localStorage.removeItem("access_token");

    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  /* -------------------------------------------------------
     User object missing
  ------------------------------------------------------- */

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  /* -------------------------------------------------------
     Role validation
  ------------------------------------------------------- */

  if (
    role &&
    String(user.role || "").toLowerCase() !==
      String(role).toLowerCase()
  ) {

    console.warn(
      `Access denied. Required role: ${role}, actual role: ${user.role}`
    );

    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  return children;
}


/* =========================================================
   APP
========================================================= */

export default function App() {

  return (

    <Routes>

      {/* ===================================================
          LOGIN
      =================================================== */}

      <Route
        path="/login"
        element={
          <Login />
        }
      />


      {/* ===================================================
          OFFICER DASHBOARD
      =================================================== */}

      <Route
        path="/officer"
        element={
          <ProtectedRoute role="officer">
            <OfficerDashboard />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          DOCUMENT UPLOAD
      =================================================== */}

      <Route
        path="/screen"
        element={
          <ProtectedRoute role="officer">
            <ScanUpload />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          PROCESSING
      =================================================== */}

      <Route
        path="/processing/:scanId"
        element={
          <ProtectedRoute role="officer">
            <Processing />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          SCREENING RESULTS
      =================================================== */}

      <Route
        path="/results/:scanId"
        element={
          <ProtectedRoute role="officer">
            <Results />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          RISK ASSESSMENT
      =================================================== */}

      <Route
        path="/risk-assessment/:scanId"
        element={
          <ProtectedRoute role="officer">
            <RiskAssessment />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          OFFICER REVIEW
      =================================================== */}

      <Route
        path="/review/:scanId"
        element={
          <ProtectedRoute role="officer">
            <OfficerReview />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          IDENTITY LINKAGE
      =================================================== */}

      <Route
        path="/identity-linkage/:scanId"
        element={
          <ProtectedRoute role="officer">
            <IdentityLinkage />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          AUDIT LOG
      =================================================== */}

      <Route
        path="/audit"
        element={
          <ProtectedRoute>
            <AuditLog />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          BLOCKCHAIN LEDGER
      =================================================== */}

      <Route
        path="/blockchain"
        element={
          <ProtectedRoute>
            <BlockchainLedger />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          ADMIN DASHBOARD
      =================================================== */}

      <Route
        path="/admin"
        element={
          <ProtectedRoute role="admin">
            <AdminDashboard />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          ADMIN CASE INTELLIGENCE
          
          Admin enters:
          
          SCR-XXXXXXXX

          and is redirected here.
      =================================================== */}

      <Route
        path="/admin/case/:screeningId"
        element={
          <ProtectedRoute role="admin">
            <CaseIntelligence />
          </ProtectedRoute>
        }
      />


      {/* ===================================================
          DEFAULT ROUTE
      =================================================== */}

      <Route
        path="/"
        element={
          <Navigate
            to="/login"
            replace
          />
        }
      />


      {/* ===================================================
          UNKNOWN ROUTE
      =================================================== */}

      <Route
        path="*"
        element={
          <Navigate
            to="/login"
            replace
          />
        }
      />

    </Routes>

  );
}