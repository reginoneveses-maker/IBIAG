export const normalizeProductText = value => String(value || "").normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

// Imported portfolio lines (e.g. Herbs and Roots) are not ingredient categories.
// Match names first; never turn every uncategorized product into açaí.
export const INGREDIENTS = [
  ["acai", "Açaí", "Açaí", /\bacai\b/],
  ["acerola", "Acerola", "Acerola", /\bacerola\b/],
  ["coconut", "Coco", "Coconut", /\b(?:coco|coconut)\b/],
  ["cashew", "Caju", "Cashew", /\b(?:caju|cashew)\b/],
  ["brazil-nut", "Castanha-do-pará", "Brazil nuts", /\b(?:castanha (?:do |de )?(?:para|brasil)|brazil(?:ian)? nuts?)\b/],
  ["baru", "Baru", "Baru", /\bbaru\b/],
  ["guarana", "Guaraná", "Guarana", /\bguarana\b/],
  ["camu-camu", "Camu-camu", "Camu-camu", /\bcamu ?camu\b/],
  ["pineapple", "Abacaxi", "Pineapple", /\b(?:abacaxi|pineapple)\b/],
  ["orange", "Laranja", "Orange", /\b(?:laranja|orange)\b/],
  ["passion-fruit", "Maracujá", "Passion fruit", /\b(?:maracuja|passion ?fruit)\b/],
  ["guava", "Goiaba", "Guava", /\b(?:goiaba|guava)\b/],
  ["lime", "Limão", "Lime", /\b(?:limao tahiti|lime)\b/],
  ["banana", "Banana", "Banana", /\bbanana\b/],
  ["cupuacu", "Cupuaçu", "Cupuacu", /\b(?:cupuacu|cupuassu)\b/],
  ["mango", "Manga", "Mango", /\b(?:manga|mango)\b/],
  ["lemon", "Limão-siciliano", "Lemon", /\b(?:limao siciliano|lemon)\b(?! vine)/],
  ["andiroba", "Andiroba", "Andiroba", /\bandiroba\b/],
  ["apple", "Maçã", "Apple", /\b(?:maca|apple)\b/],
  ["artichoke", "Alcachofra", "Artichoke", /\b(?:alcachofra|artichoke)\b/],
  ["babassu", "Babaçu", "Babassu", /\b(?:babacu|babassu)\b/],
  ["bacaba", "Bacaba", "Bacaba", /\bbacaba\b/],
  ["bacuri", "Bacuri", "Bacuri", /\bbacuri\b/],
  ["cocoa", "Cacau", "Cocoa", /\b(?:cacau|cocoa|cacao)\b/],
  ["caja", "Cajá", "Caja", /\b(?:caja|tapereba)\b/],
  ["cariru", "Cariru", "Cariru", /\bcariru\b/],
  ["catuaba", "Catuaba", "Catuaba", /\bcatuaba\b/],
  ["chicory", "Chicória", "Chicory", /\b(?:chicoria|chicory)\b/],
  ["grape", "Uva", "Grape", /\b(?:uva|grape)\b/],
  ["soursop", "Graviola", "Soursop", /\b(?:graviola|soursop)\b/],
  ["green-coffee", "Café verde", "Green coffee", /\b(?:cafe verde|green coffee)\b/],
  ["hibiscus", "Hibisco / Vinagreira", "Hibiscus", /\b(?:hibisco|hibiscus|vinagreira)\b/],
  ["jambu", "Jambu", "Jambu", /\b(?:jambu|paracress)\b/],
  ["lithothamnium", "Lithothamnium", "Lithothamnium", /\blithothamn(?:ium|ion)\b/],
  ["melon", "Melão", "Melon", /\b(?:melao|melon)\b/],
  ["moringa", "Moringa", "Moringa", /\bmoringa\b/],
  ["muirapuama", "Muira puama", "Muira puama", /\bmuira ?puama\b/],
  ["ora-pro-nobis", "Ora-pro-nóbis", "Ora-pro-nobis", /\b(?:ora ?pro ?nobis|lemon vine)\b/],
  ["papaya", "Mamão", "Papaya", /\b(?:mamao|papaya)\b/],
  ["pau-darco", "Pau d’arco", "Pau d’arco", /\bpau ?d[ae]? ?arco\b/],
  ["ginseng", "Ginseng brasileiro", "Brazilian ginseng", /\b(?:pfaffia|ginseng)\b/],
  ["dragon-fruit", "Pitaya", "Dragon fruit", /\b(?:pitaya|dragon fruit)\b/],
  ["pupunha", "Pupunha", "Pupunha", /\bpupunha\b/],
  ["quercetin", "Quercetina", "Quercetin", /\b(?:quercetin|quercetina)\b/],
  ["rutin", "Rutina", "Rutin", /\b(?:rutin|rutina)\b/],
  ["strawberry", "Morango", "Strawberry", /\b(?:morango|strawberry)\b/],
  ["taioba", "Taioba", "Taioba", /\btaioba\b/],
  ["tamarind", "Tamarindo", "Tamarind", /\btamarind[oa]?\b/],
  ["tangerine", "Tangerina", "Tangerine", /\b(?:tangerina|tangerine)\b/],
  ["tonka", "Cumaru", "Tonka", /\b(?:cumaru|tonka)\b/],
  ["watermelon", "Melancia", "Watermelon", /\b(?:melancia|watermelon)\b/],
  ["mate", "Erva-mate", "Yerba mate", /\b(?:erva mate|yerba ?mate|mate)\b/],
];

