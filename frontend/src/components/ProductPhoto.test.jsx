import React from "react";
import {render, screen, fireEvent, cleanup} from "@testing-library/react";
import ProductPhoto from "./ProductPhoto";
import {catalogImageUrl, productPhoto} from "@/lib/productPhotos";
afterEach(cleanup);
test.each([
  ["AÇAÍ EXTRACT POWDER", "acai-extract"], ["AÇAÍ EXTRACT POWDER - ORGANIC", "acai-extract"],
  ["AÇAÍ FREEZE DRIED - ORGANIC", "acai-freeze-dried"], ["AÇAÍ EM POLPA 12% SÓLIDOS", "acai-pulp"],
  ["CAMU CAMU EXTRACT POWDER", "camu-camu-extract"], ["ACEROLA POWDER", "acerola-powder"],
  ["GUARANA SEED", "guarana-seeds"],
  ["MUIRAPUAMA POWDER", "muirapuama-powder"], ["MORINGA POWDER - ORGANIC", "moringa-powder"],
  ["PAU DA'ARCO POWDER", "pau-darco-powder"], ["CATUABA POWDER", "catuaba-powder"],
  ["PAU DA'ARCO CUT", "pau-darco-cut"],
])("%s receives a photograph of its documented form", (name, key) => {
  const photo=productPhoto({name,category:"Herbs and Roots"});
  expect(photo.key).toBe(key);
  render(<ProductPhoto product={{name,image_url:""}} lang="pt"/>);
  expect(screen.getByRole("img").getAttribute("alt")).toContain(photo.names[0]);
  expect(screen.getByRole("img").getAttribute("src")).toBe(photo.src);
  expect(screen.getByRole("link").getAttribute("href")).toBe(photo.source);
  expect(screen.getByText(/foto de referência da apresentação/)).toBeTruthy();
});
test.each(["COCONUT WATER", "ACEROLA CLARIFIED CONCENTRATE", "ACEROLA EXTRACT POWDER", "GUARANA FLUID EXTRACT",
  "GUARANA EXTRACT POWDER", "AÇAÍ SINGLE STRENGTH JUICE", "AÇAÍ EXTRACT LIQUID", "AÇAÍ EXTRACT", "MANGO", "Açaí com banana", "Caju juice"])("%s cannot inherit fruit or another form's photo", name => {
  expect(productPhoto({name,category:"acai"})).toBeNull();
});
test("different nuts and ordinary guarana powder keep their licensed photographs", () => {
  expect(productPhoto({name:"CASTANHA DE CAJU W320"}).key).toBe("cashew");
  expect(productPhoto({name:"BRAZILIAN NUTS"}).key).toBe("brazil-nut");
  expect(productPhoto({name:"Guaraná em pó"}).key).toBe("guarana-powder");
});
test("a registered photo has priority, with one form-specific fallback and readable final failure", () => {
  render(<ProductPhoto product={{name:"AÇAÍ EXTRACT POWDER",image_url:"https://example.com/actual.jpg"}} lang="en"/>);
  expect(screen.getByRole("img").getAttribute("src")).toBe("https://example.com/actual.jpg");
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("img").getAttribute("src")).toBe(productPhoto({name:"AÇAÍ EXTRACT POWDER"}).src);
  expect(screen.getByText(/product form reference photo/)).toBeTruthy();
  fireEvent.error(screen.getByRole("img"));
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText("Photo of this product form not available yet")).toBeTruthy();
});
test("empty, mixed-content and unsafe image URLs cannot create broken image requests", () => {
  for (const url of ["", "http://example.com/p.jpg", "javascript:alert(1)", "//example.com/p.jpg", "data:text/html,test"])
    expect(catalogImageUrl(url)).toBe("");
  expect(catalogImageUrl("/static/media/photo.jpg")).toBe("/static/media/photo.jpg");
  expect(catalogImageUrl(" https://example.com/p.jpg ")).toBe("https://example.com/p.jpg");
  render(<ProductPhoto product={{name:"Produto não identificado",image_url:""}} lang="pt"/>);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText("Foto desta apresentação ainda não disponível")).toBeTruthy();
});
