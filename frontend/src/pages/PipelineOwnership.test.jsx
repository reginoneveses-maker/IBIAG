import React from "react";
import {render,screen,fireEvent,waitFor,cleanup} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import Pipeline from "./Pipeline";
import {api,useAuth} from "@/AuthContext";
import {toast} from "sonner";
jest.mock("@/AuthContext",()=>({api:{get:jest.fn(),post:jest.fn(),patch:jest.fn(),put:jest.fn(),delete:jest.fn()},useAuth:jest.fn()}));
jest.mock("@/i18n",()=>({useLang:()=>({t:key=>key})}));
jest.mock("sonner",()=>({toast:{error:jest.fn(),success:jest.fn()}}));
jest.mock("@/components/ui/dialog",()=>({
  Dialog:({open,children})=>open?<div>{children}</div>:null,
  DialogContent:({children})=><div>{children}</div>,DialogHeader:({children})=><div>{children}</div>,
  DialogTitle:({children})=><h2>{children}</h2>,DialogFooter:({children})=><div>{children}</div>
}));
const lead={id:"legacy",company:"Existing Company",stage:"new_lead",owner_id:""};
const mount=()=>render(<MemoryRouter initialEntries={["/prospects/pipeline?lead=legacy"]}><Pipeline/></MemoryRouter>);
beforeEach(()=>{
  jest.clearAllMocks();
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/leads"?[lead]:path==="/leads/legacy"?lead:
    path==="/auth/users"?[{id:"alice",name:"Alice",email:"alice@example.com"}]:[]}));
});
afterEach(cleanup);

test("ordinary user cannot see assignment control or request user directory",async()=>{
  useAuth.mockReturnValue({user:{id:"alice",role:"user"}});
  mount(); await screen.findByRole("heading",{name:/Existing Company/});
  expect(screen.queryByLabelText("Responsável pelo cadastro")).toBeNull();
  expect(screen.queryByRole("link",{name:"Criar pedido para esta empresa"})).toBeNull();
  expect(api.get).not.toHaveBeenCalledWith("/auth/users");
});
test("administrator explicitly assigns a legacy CRM record",async()=>{
  useAuth.mockReturnValue({user:{id:"admin",role:"admin"}});
  api.patch.mockResolvedValue({data:{...lead,owner_id:"alice"}});
  mount(); const selector=await screen.findByLabelText("Responsável pelo cadastro");
  expect(screen.getByRole("link",{name:"Criar pedido para esta empresa"}).getAttribute("href")).toBe("/prospects/orders?lead=legacy");
  await screen.findByRole("option",{name:"Alice"});
  fireEvent.change(selector,{target:{value:"alice"}});
  await waitFor(()=>expect(api.patch).toHaveBeenCalledWith("/leads/legacy/owner",{owner_id:"alice"}));
  await waitFor(()=>expect(selector.value).toBe("alice"));
});
test("assignment failure preserves previous owner",async()=>{
  useAuth.mockReturnValue({user:{id:"admin",role:"admin"}});
  api.patch.mockRejectedValue(new Error("denied"));
  mount(); const selector=await screen.findByLabelText("Responsável pelo cadastro");
  await screen.findByRole("option",{name:"Alice"});
  fireEvent.change(selector,{target:{value:"alice"}});
  await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("Não foi possível alterar o responsável."));
  expect(selector.value).toBe("");
});
