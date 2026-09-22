const CASES_KEY = "cyberfoxxx_cases";

export function getCases() {
  try {
    return JSON.parse(localStorage.getItem(CASES_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveCases(cases) {
  localStorage.setItem(CASES_KEY, JSON.stringify(cases));
}

export function createCase(scanId, fileName) {
  const cases = getCases();

  const newCase = {
    id: scanId,
    fileName: fileName || "Unknown document",
    status: "PENDING",
    createdAt: new Date().toISOString(),
  };

  cases.push(newCase);
  saveCases(cases);

  return newCase;
}

export function updateCaseStatus(scanId, status) {
  const cases = getCases();

  const updatedCases = cases.map((item) =>
    item.id === scanId
      ? {
          ...item,
          status,
          updatedAt: new Date().toISOString(),
        }
      : item
  );

  saveCases(updatedCases);

  return updatedCases;
}

export function getCaseStats() {
  const cases = getCases();

  return {
    total: cases.length,

    pending: cases.filter(
      (item) => item.status === "PENDING"
    ).length,

    cleared: cases.filter(
      (item) => item.status === "CLEAR"
    ).length,

    review: cases.filter(
      (item) => item.status === "REVIEW"
    ).length,

    rejected: cases.filter(
      (item) => item.status === "REJECT"
    ).length,
  };
}