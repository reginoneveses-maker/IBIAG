import React from "react";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import TradeIntel from "./TradeIntel";
import Pipeline from "./Pipeline";
import Documentos from "./gestao/Documentos";
import { api } from "@/AuthContext";
import { previewMime } from "@/lib/api";

jest.mock("@/AuthContext", () => ({api: {get: jest.fn(), post: jest.fn(), patch: jest.fn(), delete: jest.fn()}, useAuth: () => ({user: {id: "u", role: "admin"}})}));
jest.mock("@/i18n", () => ({useLang: () => ({t: key => key})}));
jest.mock("sonner", () => ({toast: {error: jest.fn(), success: jest.fn(), info: jest.fn()}}));
jest.mock("@/components/ui/dialog", () => ({
  Dialog: ({open,children}) => open ? <div>{children}</div> : null,
  DialogContent: ({children}) => <div>{children}</div>, DialogHeader: ({children}) => <div>{children}</div>,
  DialogTitle: ({children}) => <h2>{children}</h2>, DialogFooter: ({children}) => <div>{children}</div>
}));
const buyer={company:"ABC-Ingredients",country:"Portugal",product_interest:"Acerola",website:"https://example.com",source_url:"https://example.com/company",priority_score:80};
const response = data => Promise.resolve({data});
const mount = (Component, path="/") => render(<MemoryRouter initialEntries={[path]}><Component/></MemoryRouter>);
beforeEach(()=>{
  jest.clearAllMocks();
  api.get.mockImplementation(path=>response(path==="/document-folders"?["Produtos","Produtos/Acerola","Produtos/Acerola/COA"]:path==="/documents/page"?{items:[],total:0}:[]));
  api.post.mockResolvedValue({data:{id:"lead1"}});
});
afterEach(cleanup);
async function searchBuyers(){
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Acerola"}});
  fireEvent.change(screen.getByPlaceholderText("País, ex.: Estados Unidos"),{target:{value:"Portugal"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  await screen.findByText("ABC-Ingredients");
}

test("buyer has visible site/source links and CRM deep link after saving",async()=>{
  api.post.mockImplementation(path=>response(path==="/buyer-discovery/search"?{results:[buyer]}:{id:"lead1"}));
  mount(TradeIntel);await searchBuyers();
  expect(screen.getByRole("link",{name:"Abrir site da empresa"}).getAttribute("href")).toBe(buyer.website+"/");
  fireEvent.click(screen.getByRole("button",{name:"Adicionar ao CRM"}));
  const link=await screen.findByRole("link",{name:"Ver empresa no CRM"});
  expect(link.getAttribute("href")).toBe("/prospects/pipeline?lead=lead1");
  expect(api.post).toHaveBeenCalledWith("/buyer-discovery/to-crm",expect.objectContaining({country:"Portugal",product_interest:"Acerola"}),{timeout:90000});
});

test("decision search preserves company source and displays not found",async()=>{
  api.post.mockImplementation(path=>response(path==="/buyer-discovery/search"?{results:[buyer]}:{validation_status:"not_found",decision_source_url:"https://example.com/team"}));
  mount(TradeIntel);await searchBuyers();
  fireEvent.click(screen.getByRole("button",{name:"Buscar decisor"}));
  await screen.findByText("Decisor não encontrado");
  expect(screen.getByRole("link",{name:"Fonte da empresa"}).getAttribute("href")).toBe(buyer.source_url);
  expect(screen.getByRole("link",{name:"Fonte do decisor"}).getAttribute("href")).toBe("https://example.com/team");
});

test("new buyer search removes old actionable results while loading",async()=>{
  let finish;
  api.post.mockImplementationOnce(()=>response({results:[buyer]})).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  mount(TradeIntel);await searchBuyers();
  fireEvent.change(screen.getByPlaceholderText("País, ex.: Estados Unidos"),{target:{value:"Canada"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  expect(screen.queryByText("ABC-Ingredients")).toBeNull();
  await act(async()=>finish({data:{results:[]}}));
});

test("documents area/type/certificate filters render without undefined variables",async()=>{
  const docs=[{id:"d1",title:"Orgânico Acerola",category:"Produtos",product_name:"Acerola",document_type:"Certificado",certificate_type:"Orgânico",file_name:"cert.pdf",folder_path:"Produtos/Acerola/COA"},
    {id:"d2",title:"Laudo Acerola",category:"Produtos",product_name:"Acerola",document_type:"COA / Laudo",file_name:"coa.pdf"}];
  api.get.mockImplementation(path=>response(path==="/documents/page"?{items:docs,total:2}:path==="/document-folders"?["Produtos","Produtos/Acerola","Produtos/Acerola/COA"]:[]));
  mount(Documentos);await screen.findByText("Orgânico Acerola");
  fireEvent.change(screen.getByLabelText("Filtrar área"),{target:{value:"Produtos"}});
  fireEvent.click(screen.getByRole("button",{name:/^Certificado 1 documentos$/}));
  expect(screen.queryByText("Laudo Acerola")).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:/^Orgânico 1 documentos$/}));
  expect(screen.getByRole("button",{name:"Baixar Orgânico Acerola"})).toBeTruthy();
});

test("folder navigation and upload send selected destination in one request",async()=>{
  mount(Documentos);
  await screen.findByRole("button",{name:"Produtos"});
  fireEvent.click(screen.getByRole("button",{name:"Produtos"}));
  fireEvent.click(screen.getByRole("button",{name:"Acerola"}));
  fireEvent.click(screen.getByRole("button",{name:"COA"}));
  fireEvent.click(screen.getByRole("button",{name:"Novo documento"}));
  expect(screen.getByLabelText("Pasta de destino").value).toBe("Produtos/Acerola/COA");
  const fileInput=document.querySelector('input[type="file"]:not(.hidden)');
  fireEvent.change(fileInput,{target:{files:[new File(["pdf"],"coa.pdf",{type:"application/pdf"})]}});
  fireEvent.click(screen.getByRole("button",{name:"Salvar documento"}));
  await waitFor(()=>expect(api.post).toHaveBeenCalledWith("/documents/upload",expect.any(FormData)));
  const fd=api.post.mock.calls.find(([path])=>path==="/documents/upload")[1];
  expect(JSON.parse(fd.get("metadata")).folder_path).toBe("Produtos/Acerola/COA");
  expect(api.post.mock.calls.some(([path])=>path==="/upload")).toBe(false);
});

test("CRM URL opens requested company with document actions",async()=>{
  api.get.mockImplementation(path=>response(path==="/leads/lead1"?{...buyer,id:"lead1",decision_maker_email:"ana@example.com"}:path==="/documents"?[{id:"doc",title:"Laudo"}]:[]));
  mount(Pipeline,"/prospects/pipeline?lead=lead1");
  await screen.findByRole("heading",{name:/ABC-Ingredients/});
  await screen.findByRole("button",{name:"Baixar Laudo"});
  expect(screen.getByRole("link",{name:"Gerenciar documentos desta empresa"}).getAttribute("href")).toBe("/gestao/documentos?lead=lead1");
});


test("creating a folder opens it and makes upload destination clear",async()=>{
  api.post.mockResolvedValue({data:{path:"Clientes/Acme"}});
  mount(Documentos);await screen.findByRole("button",{name:"Criar pasta"});
  fireEvent.change(screen.getByLabelText("Nome da nova subpasta"),{target:{value:"Clientes/Acme"}});
  fireEvent.click(screen.getByRole("button",{name:"Criar pasta"}));
  await screen.findByText("Pasta atual: Raiz / Clientes/Acme");
  fireEvent.click(screen.getByRole("button",{name:"Novo documento"}));
  expect(screen.getByLabelText("Pasta de destino").value).toBe("Clientes/Acme");
});

test("PDF preview uses native object with open/download fallback, not sandboxed iframe",async()=>{
  const doc={id:"pdf",title:"Laudo PDF",file_name:"laudo.pdf",file_path:"u/pdf",category:"Produtos"};
  URL.createObjectURL=jest.fn(()=>"blob:test-pdf");URL.revokeObjectURL=jest.fn();
  api.get.mockImplementation(path=>response(path==="/documents/page"?{items:[doc],total:1}:path.startsWith("/files/")?new Blob(["%PDF-1.4 test"],{type:"application/pdf"}):[]));
  mount(Documentos);await screen.findByRole("button",{name:"Visualizar Laudo PDF"});
  fireEvent.click(screen.getByRole("button",{name:"Visualizar Laudo PDF"}));
  await screen.findByRole("link",{name:"Abrir em nova aba"});
  expect(document.querySelector('object[type="application/pdf"]').getAttribute("data")).toBe("blob:test-pdf");
  expect(document.querySelector("iframe")).toBeNull();
  expect(screen.getByRole("button",{name:"Baixar arquivo"})).toBeTruthy();
});

test("preview checks file signature and rejects HTML and SVG regardless of filename",()=>{
  expect(previewMime(new Uint8Array([37,80,68,70,45]))).toBe("application/pdf");
  expect(previewMime(new Uint8Array([137,80,78,71,13,10,26,10]))).toBe("image/png");
  expect(previewMime(new TextEncoder().encode("<html><script>test</script>"))).toBe("");
  expect(previewMime(new TextEncoder().encode("<svg onload='test'>"))).toBe("");
});
