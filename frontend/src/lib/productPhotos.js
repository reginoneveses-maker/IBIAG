import credits from "@/assets/product-photos/credits.json";
import formCredits from "@/assets/product-photos/form-credits.json";
import acaiExtract from "@/assets/product-photos/acai-extract.jpg";
import acaiFreezeDried from "@/assets/product-photos/acai-freeze-dried.jpg";
import acaiPulp from "@/assets/product-photos/acai-pulp.jpg";
import acerolaPowder from "@/assets/product-photos/acerola-powder.jpg";
import camuCamuExtract from "@/assets/product-photos/camu-camu-extract.jpg";
import guaranaSeeds from "@/assets/product-photos/guarana-seeds.jpg";
import cashew from "@/assets/product-photos/cashew.jpg";
import brazilNut from "@/assets/product-photos/brazil-nut.jpg";
import guaranaPowder from "@/assets/product-photos/guarana-powder.jpg";
import muirapuamaPowder from "@/assets/product-photos/muirapuama-powder.jpg";
import moringaPowder from "@/assets/product-photos/moringa-powder.jpg";
import pauDarcoPowder from "@/assets/product-photos/pau-darco-powder.jpg";
import catuabaPowder from "@/assets/product-photos/catuaba-powder.jpg";
import pauDarcoCut from "@/assets/product-photos/pau-darco-cut.jpg";
import {ingredientKeys, productForm} from "./catalogIngredients";

const photographs = {
  "acai:extract-powder": ["acai-extract", acaiExtract],
  "acai:freeze-dried": ["acai-freeze-dried", acaiFreezeDried],
  "acai:pulp": ["acai-pulp", acaiPulp],
  "acerola:powder": ["acerola-powder", acerolaPowder],
  "camu-camu:extract-powder": ["camu-camu-extract", camuCamuExtract],
  "guarana:seeds": ["guarana-seeds", guaranaSeeds],
  "guarana:powder": ["guarana-powder", guaranaPowder],
  "cashew:nuts": ["cashew", cashew],
  "brazil-nut:nuts": ["brazil-nut", brazilNut],
  "muirapuama:powder": ["muirapuama-powder", muirapuamaPowder],
  "moringa:powder": ["moringa-powder", moringaPowder],
  "pau-darco:powder": ["pau-darco-powder", pauDarcoPowder],
  "catuaba:powder": ["catuaba-powder", catuabaPowder],
  "pau-darco:cut": ["pau-darco-cut", pauDarcoCut],
};
const nutNames = {
  cashew: ["Castanha de caju", "Cashew nuts"],
  "brazil-nut": ["Castanha-do-pará", "Brazil nuts"],
  "guarana-powder": ["Guaraná em pó", "Guarana powder"],
};

// A photograph must match both ingredient AND sold form. Fruit pictures,
// generic category defaults and photographs of another process are not fallbacks.
export function productPhoto(product) {
  const ingredients = ingredientKeys(product);
  if (ingredients.length !== 1) return null;
  const selected = photographs[`${ingredients[0]}:${productForm(product)}`];
  if (!selected) return null;
  const [key, src] = selected;
  const credit = formCredits.find(c => c.key === key) || credits.find(c => c.key === key);
  return {...credit, key, src, names: credit.names || nutNames[key]};
}

export function catalogImageUrl(value) {
  const url = String(value || "").trim();
  if (url.startsWith("/") && !url.startsWith("//")) return url;
  try { const parsed = new URL(url); return parsed.protocol === "https:" ? parsed.href : ""; }
  catch { return ""; }
}
