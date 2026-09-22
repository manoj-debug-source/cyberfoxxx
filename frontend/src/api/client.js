import axios from "axios";

/* =========================================================
   API CONFIGURATION
========================================================= */

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000/api";


/* =========================================================
   AXIOS CLIENT
========================================================= */

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});


/* =========================================================
   REQUEST INTERCEPTOR
   Attach JWT automatically
========================================================= */

client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);


/* =========================================================
   RESPONSE INTERCEPTOR
========================================================= */

client.interceptors.response.use(
  (response) => response,

  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("cyberfoxxx_user");

      window.location.href = "/login";
    }

    return Promise.reject(error);
  }
);


/* =========================================================
   AUTHENTICATION
========================================================= */

export async function loginUser(credentials) {
  if (!credentials) {
    throw new Error("Login credentials are required.");
  }

  const response = await client.post(
    "/auth/login",
    credentials
  );

  return response.data;
}


export async function getCurrentUser() {
  const response = await client.get(
    "/auth/me"
  );

  return response.data;
}


/* =========================================================
   DASHBOARD / STATISTICS
========================================================= */

export async function getScreeningStats() {
  const response = await client.get(
    "/screening/stats"
  );

  return response.data;
}


/* =========================================================
   SCREENING CREATION
========================================================= */

export async function scanDocument(file) {
  if (!file) {
    throw new Error("Document file is required.");
  }

  const formData = new FormData();

  formData.append("file", file);

  const response = await client.post(
    "/screening/upload",
    formData
  );

  return response.data;
}


/* =========================================================
   MASTER SCREENING PIPELINE
========================================================= */

export async function runScreeningPipeline(file) {
  if (!file) {
    throw new Error("Document file is required.");
  }

  const formData = new FormData();

  formData.append("file", file);

  const response = await client.post(
    "/pipeline/screen",
    formData
  );

  return response.data;
}


/* =========================================================
   SCREENING / SCAN
========================================================= */

