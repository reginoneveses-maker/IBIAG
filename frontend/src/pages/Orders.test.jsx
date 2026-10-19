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
  expect(screen.getByTestId("current-route").textContent).toBe("/prospects/orders");
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
  expect(screen.getByLabelText("Empresa do CRM").value).toBe("");
});
