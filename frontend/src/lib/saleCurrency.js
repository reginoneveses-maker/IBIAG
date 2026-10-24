import {priceMoney} from "./pricing";
export const saleCurrency = record => record.currency || "USD";
export const saleAmount = record => saleCurrency(record) === "USD" ? record.total_usd : record.total_amount;
export const saleValid = record => ["USD","BRL","EUR"].includes(saleCurrency(record)) && typeof saleAmount(record) === "number" && Number.isFinite(saleAmount(record)) && saleAmount(record) >= 0;
export const saleMoney = record => saleValid(record) ? priceMoney(saleAmount(record), saleCurrency(record)) : "Valor pendente de revisão";
export function saleTotals(records) {
 const cents = new Map();
 for (const record of records) {
  const currency = saleCurrency(record), amount = saleAmount(record);
  if (!["USD","BRL","EUR"].includes(currency) || typeof amount !== "number" || !Number.isFinite(amount) || amount < 0) continue;
  cents.set(currency,(cents.get(currency)||0)+Math.round(amount*100));
 }
 return [...cents].sort(([a],[b])=>a.localeCompare(b)).map(([currency,total])=>({currency,total:total/100}));
}
