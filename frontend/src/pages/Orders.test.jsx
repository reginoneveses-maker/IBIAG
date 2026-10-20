import React from "react";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import Orders from "./Orders";
import { api, useAuth } from "@/AuthContext";
import { toast } from "sonner";
jest.mock("@/AuthContext",()=>({api:{get:jest.fn(),post:jest.fn(),put:jest.fn(),delete:jest.fn()},useAuth:jest.fn()}));
jest.mock("sonner",()=>({toast:{error:jest.fn(),success:jest.fn()}}));
jest.mock("@/components/ui/dialog",()=>({
  Dialog:({open,children})=>open?<div>{children}</div>:null,
  DialogContent:({children})=><div>{children}</div>,DialogHeader:({children})=><div>{children}</div>,
  DialogTitle:({children})=><h2>{children}</h2>,DialogFooter:({children})=><div>{children}</div>
}));
const lead={id:"crm1",company:"Existing Buyer",country:"Portugal"};
function LocationEcho(){const location=useLocation();return <output data-testid="current-route">{location.pathname+location.search}</output>;}
const mount=(url="/prospects/orders")=>render(<MemoryRouter initialEntries={[url]}><Orders/><LocationEcho/></MemoryRouter>);
beforeEach(()=>{
  jest.clearAllMocks();
  Object.defineProperty(global,"crypto",{configurable:true,value:{randomUUID:()=>"new-order"}});
  useAuth.mockReturnValue({user:{id:"admin",role:"admin"}});
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/leads"?[lead]:path==="/leads/crm1"?lead:[]}));
  api.post.mockResolvedValue({data:{}});
});
afterEach(cleanup);

test("selecting CRM buyer fills readonly identity and saves existing order endpoint only",async()=>{
  mount();fireEvent.click(screen.getByTestId("new-order-button"));
  await screen.findByRole("option",{name:"Existing Buyer · Portugal"});
  fireEvent.change(screen.getByLabelText("Empresa do CRM"),{target:{value:"crm1"}});
  expect(screen.getByTestId("ord-customer-input").value).toBe("Existing Buyer");
  expect(screen.getByTestId("ord-customer-input").readOnly).toBe(true);
  expect(screen.getByLabelText("País").value).toBe("Portugal");
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByTestId("save-order-button"));
  await waitFor(()=>expect(api.post).toHaveBeenCalledWith("/orders",expect.objectContaining({lead_id:"crm1",customer:"Existing Buyer",customer_country:"Portugal",status:"draft",items:[]})));
  expect(api.post.mock.calls).toHaveLength(1);
});

test("CRM shortcut opens prefilled draft without saving automatically",async()=>{
  mount("/prospects/orders?lead=crm1");
  await screen.findByRole("heading",{name:"Pedido de venda"});
  expect(screen.getByTestId("ord-customer-input").value).toBe("Existing Buyer");
  expect(screen.getByLabelText("Empresa do CRM").value).toBe("crm1");
  expect(api.post).not.toHaveBeenCalled();
  await waitFor(()=>expect(screen.getByTestId("current-route").textContent).toBe("/prospects/orders"));
});

test("CRM picker loads beyond first 250 companies",async()=>{
  const page=Array.from({length:250},(_,i)=>({id:`id${i}`,company:`Buyer ${i}`}));
  api.get.mockImplementation((path,config)=>Promise.resolve({data:path==="/leads"?(config.params.skip===0?page:[lead]):[]}));
  mount();fireEvent.click(screen.getByTestId("new-order-button"));
  await screen.findByRole("option",{name:"Existing Buyer · Portugal"});
  expect(api.get).toHaveBeenCalledWith("/leads",{params:{skip:250,limit:250}});
});

test("load failure can retry and cannot silently replace an existing linked client",async()=>{
  let failed=true;
  const order={id:"order",customer:"Historical Buyer",customer_country:"Spain",lead_id:"crm1",status:"confirmed",total_usd:10};
  api.get.mockImplementation(path=>path==="/leads"&&failed?Promise.reject(new Error("offline")):Promise.resolve({data:path==="/orders"?[order]:path==="/leads"?[lead]:[]}));
  mount();fireEvent.click(await screen.findByRole("button",{name:"Editar"}));
  const retry=await screen.findByRole("button",{name:"Tentar carregar empresas novamente"});
  failed=false;fireEvent.click(retry);
  await screen.findByRole("option",{name:"Existing Buyer · Portugal"});
  expect(screen.getByLabelText("Empresa do CRM").disabled).toBe(true);
  expect(screen.getByTestId("ord-customer-input").value).toBe("Historical Buyer");
  expect(screen.getByLabelText("País").value).toBe("Spain");
  expect(screen.getByRole("link",{name:"Ver empresa no CRM"}).getAttribute("href")).toBe("/prospects/pipeline?lead=crm1");
});

