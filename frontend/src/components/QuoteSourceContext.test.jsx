import React from "react";
import {render,screen,fireEvent,act,cleanup} from "@testing-library/react";
import QuoteSourceContext from "./QuoteSourceContext";
import {api} from "@/AuthContext";
import {documentPreview} from "@/lib/api";
jest.mock("@/AuthContext",()=>({api:{get:jest.fn()}}));
jest.mock("@/lib/api",()=>({documentPreview:jest.fn(),downloadDocument:jest.fn()}));
const context=name=>({supplier:{name,contact:"Synthetic contact",email:"supplier@example.test",phone:"+00 000"},
 product:{name:"Ingredient"},conditions:{"MOQ registrado":"25 kg"},linksRequiringReview:1,
 documents:[{id:"cert",kind:"certification",title:"Synthetic certificate",expiryDate:"2000-01-01",flags:["expired"],
 files:[{label:"certificado",file_path:"fixture/cert.pdf",file_name:"cert.pdf"}]}]});
beforeEach(()=>{jest.clearAllMocks();URL.revokeObjectURL=jest.fn()});
afterEach(cleanup);
test("context warns about expiry and unresolved links without changing the quotation",async()=>{
 api.get.mockResolvedValue({data:context("Supplier")});
 render(<><input aria-label="Quantity already entered" defaultValue="1000"/><QuoteSourceContext offerId="offer"/></>);
 await screen.findByText("Synthetic certificate");
 expect(screen.getByText(/Vencido/)).toBeTruthy();
 expect(screen.getByText(/vínculo\(s\) sem documento visível único/)).toBeTruthy();
 expect(screen.getByLabelText("Quantity already entered").value).toBe("1000");
 expect(api.get).toHaveBeenCalledWith("/integrated/offers/offer/context",{timeout:15000});
});
test("a late response from a previous ingredient cannot replace the current supplier",async()=>{
 const resolve={};api.get.mockImplementation(path=>new Promise(r=>{resolve[path]=r}));
 const view=render(<QuoteSourceContext offerId="first"/>);view.rerender(<QuoteSourceContext offerId="second"/>);
 await act(async()=>resolve["/integrated/offers/second/context"]({data:context("Current supplier")}));
 await screen.findByText("Current supplier");
 await act(async()=>resolve["/integrated/offers/first/context"]({data:context("Stale supplier")}));
 expect(screen.queryByText("Stale supplier")).toBeNull();
 expect(screen.getByText("Current supplier")).toBeTruthy();
});
test("failed context can be retried without clearing fields or a draft",async()=>{
 api.get.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce({data:context("Recovered supplier")});
 render(<><input aria-label="Manual price" defaultValue="17.5"/><QuoteSourceContext offerId="offer"/></>);
 await screen.findByRole("alert");
 fireEvent.click(screen.getByRole("button",{name:"Recarregar consulta sem alterar cotação"}));
 await screen.findByText("Recovered supplier");
 expect(screen.getByLabelText("Manual price").value).toBe("17.5");
 expect(api.get).toHaveBeenCalledTimes(2);
});
test("private file failure keeps the quotation and does not create a preview",async()=>{
 api.get.mockImplementation(path=>path.includes("/context")?Promise.resolve({data:context("Supplier")}):Promise.reject(new Error("403")));
 render(<><input aria-label="Draft quantity" defaultValue="1000"/><QuoteSourceContext offerId="offer"/></>);
 fireEvent.click(await screen.findByRole("button",{name:"Visualizar certificado"}));
 await screen.findByRole("alert");
 expect(screen.queryByLabelText("Prévia do documento privado")).toBeNull();
 expect(screen.getByLabelText("Draft quantity").value).toBe("1000");
 expect(documentPreview).not.toHaveBeenCalled();
});
test("a file arriving after ingredient change is ignored before decoding",async()=>{
 let finish;api.get.mockImplementation(path=>path.includes("/context")?Promise.resolve({data:context(path.includes("first")?"First":"Second")}):new Promise(r=>{finish=r}));
 const view=render(<QuoteSourceContext offerId="first"/>);
 fireEvent.click(await screen.findByRole("button",{name:"Visualizar certificado"}));
 view.rerender(<QuoteSourceContext offerId="second"/>);
 await screen.findByText("Second");
 await act(async()=>finish({data:new Blob(["%PDF-1.4"])}));
 expect(documentPreview).not.toHaveBeenCalled();
 expect(screen.queryByLabelText("Prévia do documento privado")).toBeNull();
});
test("closing a recognized private preview revokes its object URL",async()=>{
 api.get.mockImplementation(path=>Promise.resolve({data:path.includes("/context")?context("Supplier"):new Blob(["%PDF-1.4"])}));
 documentPreview.mockResolvedValue({kind:"pdf",url:"blob:synthetic-preview"});
 render(<QuoteSourceContext offerId="offer"/>);
 fireEvent.click(await screen.findByRole("button",{name:"Visualizar certificado"}));
 await screen.findByLabelText("Prévia do documento privado");
 fireEvent.click(screen.getByRole("button",{name:"Fechar documento e continuar cotação"}));
 expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:synthetic-preview");
});
