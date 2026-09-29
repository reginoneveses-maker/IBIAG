import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

export const STAGES = ["new_lead", "initial_contact", "sample_sent", "negotiation", "closed_won", "closed_lost"];
export const INDUSTRIES = ["beverage", "cosmetics", "food_service", "distributor"];
export const CATEGORIES = ["acai", "acerola", "juices", "coconut", "nuts"];

export const stageColor = (s) => ({
  new_lead: "bg-blue-100 text-blue-800 border-blue-200",
  initial_contact: "bg-purple-100 text-purple-800 border-purple-200",
  sample_sent: "bg-amber-100 text-amber-800 border-amber-200",
  negotiation: "bg-emerald-100 text-emerald-800 border-emerald-200",
  closed_won: "bg-green-200 text-green-900 border-green-300",
  closed_lost: "bg-rose-100 text-rose-800 border-rose-200",
}[s] || "bg-slate-100 text-slate-700");

export const flag = (code) => {
  if (!code || code.length !== 2) return "🌍";
  const A = 127397;
  return String.fromCodePoint(...code.toUpperCase().split("").map(c => c.charCodeAt(0) + A));
};

export const fmtUSD = (v) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(v || 0);