test("failed source lookup does not create or open an unintended order",async()=>{
  api.get.mockImplementation(path=>path==="/leads/crm1"?Promise.reject(new Error("missing")):Promise.resolve({data:[]}));
  mount("/prospects/orders?lead=crm1");
  await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("Não foi possível abrir a empresa do CRM. Nenhum pedido foi criado."));
  expect(screen.queryByTestId("save-order-button")).toBeNull();expect(api.post).not.toHaveBeenCalled();
});

test("late shortcut response cannot overwrite a manually opened draft",async()=>{
  let resolve;
  api.get.mockImplementation(path=>path==="/leads/crm1"?new Promise(r=>{resolve=r;}):Promise.resolve({data:[]}));
  mount("/prospects/orders?lead=crm1");fireEvent.click(screen.getByTestId("new-order-button"));
  fireEvent.change(screen.getByTestId("ord-customer-input"),{target:{value:"Manual draft"}});
  await act(async()=>resolve({data:lead}));
  expect(screen.getByTestId("ord-customer-input").value).toBe("Manual draft");
  await waitFor(()=>expect(screen.getByTestId("current-route").textContent).toBe("/prospects/orders"));
  expect(screen.getByLabelText("Empresa do CRM").value).toBe("");
});

const source={source_price_id:"calc1",source_price_revision:"a".repeat(64),source_price_snapshot:{product_name:"Product",quantity:1000,unit:"kg",sale_total_usd:4260},total_usd:4260,
  items:[{product_id:"p",offer_id:"offer",product_name:"Product",supplier_id:"s",supplier_name:"Supplier",quantity:1000,unit:"kg",unit_price:4.26}]};

test("saved calculation opens a frozen draft and requires explicit customer/save",async()=>{
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/prices/calc1/order-draft"?source:path==="/leads"?[lead]:path==="/product-offers"?[{id:"offer",product_id:"p",product_name:"Product",supplier_name:"Supplier"}]:[]}));
  mount("/prospects/orders?price=calc1");
  await screen.findByTestId("order-price-origin");
  expect(screen.getByLabelText("Quantidade do item 1").value).toBe("1000");
  expect(screen.getByLabelText("Preço USD do item 1").value).toBe("4.26");
  expect(screen.getByLabelText("Quantidade do item 1").disabled).toBe(true);
  expect(screen.getByLabelText("Situação do pedido").disabled).toBe(true);
  expect(screen.queryByRole("button",{name:"Adicionar item"})).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
  fireEvent.click(screen.getByTestId("save-order-button"));
  expect(api.post).not.toHaveBeenCalled();
  await screen.findByRole("option",{name:"Existing Buyer · Portugal"});
  fireEvent.change(screen.getByLabelText("Empresa do CRM"),{target:{value:"crm1"}});
  fireEvent.click(screen.getByTestId("save-order-button"));
  await waitFor(()=>expect(api.post).toHaveBeenCalledWith("/orders",expect.objectContaining({source_price_id:"calc1",source_price_revision:"a".repeat(64),lead_id:"crm1",status:"draft",total_usd:4260})));
  expect(api.post.mock.calls[0][1].source_price_snapshot).toBeUndefined();
  await waitFor(()=>expect(screen.getByTestId("current-route").textContent).toBe("/prospects/orders"));
});

test("combined CRM and calculation shortcut prepares one draft and consumes both parameters",async()=>{
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/prices/calc1/order-draft"?source:path==="/leads/crm1"?lead:path==="/leads"?[lead]:[]}));
  mount("/prospects/orders?lead=crm1&price=calc1");
  await screen.findByTestId("order-price-origin");
  expect(screen.getByTestId("ord-customer-input").value).toBe("Existing Buyer");
  expect(screen.getByLabelText("Quantidade do item 1").value).toBe("1000");
  await waitFor(()=>expect(screen.getByTestId("current-route").textContent).toBe("/prospects/orders"));
  expect(api.post).not.toHaveBeenCalled();
});

