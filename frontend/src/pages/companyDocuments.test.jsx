import React from "react";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import TradeIntel from "./TradeIntel";
import Specs from "./gestao/Specs";
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
  fireEvent.change(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal"),{target:{value:"Portugal"}});
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
  fireEvent.change(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal"),{target:{value:"Canada"}});
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

const multiJob = {id:"job1",product:"Acerola",label:"Alemanha, Espanha, Portugal",status:"complete",completed:3,total:3,progress:{},results:[{...buyer,company:"Empresa alemã",country:"Alemanha",country_code:"DE"},{...buyer,company:"Empresa portuguesa"}]};
test("multi-country search preserves each market and filters results",async()=>{
  api.post.mockImplementation(path=>response(path==="/buyer-discovery/search-jobs"?multiJob:{id:"lead1"}));
  api.get.mockImplementation(path=>response(path.includes("search-jobs")?multiJob:[]));
  mount(TradeIntel);
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Acerola"}});
  fireEvent.change(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal"),{target:{value:"Alemanha, Espanha, Portugal"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  await screen.findByText("Empresa alemã");
  expect(api.post).toHaveBeenCalledWith("/buyer-discovery/search-jobs",{product:"Acerola",countries:["Alemanha","Espanha","Portugal"],region:"",limit:10,replace_previous:true});
  fireEvent.change(screen.getByLabelText("Filtrar resultados por país"),{target:{value:"Alemanha"}});
  expect(screen.queryByText("Empresa portuguesa")).toBeNull();
  fireEvent.click(screen.getByRole("button",{name:"Adicionar ao CRM"}));
  await waitFor(()=>expect(api.post).toHaveBeenCalledWith("/buyer-discovery/to-crm",expect.objectContaining({country:"Alemanha",country_code:"DE"}),{timeout:90000}));
});
test("region search starts a job and completed job resumes on reload without another search",async()=>{
  api.post.mockResolvedValue({data:multiJob});api.get.mockImplementation(path=>response(path.includes("search-jobs")?multiJob:[]));
  mount(TradeIntel);
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Acerola"}});
  fireEvent.change(screen.getByLabelText("Região da pesquisa"),{target:{value:"asia"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  await screen.findByText("Empresa alemã");
  expect(api.post).toHaveBeenCalledWith("/buyer-discovery/search-jobs",{product:"Acerola",countries:[],region:"asia",limit:10,replace_previous:true});
  cleanup();api.post.mockClear();mount(TradeIntel,"/?buyer_job=job1");
  await screen.findByText("Empresa portuguesa");expect(api.post).not.toHaveBeenCalled();
});

test("clear aborts pending single search and a late answer cannot overwrite the next search",async()=>{
  let oldAnswer;
  api.post.mockImplementationOnce(()=>new Promise(resolve=>{oldAnswer=resolve;})).mockImplementationOnce(()=>response({results:[{...buyer,company:"Nova empresa",product_interest:"Guarana"}]}));
  mount(TradeIntel);
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Acerola"}});
  fireEvent.change(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal"),{target:{value:"Portugal"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  const signal=api.post.mock.calls[0][2].signal;
  fireEvent.click(screen.getByRole("button",{name:"Limpar pesquisa"}));
  expect(signal.aborted).toBe(true);
  expect(screen.getByPlaceholderText("Produto, ex.: Acerola Powder").value).toBe("");
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Guarana"}});
  fireEvent.change(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal"),{target:{value:"Espanha"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  await screen.findByText("Nova empresa");
  await act(async()=>oldAnswer({data:{results:[buyer]}}));
  expect(screen.queryByText("ABC-Ingredients")).toBeNull();
  expect(screen.getByText("Nova empresa")).toBeTruthy();
  expect(api.post.mock.calls[1][1]).toEqual({product:"Guarana",country:"Espanha",limit:10});
});
test("editing the product removes completed results before the next search",async()=>{
  api.post.mockResolvedValue({data:{results:[buyer]}});
  mount(TradeIntel);await searchBuyers();
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Manga"}});
  expect(screen.queryByText("ABC-Ingredients")).toBeNull();
});
test("clear removes a resumed job and rejects its late polling response",async()=>{
  let oldPoll;
  api.get.mockImplementation(path=>path.includes("search-jobs/old")?new Promise(resolve=>{oldPoll=resolve;}):response(path.includes("search-jobs/job1")?multiJob:[]));
  api.post.mockImplementation(path=>response(path==="/buyer-discovery/search-jobs"?multiJob:{cancel_requested:true}));
  mount(TradeIntel,"/?buyer_job=old");
  await waitFor(()=>expect(oldPoll).toBeDefined());
  fireEvent.click(screen.getByRole("button",{name:"Limpar pesquisa"}));
  expect(api.post).toHaveBeenCalledWith("/buyer-discovery/search-jobs/old/cancel");
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Acerola"}});
  fireEvent.change(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal"),{target:{value:"DE,PT"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  await screen.findByText("Empresa alemã");
  await act(async()=>oldPoll({data:{...multiJob,id:"old",results:[{...buyer,company:"Empresa antiga"}]}}));
  expect(screen.queryByText("Empresa antiga")).toBeNull();
  expect(screen.getByText("Empresa alemã")).toBeTruthy();
});
test("known directory links are identified as sources instead of official company websites",async()=>{
  api.post.mockResolvedValue({data:{results:[{...buyer,is_directory:true,website:"https://www.europages.com/company"}]}});
  mount(TradeIntel);await searchBuyers();
  expect(screen.getByRole("link",{name:"Abrir fonte no diretório"})).toBeTruthy();
  expect(screen.queryByRole("link",{name:"Abrir site da empresa"})).toBeNull();
});

test("a job created after clearing is cancelled instead of reopening its results",async()=>{
  let created;
  api.post.mockImplementation(path=>path==="/buyer-discovery/search-jobs"?new Promise(resolve=>{created=resolve;}):response({cancel_requested:true}));
  mount(TradeIntel);
  fireEvent.change(screen.getByPlaceholderText("Produto, ex.: Acerola Powder"),{target:{value:"Acerola"}});
  fireEvent.change(screen.getByLabelText("Região da pesquisa"),{target:{value:"europe"}});
  fireEvent.click(screen.getByRole("button",{name:"Buscar compradores"}));
  fireEvent.click(screen.getByRole("button",{name:"Limpar pesquisa"}));
  await act(async()=>created({data:multiJob}));
  expect(api.post).toHaveBeenCalledWith("/buyer-discovery/search-jobs/job1/cancel");
  expect(screen.getByLabelText("Região da pesquisa").value).toBe("");
  expect(screen.getByPlaceholderText("Países, ex.: Alemanha, Espanha, Portugal").disabled).toBe(false);
  expect(screen.queryByText("Empresa alemã")).toBeNull();
});

const supplierFixtures=[{id:"s1",name:"Nossa Fruta"},{id:"s2",name:"Itaueira"}];
const specFixtures={items:[{id:"document:d1",document_id:"d1",source_type:"document",supplier_id:"s1",supplier_name:"Nossa Fruta",product_name:"Acerola",title:"Ficha técnica Acerola",original_file_path:"shared/spec",original_file_name:"acerola.pdf"},{id:"document:d2",document_id:"d2",source_type:"document",supplier_id:"s2",supplier_name:"Itaueira",product_name:"Manga",original_file_path:"manga",original_file_name:"manga.pdf"}],unassigned:[{id:"document:u",document_id:"u",source_type:"document",product_name:"Guaraná",original_file_path:"guarana",original_file_name:"guarana.pdf",assignment_reason:"Fornecedor não identificado."}],counts:{s1:1,s2:1},total:2};
test("supplier specs include central documents, stay scoped when switching and survive reload",async()=>{
  api.get.mockImplementation(path=>response(path==="/suppliers"?supplierFixtures:path==="/specs/library"?specFixtures:[]));
  mount(Specs,"/gestao/prospeccao?supplier=s1");
  await screen.findByRole("button",{name:"Baixar acerola.pdf"});
  expect(screen.queryByRole("button",{name:"Baixar manga.pdf"})).toBeNull();
  fireEvent.click(screen.getByTestId("supplier-tab-s2"));
  expect(screen.getByRole("button",{name:"Baixar manga.pdf"})).toBeTruthy();
  expect(screen.queryByRole("button",{name:"Baixar acerola.pdf"})).toBeNull();
  cleanup();mount(Specs,"/gestao/prospeccao?supplier=s2");
  await screen.findByRole("button",{name:"Baixar manga.pdf"});
  expect(screen.queryByRole("button",{name:"Baixar acerola.pdf"})).toBeNull();
});
test("unassigned technical document can be linked to its supplier without uploading again",async()=>{
  let linked=false;
  api.get.mockImplementation(path=>response(path==="/suppliers"?supplierFixtures:path==="/specs/library"?linked?{...specFixtures,items:[...specFixtures.items,{...specFixtures.unassigned[0],supplier_id:"s1",supplier_name:"Nossa Fruta"}],unassigned:[],counts:{s1:2,s2:1}}:specFixtures:[]));
  api.patch.mockImplementation(()=>{linked=true;return response({supplier_id:"s1"});});
  mount(Specs);await screen.findByRole("button",{name:"Sem fornecedor (1)"});
  fireEvent.click(screen.getByRole("button",{name:"Sem fornecedor (1)"}));
  fireEvent.change(screen.getByLabelText("Fornecedor de Guaraná"),{target:{value:"s1"}});
  fireEvent.click(screen.getByRole("button",{name:"Vincular fornecedor"}));
  await waitFor(()=>expect(api.patch).toHaveBeenCalledWith("/specs/documents/u/supplier",{supplier_id:"s1"}));
  await waitFor(()=>expect(screen.queryByRole("button",{name:"Sem fornecedor (1)"})).toBeNull());
  fireEvent.click(screen.getByTestId("supplier-tab-s1"));
  expect(screen.getByRole("button",{name:"Baixar guarana.pdf"})).toBeTruthy();
  expect(api.post).not.toHaveBeenCalled();
});
