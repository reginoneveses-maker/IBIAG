import React from "react";
import { render, screen, fireEvent, waitFor, cleanup, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Shipments from "./Shipments";
import { api } from "@/AuthContext";
import { toast } from "sonner";
jest.mock("@/AuthContext",()=>({api:{get:jest.fn(),put:jest.fn()}}));
jest.mock("sonner",()=>({toast:{error:jest.fn(),success:jest.fn()}}));
jest.mock("@/components/ui/dialog",()=>({Dialog:({open,children})=>open?<div>{children}</div>:null,DialogContent:({children})=><div>{children}</div>,DialogHeader:({children})=><div>{children}</div>,DialogTitle:({children})=><h2>{children}</h2>,DialogFooter:({children})=><div>{children}</div>}));
const detail={id:"sale",customer:"Buyer",number:"S1",version:2,shipment:{},allowed_statuses:["planned"]};
const shipment={reference:"SHIP-1",status:"planned",origin:"Santos",destination:"Lisboa",mode:"sea",responsible_id:"owner",planned_departure:"2020-10-02",planned_arrival:"2020-10-10",history:[{id:"event1",by:"admin",at:"2020-10-01",to_status:"planned",note:"Initial plan",changes:{origin:"Santos"}}]};
const mount=(url="/gestao/embarques")=>render(<MemoryRouter initialEntries={[url]}><Shipments/></MemoryRouter>);
beforeEach(()=>{jest.clearAllMocks();api.get.mockImplementation(path=>Promise.resolve({data:path==="/integrated/operators"?[{id:"owner",name:"Owner",active:true,role:"user"}]:path==="/orders/sale/shipment"?detail:[]}));});
afterEach(cleanup);

test("opens deep link and saves only bounded logistics fields with current version",async()=>{
  api.put.mockResolvedValue({data:{...detail,version:3,shipment,allowed_statuses:["planned","booked","cancelled"]}});
  mount("/gestao/embarques?order=sale");await screen.findByRole("heading",{name:"Embarque — Buyer"});
  fireEvent.change(screen.getByLabelText("Referência"),{target:{value:"SHIP-1"}});
  fireEvent.change(screen.getByRole("combobox",{name:"Responsável",exact:true}),{target:{value:"owner"}});
  fireEvent.change(screen.getByLabelText("Motivo da alteração"),{target:{value:"Initial plan"}});
  fireEvent.click(screen.getByRole("button",{name:"Salvar embarque"}));
  await waitFor(()=>expect(api.put).toHaveBeenCalledWith("/orders/sale/shipment",expect.objectContaining({version:2,reference:"SHIP-1",responsible_id:"owner",change_note:"Initial plan"})));
  expect(api.put.mock.calls[0][1]).not.toHaveProperty("history");
  expect(api.put.mock.calls[0][1]).not.toHaveProperty("customer");
  await screen.findByText("Pedido S1 · versão 3");
  expect(screen.getByLabelText("Motivo da alteração").value).toBe("");
  expect(screen.getByRole("button",{name:"Salvar embarque"}).disabled).toBe(true);
  expect(screen.getByText("Initial plan")).not.toBeNull();
});

test("conflict retains entered fields and never retries the write automatically",async()=>{
  api.put.mockRejectedValue({response:{status:409,data:{detail:"Pedido alterado. Recarregue."}}});
  mount("/gestao/embarques?order=sale");await screen.findByLabelText("Referência");
  fireEvent.change(screen.getByLabelText("Referência"),{target:{value:"My reference"}});
  fireEvent.change(screen.getByLabelText("Motivo da alteração"),{target:{value:"Planning"}});
  fireEvent.click(screen.getByRole("button",{name:"Salvar embarque"}));
  await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("Pedido alterado. Recarregue."));
  expect(screen.getByLabelText("Referência").value).toBe("My reference");expect(api.put).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button",{name:"Recarregar pedido"}));
  await screen.findByRole("heading",{name:"Embarque — Buyer"});
  expect(api.get.mock.calls.filter(([path])=>path==="/orders/sale/shipment")).toHaveLength(2);
});

test("archived history is readonly and departure freezes route and real dates",async()=>{
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/integrated/operators"?[]:path==="/orders/sale/shipment"?{...detail,shipment:{...shipment,actual_departure:"2020-10-02"},allowed_statuses:[]}:[]}));
  mount("/gestao/embarques?order=sale");await screen.findByText(/Histórico somente para consulta/);
  expect(screen.getByLabelText("Referência").matches(":disabled")).toBe(true);
  expect(screen.getByLabelText("Origem").readOnly).toBe(true);
  expect(screen.getByLabelText("Saída real").readOnly).toBe(true);
  expect(screen.queryByRole("button",{name:"Salvar embarque"})).toBeNull();
});

test("list retries errors and forwards filters without showing stale rows",async()=>{
  api.get.mockRejectedValueOnce(new Error("offline"));mount();
  await screen.findByRole("alert");
  api.get.mockResolvedValue({data:[{id:"sale",customer:"Buyer",shipment}]});
  fireEvent.click(screen.getByRole("button",{name:"Atualizar lista"}));
  await screen.findByText("SHIP-1 — Buyer");
  fireEvent.change(screen.getByLabelText("Situação logística"),{target:{value:"booked"}});
  await waitFor(()=>expect(api.get).toHaveBeenCalledWith("/shipments",{params:{status:"booked",archived:false,skip:0,limit:50}}));
  fireEvent.click(screen.getByLabelText("Pedidos arquivados"));
  await waitFor(()=>expect(api.get).toHaveBeenCalledWith("/shipments",{params:{status:"booked",archived:true,skip:0,limit:50}}));
});

test("failed detail or directory load never opens an editable form",async()=>{
  api.get.mockImplementation(path=>path==="/integrated/operators"?Promise.reject(new Error("offline")):Promise.resolve({data:path==="/orders/sale/shipment"?detail:[]}));
  mount("/gestao/embarques?order=sale");await screen.findByRole("alert");
  expect(screen.queryByLabelText("Referência")).toBeNull();expect(api.put).not.toHaveBeenCalled();
});

test("a late list response cannot overwrite a newer filter",async()=>{
  let resolveOld;
  api.get.mockImplementationOnce(()=>new Promise(resolve=>{resolveOld=resolve;}));
  mount();
  api.get.mockResolvedValue({data:[]});
  fireEvent.change(screen.getByLabelText("Situação logística"),{target:{value:"delivered"}});
  await screen.findByText("Nenhum embarque nesta página.");
  await act(async()=>{resolveOld({data:[{id:"old",customer:"Old buyer",shipment}]});});
  await waitFor(()=>expect(screen.queryByText("SHIP-1 — Old buyer")).toBeNull());
});
