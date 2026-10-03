import credits from "@/assets/product-photos/credits.json";
import acai from "@/assets/product-photos/acai.jpg";
import acerola from "@/assets/product-photos/acerola.jpg";
import coconut from "@/assets/product-photos/coconut.jpg";
import cashew from "@/assets/product-photos/cashew.jpg";
import brazilNut from "@/assets/product-photos/brazil-nut.jpg";
import guaranaPowder from "@/assets/product-photos/guarana-powder.jpg";
import pineapple from "@/assets/product-photos/pineapple.jpg";
import orange from "@/assets/product-photos/orange.jpg";
import passionFruit from "@/assets/product-photos/passion-fruit.jpg";
import guava from "@/assets/product-photos/guava.jpg";
import lime from "@/assets/product-photos/lime.jpg";
import banana from "@/assets/product-photos/banana.jpg";
import cupuacu from "@/assets/product-photos/cupuacu.jpg";
import mango from "@/assets/product-photos/mango.jpg";
import lemon from "@/assets/product-photos/lemon.jpg";

const sources = {acai, acerola, coconut, cashew, "brazil-nut": brazilNut,
  "guarana-powder": guaranaPowder, pineapple, orange, "passion-fruit": passionFruit,
  guava, lime, banana, cupuacu, mango, lemon};
const names = {
  acai: ["Açaí", "Açaí"], acerola: ["Acerola", "Acerola"], coconut: ["Coco", "Coconut"],
  cashew: ["Castanha de caju", "Cashew nuts"], "brazil-nut": ["Castanha-do-pará", "Brazil nuts"],
  "guarana-powder": ["Guaraná em pó", "Guarana powder"], pineapple: ["Abacaxi", "Pineapple"],
  orange: ["Laranja", "Orange"], "passion-fruit": ["Maracujá", "Passion fruit"],
  guava: ["Goiaba", "Guava"], lime: ["Limão", "Lime"], banana: ["Banana", "Banana"],
  cupuacu: ["Cupuaçu", "Cupuacu"],
  mango: ["Manga", "Mango"], lemon: ["Limão-siciliano", "Lemon"],
};
const rules = [
  ["acai", /\bacai\b/], ["acerola", /\bacerola\b/],
  ["coconut", /\b(?:coco|coconut)\b/],
  ["cashew", /\b(?:castanha (?:de )?caju|cashew)\b/],
  ["brazil-nut", /\b(?:castanha (?:do |de )?(?:para|brasil)|brazil nuts?)\b/],
  ["guarana-powder", /\bguarana\b.*\b(?:po|powder|ground)\b/],
  ["pineapple", /\b(?:abacaxi|pineapple)\b/], ["orange", /\b(?:laranja|orange)\b/],
  ["passion-fruit", /\b(?:maracuja|passion fruit)\b/], ["guava", /\b(?:goiaba|guava)\b/],
  ["lime", /\b(?:limao tahiti|lime)\b/], ["banana", /\bbanana\b/],
  ["cupuacu", /\b(?:cupuacu|cupuassu)\b/],
  ["mango", /\b(?:manga|mango)\b/], ["lemon", /\b(?:limao siciliano|lemon)\b/],
];
const normalize = value => String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "")
  .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

// Match the product name, never a broad category or a mention in its description.
// Blends and unrecognized products must not inherit a photograph of another ingredient.
export function productPhoto(product) {
  const text = normalize(product.name);
  const matches = rules.filter(([,pattern]) => pattern.test(text));
  if (matches.length !== 1) return null;
  const key = matches[0][0];
  return {...credits.find(c => c.key === key), src: sources[key], names: names[key]};
}

export function catalogImageUrl(value) {
  const url = String(value || "").trim();
  if (url.startsWith("/") && !url.startsWith("//")) return url;
  try { const parsed = new URL(url); return parsed.protocol === "https:" ? parsed.href : ""; }
  catch { return ""; }
}
