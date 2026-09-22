import { create } from "zustand";

export const useScreeningStore = create((set) => ({
  /* =====================================================
     CURRENT SCREENING
  ===================================================== */

  currentScan: null,

  /* =====================================================
     ORIGINAL UPLOADED DOCUMENT
  ===================================================== */

  currentFile: null,

  /* =====================================================
     RISK RESULT
  ===================================================== */

  riskResult: null,

  /* =====================================================
     IDENTITY LINKAGE
  ===================================================== */

  identityLinkage: null,

  /* =====================================================
     SET SCREENING
  ===================================================== */

  setScan: (scan) =>
    set({
      currentScan: scan,
    }),

  /* =====================================================
     SET ORIGINAL FILE
  ===================================================== */

  setFile: (file) =>
    set({
      currentFile: file,
    }),

  /* =====================================================
     SET RISK RESULT
  ===================================================== */

  setRiskResult: (risk) =>
    set({
      riskResult: risk,
    }),

  /* =====================================================
     SET IDENTITY LINKAGE
  ===================================================== */

  setIdentityLinkage: (linkage) =>
    set({
      identityLinkage: linkage,
    }),

  /* =====================================================
     RESET SCREENING
  ===================================================== */

  reset: () =>
    set({
      currentScan: null,
      currentFile: null,
      riskResult: null,
      identityLinkage: null,
    }),
}));