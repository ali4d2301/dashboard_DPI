const BAILLEUR_PALETTE = [
  { keys: ["non couvert"], color: "#64748b" },
  { keys: ["ucps bm", "ucps"], color: "#8e44ad" },
  { keys: ["padci"], color: "#f59e0b" },
  { keys: ["prtds", "ptdrs"], color: "#1d4ed8" },
  { keys: ["fonds"], color: "#0b3b78" },
  { keys: ["unicef"], color: "#0b86e8" },
  { keys: ["gavi"], color: "#28a745" },
  { keys: ["usaid"], color: "#44546a" },
  { keys: ["bm"], color: "#2563eb" },
];

function normalizeBailleur(value = "") {
  return String(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function bailleurColor(value) {
  const normalized = normalizeBailleur(value);
  const match = BAILLEUR_PALETTE.find((item) => item.keys.some((key) => normalized.includes(key)));
  return match?.color || "#1f5d99";
}
