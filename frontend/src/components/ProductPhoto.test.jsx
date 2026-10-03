import React from "react";
import {render, screen, fireEvent, cleanup} from "@testing-library/react";
import ProductPhoto from "./ProductPhoto";
import {catalogImageUrl, productPhoto} from "@/lib/productPhotos";

afterEach(cleanup);
test.each(["AÇAÍ EXTRACT POWDER", "AÇAÍ FREEZE DRIED - ORGANIC", "AÇAÍ EM POLPA 12% SÓLIDOS", "Acai pulp organic"])("imported %s gets a licensed real ingredient photo", name => {
  render(<ProductPhoto product={{name, image_url:""}} lang="pt"/>);
  expect(screen.getByRole("img").getAttribute("src")).toBeTruthy();
  expect(screen.getByRole("img").getAttribute("alt")).toContain("Açaí");
  expect(screen.getByText("Foto do ingrediente · representativa")).toBeTruthy();
  expect(screen.getByRole("link", {name:"Fonte da foto de Açaí"}).getAttribute("href")).toContain("commons.wikimedia.org");
});
test("different nuts are distinguished; unrelated products and blends get no guessed photo", () => {
  expect(productPhoto({name:"CASTANHA DE CAJU W320"}).key).toBe("cashew");
  expect(productPhoto({name:"CASTANHA-DO-PARÁ"}).key).toBe("brazil-nut");
  expect(productPhoto({name:"Guaraná em pó"}).key).toBe("guarana-powder");
  expect(productPhoto({name:"Guaraná fruit"})).toBeNull();
  expect(productPhoto({name:"Açaí com banana"})).toBeNull();
  expect(productPhoto({name:"Tomate",category:"acai"})).toBeNull();
  expect(productPhoto({name:"Caju juice"})).toBeNull();
});
test("registered photo takes priority; a failed URL falls back once to the ingredient and ends with readable text if both fail", () => {
  render(<ProductPhoto product={{name:"Acerola powder",image_url:"https://example.com/actual-acerola.jpg"}} lang="en"/>);
  expect(screen.getByRole("img").getAttribute("src")).toBe("https://example.com/actual-acerola.jpg");
  expect(screen.queryByText("Representative ingredient photo")).toBeNull();
  fireEvent.error(screen.getByRole("img"));
  expect(screen.getByRole("img").getAttribute("src")).not.toContain("example.com");
  expect(screen.getByText("Representative ingredient photo")).toBeTruthy();
  fireEvent.error(screen.getByRole("img"));
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText("Product photo not available yet")).toBeTruthy();
});
test("empty, mixed-content and unsafe image URLs cannot create broken image requests", () => {
  for (const url of ["", "http://example.com/p.jpg", "javascript:alert(1)", "//example.com/p.jpg", "data:text/html,test"])
    expect(catalogImageUrl(url)).toBe("");
  expect(catalogImageUrl("/static/media/photo.jpg")).toBe("/static/media/photo.jpg");
  expect(catalogImageUrl(" https://example.com/p.jpg ")).toBe("https://example.com/p.jpg");
  render(<ProductPhoto product={{name:"Produto não identificado",image_url:""}} lang="pt"/>);
  expect(screen.queryByRole("img")).toBeNull();
  expect(screen.getByText("Foto do produto ainda não disponível")).toBeTruthy();
});