export async function getScan(screeningId) {
  if (!screeningId) {
    throw new Error("Screening ID is required.");
  }

  const response = await client.get(
    `/screening/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


export async function getScreening(screeningId) {
  return getScan(screeningId);
}


export async function getScanStatus(screeningId) {
  return getScan(screeningId);
}


/* =========================================================
   DOCUMENT VALIDATION
========================================================= */

export async function validateDocument(screeningId) {
  if (!screeningId) {
    throw new Error("Screening ID is required.");
  }

  const response = await client.post(
    `/identity-validation/validate/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


/* =========================================================
   WATCHLIST / BLACKLIST
========================================================= */

/*
 * Run the actual watchlist screening.
 *
 * Backend:
 * POST /api/watchlist/check/{screening_id}
 *
 * This performs the comparison against:
 *
 * MongoDB
 *   ↓
 * watchlist_records
 *
 * Result:
 * MATCH
 * POTENTIAL_MATCH
 * NO_MATCH
 * PENDING
 */

export async function checkWatchlist(screeningId) {
  if (!screeningId) {
    throw new Error("Screening ID is required.");
  }

  const response = await client.post(
    `/watchlist/check/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


/*
 * Retrieve an already-performed watchlist result.
 *
 * Backend:
 * GET /api/watchlist/result/{screening_id}
 *
 * IMPORTANT:
 * This is GET, NOT POST.
 */

export async function getWatchlistResult(screeningId) {
  if (!screeningId) {
    throw new Error("Screening ID is required.");
  }

  const response = await client.get(
    `/watchlist/result/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


/* =========================================================
   TAMPER DETECTION
========================================================= */

export async function analyzeTamper(
  file,
  screeningId
) {
  if (!file) {
    throw new Error("Document file is required.");
  }

  if (!screeningId) {
    throw new Error("Screening ID is required.");
  }

  const formData = new FormData();

  formData.append("file", file);
  formData.append("screening_id", screeningId);

  const response = await client.post(
    "/tamper/analyze",
    formData
  );

  return response.data;
}


/* =========================================================
   ANOMALY DETECTION
========================================================= */

export async function analyzeAnomaly(
  file,
  screeningId
) {
  if (!file) {
    throw new Error(
      "Document file is required for anomaly analysis."
    );
  }

  if (!screeningId) {
    throw new Error(
      "Screening ID is required for anomaly analysis."
    );
  }

  const formData = new FormData();

  formData.append("file", file);
  formData.append("screening_id", screeningId);

  const response = await client.post(
    "/anomaly/analyze",
    formData
  );

  return response.data;
}


/* =========================================================
   FACE MATCHING
========================================================= */

export async function matchFace(formData) {
  if (!formData) {
    throw new Error(
      "Face matching data is required."
    );
  }

  const response = await client.post(
    "/face/match",
    formData
  );

  return response.data;
}


/* =========================================================
   IDENTITY LINKAGE
========================================================= */

export async function getIdentityLinkage(
  screeningId
) {
  if (!screeningId) {
    throw new Error("Screening ID is required.");
  }

  const response = await client.get(
    `/identity/linkage/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


export async function linkIdentityToLedger(
  data
) {
  if (!data) {
    throw new Error(
      "Identity data is required."
    );
  }

  if (!data.screening_id) {
    throw new Error(
      "Screening ID is required."
    );
  }

  if (!data.identity_data) {
    throw new Error(
      "Identity data is required."
    );
  }

  const response = await client.post(
    "/identity/link",
    data
  );

  return response.data;
}


/* =========================================================
   IDENTITY VALIDATION
========================================================= */

export async function validateIdentity(
  identityData
) {
  if (!identityData) {
    throw new Error(
      "Identity data is required."
    );
  }

  const response = await client.post(
    "/identity-validation/validate",
    identityData
  );

  return response.data;
}


/* =========================================================
   RISK
========================================================= */

export async function getRiskScore(
  screeningId
) {
  if (!screeningId) {
    throw new Error(
      "Screening ID is required."
    );
  }

  const response = await client.get(
    `/risk/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


export async function calibrateRiskFromScreening(
  screeningId
) {
  if (!screeningId) {
    throw new Error(
      "Screening ID is required for risk calibration."
    );
  }

  const response = await client.post(
    `/risk/calibrate-from-screening/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


/* =========================================================
   OFFICER DECISION
========================================================= */

export async function submitOfficerDecision(
  screeningId,
  decision,
  notes = ""
) {
  if (!screeningId) {
    throw new Error(
      "Screening ID is required."
    );
  }

  if (!decision) {
    throw new Error(
      "Officer decision is required."
    );
  }

  const response = await client.post(
    `/screening/${encodeURIComponent(screeningId)}/decision`,
    {
      decision,
      notes,
    }
  );

  return response.data;
}


export async function submitScreeningDecision(
  screeningId,
  data
) {
  if (!screeningId) {
    throw new Error(
      "Screening ID is required."
    );
  }

  if (!data?.decision) {
    throw new Error(
      "Officer decision is required."
    );
  }

  const response = await client.post(
    `/screening/${encodeURIComponent(screeningId)}/decision`,
    data
  );

  return response.data;
}


/* =========================================================
   BLOCKCHAIN
========================================================= */

export async function createBlockchainRecord(
  data
) {
  if (!data) {
    throw new Error(
      "Blockchain data is required."
    );
  }

  const response = await client.post(
    "/blockchain/create",
    data
  );

  return response.data;
}


export async function getBlockchainRecord(
  screeningId
) {
  if (!screeningId) {
    throw new Error(
      "Screening ID is required."
    );
  }

  const response = await client.get(
    `/blockchain/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


/* =========================================================
   AUDIT
========================================================= */

export async function createAuditLog(
  data
) {
  if (!data) {
    throw new Error(
      "Audit data is required."
    );
  }

  const response = await client.post(
    "/audit/create",
    data
  );

  return response.data;
}


export async function getAuditLogs() {
  const response = await client.get(
    "/audit/logs"
  );

  return response.data;
}


/* =========================================================
   SCREENING RECORD
========================================================= */

export async function createScreening(
  data
) {
  if (!data) {
    throw new Error(
      "Screening data is required."
    );
  }

  const response = await client.post(
    "/screening/create",
    data
  );

  return response.data;
}


/* =========================================================
   PIPELINE
========================================================= */

export async function getPipeline(
  screeningId
) {
  if (!screeningId) {
    throw new Error(
      "Screening ID is required."
    );
  }

  const response = await client.get(
    `/pipeline/${encodeURIComponent(screeningId)}`
  );

  return response.data;
}


/* =========================================================
   BLOCKCHAIN LEDGER
========================================================= */

export async function verifyChain() {
  const response = await client.get(
    "/blockchain/verify"
  );

  return response.data;
}


export async function getLedgerEvents() {
  const response = await client.get(
    "/blockchain/ledger"
  );

  return response.data;
}


/* =========================================================
   DEFAULT EXPORT
========================================================= */

export default client;