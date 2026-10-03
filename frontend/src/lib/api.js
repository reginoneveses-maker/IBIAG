import { api } from "@/AuthContext";
export { api, API } from "@/AuthContext";

export const STAGES = ["new_lead", "qualified", "initial_contact", "negotiation", "sample_quote", "closed_won", "closed_lost"];
export const INDUSTRIES = ["beverage", "cosmetics", "food_service", "distributor"];
export const CATEGORIES = ["acai", "acerola", "juices", "coconut", "nuts"];

export const stageColor = (s) => ({
  new_lead: "bg-blue-100 text-blue-800 border-blue-200",
  qualified: "bg-cyan-100 text-cyan-800 border-cyan-200",
  initial_contact: "bg-purple-100 text-purple-800 border-purple-200",
  sample_quote: "bg-amber-100 text-amber-800 border-amber-200",
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
export const fmtBRL = (v) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 }).format(v || 0);

// URLs from discovery are external data; only HTTP(S) links are rendered.
export const externalUrl = (value) => {
  try { const url = new URL(value); return ["http:", "https:"].includes(url.protocol) ? url.href : ""; }
  catch { return ""; }
};

export const downloadDocument = async (doc) => {
  const r = await api.get("/files/" + doc.file_path, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url; a.download = doc.file_name || "documento";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

// Only recognized PDF/raster signatures are displayed. Other formats use download.
export const previewMime = (bytes) => {
  const starts = (...values) => values.every((value,index) => bytes[index] === value);
  if (starts(37,80,68,70,45)) return "application/pdf";
  if (starts(137,80,78,71,13,10,26,10)) return "image/png";
  if (starts(255,216,255)) return "image/jpeg";
  if (starts(71,73,70,56) && [55,57].includes(bytes[4]) && bytes[5]===97) return "image/gif";
  if (starts(82,73,70,70) && bytes[8]===87 && bytes[9]===69 && bytes[10]===66 && bytes[11]===80) return "image/webp";
  return "";
};
export const documentPreview = async (blob) => {
  const buffer = await new Promise((resolve,reject) => {const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(new Error("Não foi possível ler o arquivo."));reader.readAsArrayBuffer(blob.slice(0,512));});
  const mime=previewMime(new Uint8Array(buffer));
  if(!mime)return {kind:"unsupported",url:""};
  return {kind:mime==="application/pdf"?"pdf":"image",url:URL.createObjectURL(new Blob([blob],{type:mime}))};
};