test("stale calculation rejection preserves the form and never retries creation automatically",async()=>{
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/prices/calc1/order-draft"?source:path==="/leads"?[lead]:[]}));
  api.post.mockRejectedValue({response:{status:409,data:{detail:"O cálculo mudou. Confira novamente."}}});
  mount("/prospects/orders?price=calc1");
  await screen.findByTestId("order-price-origin");
  await screen.findByRole("option",{name:"Existing Buyer · Portugal"});
  fireEvent.change(screen.getByLabelText("Empresa do CRM"),{target:{value:"crm1"}});
  fireEvent.click(screen.getByTestId("save-order-button"));
  await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("O cálculo mudou. Confira novamente."));
  expect(screen.getByTestId("save-order-button")).toBeTruthy();expect(api.post.mock.calls).toHaveLength(1);
});

test("late calculation lookup cannot replace a manually opened draft",async()=>{
  let resolve;
  api.get.mockImplementation(path=>path==="/prices/calc1/order-draft"?new Promise(r=>{resolve=r;}):Promise.resolve({data:[]}));
  mount("/prospects/orders?price=calc1");fireEvent.click(screen.getByTestId("new-order-button"));
  fireEvent.change(screen.getByTestId("ord-customer-input"),{target:{value:"Manual price"}});
  await act(async()=>resolve({data:source}));
  expect(screen.queryByTestId("order-price-origin")).toBeNull();
  expect(screen.getByTestId("ord-customer-input").value).toBe("Manual price");
  await waitFor(()=>expect(screen.getByTestId("current-route").textContent).toBe("/prospects/orders"));
});

test("invalid calculation explains the required correction without creating or opening an order",async()=>{
  api.get.mockImplementation(path=>path==="/prices/calc1/order-draft"?Promise.reject({response:{status:400,data:{detail:"Vincule o cálculo a uma oferta de produto e fornecedor antes de criar um pedido."}}}):Promise.resolve({data:[]}));
  mount("/prospects/orders?price=calc1");
  await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("Vincule o cálculo a uma oferta de produto e fornecedor antes de criar um pedido."));
  expect(screen.queryByTestId("save-order-button")).toBeNull();expect(api.post).not.toHaveBeenCalled();
});

test("approved quotation opens readonly draft and sends revision without client snapshot",async()=>{
 const source={source_quote_id:"q1",source_quote_revision:2,source_quote_snapshot:{reference:"COT-1",payment_terms:"Prepaid",delivery_terms:"Santos",valid_until:"2099-12-31"},lead_id:"crm1",customer:"Existing Buyer",customer_country:"Portugal",incoterm:"DAP",items:[{product_id:"p",offer_id:"offer",quantity:2,unit:"kg",unit_price:4}],total_usd:8};
 api.get.mockImplementation(path=>Promise.resolve({data:path==="/quotations/q1/order-draft"?source:path==="/leads"?[lead]:[]}));mount("/prospects/orders?quote=q1");await screen.findByTestId("order-quote-origin");expect(screen.getByLabelText("Empresa do CRM").disabled).toBe(true);expect(screen.getByLabelText("Incoterm").disabled).toBe(true);expect(screen.getByLabelText("Quantidade do item 1").disabled).toBe(true);expect(screen.getByLabelText("Situação do pedido").disabled).toBe(true);expect(api.post).not.toHaveBeenCalled();fireEvent.click(screen.getByTestId("save-order-button"));await waitFor(()=>expect(api.post).toHaveBeenCalledWith("/orders",expect.objectContaining({source_quote_id:"q1",source_quote_revision:2,status:"draft",incoterm:"DAP"})));expect(api.post.mock.calls[0][1].source_quote_snapshot).toBeUndefined();
});
test("ambiguous quotation and price shortcuts cannot open or save an unintended order",async()=>{mount("/prospects/orders?quote=q1&price=p1");await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("Escolha uma única origem para o pedido. Nenhum pedido foi criado."));expect(screen.queryByTestId("save-order-button")).toBeNull();expect(api.post).not.toHaveBeenCalled();});