export function ingredientKeys(product) {
  const name = normalizeProductText(product.name);
  const matches = INGREDIENTS.filter(([, , , rule]) => rule.test(name)).map(([key]) => key);
  return matches.length ? matches : ["other"];
}

export function productForm(product) {
  const name = normalizeProductText(product.name);
  if (/\b(?:freeze dried|freeze powder|liofilizad[oa])\b/.test(name)) return "freeze-dried";
  if (/\b(?:liquid|fluid|liquido|fluido)\b.*\b(?:extract|extrato)\b|\b(?:extract|extrato)\b.*\b(?:liquid|fluid|liquido|fluido)\b/.test(name)) return "liquid-extract";
  if (/\b(?:extract|extrato)\b/.test(name)) return /\b(?:dry|seco|powder|po)\b/.test(name) ? "extract-powder" : "unknown";
  if (/\b(?:flour|farinha)\b/.test(name)) return "flour";
  if (/\b(?:powder|po|ground)\b/.test(name)) return "powder";
  if (/\b(?:pulp|polpa|puree)\b/.test(name)) return "pulp";
  if (/\b(?:milk|leite)\b/.test(name)) return /\b(?:concentrat\w*|concentrad\w*)\b/.test(name) ? "milk-concentrate" : "milk";
  if (/\b(?:concentrat\w*|concentrad\w*)\b/.test(name)) return "concentrate";
  if (/\b(?:juice|suco)\b/.test(name)) return "juice";
  if (/\b(?:water|agua)\b/.test(name)) return "water";
  if (/\b(?:oil|oleo)\b/.test(name)) return "oil";
  if (/\b(?:nuts?|castanha)\b/.test(name)) return "nuts";
  if (/\b(?:seed|seeds|semente|sementes)\b/.test(name)) return "seeds";
  if (/\b(?:cut|leaves|leaf|folha|folhas|cancheada)\b/.test(name)) return "cut";
  return "unknown";
}

export function matchesCatalogFilter(product, filter) {
  if (filter === "all") return true;
  const ingredients = ingredientKeys(product);
  if (filter === "juices") return ["pulp", "concentrate", "juice"].includes(productForm(product));
  if (filter === "nuts") return ingredients.some(key => ["cashew", "brazil-nut", "baru"].includes(key)) && productForm(product) === "nuts";
  return ingredients.includes(filter);
}
