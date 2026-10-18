import React from "react";
import {render, screen, fireEvent, waitFor, cleanup} from "@testing-library/react";
import Tasks from "./Tasks";
import {api} from "@/lib/api";
import {useAuth} from "@/AuthContext";
import {toast} from "sonner";
jest.mock("@/lib/api", () => ({api:{get:jest.fn(),post:jest.fn(),patch:jest.fn(),delete:jest.fn()}}));
jest.mock("@/AuthContext", () => ({useAuth:jest.fn()}));
jest.mock("@/i18n", () => ({useLang:()=>({t:key=>key})}));
jest.mock("sonner", () => ({toast:{success:jest.fn(),error:jest.fn()}}));
const task={id:"legacy",title:"Existing task",completed:false,owner_id:""};
beforeEach(()=>{
  jest.clearAllMocks();
  api.get.mockImplementation(path=>Promise.resolve({data:path==="/tasks"?[task]:[
    {id:"alice",name:"Alice",email:"alice@example.com"},{id:"bob",name:"Bob",email:"bob@example.com"}]}));
});
afterEach(cleanup);

test("ordinary users do not request user directory or receive assignment controls",async()=>{
  useAuth.mockReturnValue({user:{id:"alice",role:"user"}});
  render(<Tasks/>);
  await screen.findByText("Existing task");
  expect(screen.queryByRole("combobox")).toBeNull();
  expect(api.get).not.toHaveBeenCalledWith("/auth/users");
});

test("administrator explicitly assigns a legacy task",async()=>{
  useAuth.mockReturnValue({user:{id:"admin",role:"admin"}});
  api.patch.mockResolvedValue({data:{...task,owner_id:"alice"}});
  render(<Tasks/>);
  const selector=await screen.findByRole("combobox",{name:"Responsável: Existing task"});
  await screen.findByRole("option",{name:"Alice"});
  expect(selector.value).toBe("");
  fireEvent.change(selector,{target:{value:"alice"}});
  await waitFor(()=>expect(api.patch).toHaveBeenCalledWith("/tasks/legacy/owner",{owner_id:"alice"}));
  await waitFor(()=>expect(selector.value).toBe("alice"));
  expect(toast.success).toHaveBeenCalledWith("Responsável atualizado.");
});

test("failed assignment preserves the previous owner",async()=>{
  useAuth.mockReturnValue({user:{id:"admin",role:"admin"}});
  api.patch.mockRejectedValue(new Error("denied"));
  render(<Tasks/>);
  const selector=await screen.findByRole("combobox",{name:"Responsável: Existing task"});
  await screen.findByRole("option",{name:"Bob"});
  fireEvent.change(selector,{target:{value:"bob"}});
  await waitFor(()=>expect(toast.error).toHaveBeenCalledWith("Não foi possível alterar o responsável."));
  expect(selector.value).toBe("");
});
