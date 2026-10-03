import React from "react";
import {render, screen, fireEvent, cleanup} from "@testing-library/react";
import Catalog from "./Catalog";
import portfolio from "@/lib/__fixtures__/portfolio-names.json";
import {api} from "@/AuthContext";
import {matchesCatalogFilter} from "@/lib/catalogIngredients";
jest.mock("@/AuthContext", () => ({api:{get:jest.fn()}}));
jest.mock("@/i18n", () => ({useLang:()=>({lang:"pt",t:key=>key})}));
jest.mock("sonner", () => ({toast:{success:jest.fn()}}));
const products=portfolio.map((p,i)=>({...p,id:String(i),certifications:[],image_url:""}));
afterEach(cleanup);
test("each tab and additional ingredient selector display their imported products and return to Todos", async () => {
  api.get.mockResolvedValue({data:products});
  render(<Catalog/>);
  await screen.findByTestId("product-card-0");
  expect(screen.getAllByTestId(/^product-card-/).length).toBe(products.length);
  for(const key of ["acai","acerola","coconut","nuts","juices"]){
    fireEvent.click(screen.getByTestId(`filter-${key}`));
    const expected=products.filter(p=>matchesCatalogFilter(p,key));
    expect(expected.length).toBeGreaterThan(0);
    expect(screen.getAllByTestId(/^product-card-/).map(el=>el.dataset.testid))
      .toEqual(expected.map(p=>`product-card-${p.id}`));
    expect(screen.getByTestId(`filter-${key}`).getAttribute("aria-pressed")).toBe("true");
  }
  fireEvent.change(screen.getByTestId("ingredient-filter"),{target:{value:"moringa"}});
  expect(screen.getAllByTestId(/^product-card-/).length).toBe(1);
  expect(screen.getByRole("heading",{name:"MORINGA POWDER ORGANIC"})).toBeTruthy();
  fireEvent.click(screen.getByTestId("filter-all"));
  expect(screen.getAllByTestId(/^product-card-/).length).toBe(products.length);
  expect(screen.getByTestId("ingredient-filter").value).toBe("");
});
test("failed catalog requests show a retry and recover without an empty silent screen",async()=>{
  api.get.mockRejectedValueOnce(new Error("network")).mockResolvedValueOnce({data:products.slice(0,1)});
  render(<Catalog/>);
  expect(await screen.findByRole("alert")).toBeTruthy();
  fireEvent.click(screen.getByRole("button",{name:"Tentar novamente"}));
  await screen.findByTestId("product-card-0");
  expect(screen.queryByRole("alert")).toBeNull();
});
