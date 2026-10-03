import portfolio from "./__fixtures__/portfolio-names.json";
import {ingredientKeys, matchesCatalogFilter, productForm} from "./catalogIngredients";

test.each(portfolio)("classifies imported $name independently of its $category line", product => {
  const ingredients = ingredientKeys(product);
  expect(ingredients).not.toContain("other");
  expect(ingredients.some(key => matchesCatalogFilter(product, key))).toBe(true);
});
test("ingredient tabs include every presentation and organic variant, not just exact stored categories", () => {
  const acai = portfolio.filter(p => matchesCatalogFilter(p, "acai"));
  expect(acai.length).toBeGreaterThan(5);
  expect(acai.every(p => /açaí/i.test(p.name))).toBe(true);
  expect(acai.some(p => /extract powder/i.test(p.name))).toBe(true);
  expect(acai.some(p => /freeze dried/i.test(p.name))).toBe(true);
  expect(acai.some(p => /pulp|polpa/i.test(p.name))).toBe(true);
  expect(matchesCatalogFilter({name:"MORINGA POWDER",category:"acai"},"acai")).toBe(false);
});
test("juice/pulp and nut tabs distinguish caju juice from cashew nuts", () => {
  expect(matchesCatalogFilter({name:"CASHEW JUICE CLARIFIED",category:"Herbs and Roots"}, "nuts")).toBe(false);
  expect(matchesCatalogFilter({name:"CASHEW JUICE CLARIFIED"}, "juices")).toBe(true);
  expect(matchesCatalogFilter({name:"CASHEW NUTS WW320 - ORGANIC"}, "nuts")).toBe(true);
  expect(matchesCatalogFilter({name:"CASTANHA DE BARU"}, "nuts")).toBe(true);
  expect(matchesCatalogFilter({name:"COCONUT MILK"}, "juices")).toBe(false);
  expect(matchesCatalogFilter({name:"COCONUT MILK CONCENTRATED"}, "juices")).toBe(false);
  expect(ingredientKeys({name:"ORA PRONOBIS (LEMON VINE) POWDER"})).toEqual(["ora-pro-nobis"]);
});
test.each([
  ["AÇAÍ EXTRACT POWDER", "extract-powder"], ["AÇAÍ FREEZE DRIED", "freeze-dried"],
  ["AÇAÍ EM POLPA 12% SÓLIDOS", "pulp"], ["GUARANA FLUID EXTRACT 4–6%", "liquid-extract"],
  ["COCONUT FLOUR DEGREASED", "flour"], ["ACEROLA CLARIFIED CONCENTRATE", "concentrate"],
  ["CASTANHA DE CAJU W320", "nuts"], ["MANGO", "unknown"],
  ["AÇAÍ EXTRACT LIQUID", "liquid-extract"], ["AÇAÍ EXTRACT", "unknown"],
  ["COCONUT MILK CONCENTRATED", "milk-concentrate"],
])("recognizes %s as %s", (name, form) => expect(productForm({name})).toBe(form));
