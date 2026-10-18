import React from "react";
import {render, screen, fireEvent, waitFor, cleanup} from "@testing-library/react";
import AccountAccess from "./AccountAccess";
import {api} from "@/lib/api";
import {useAuth} from "@/AuthContext";
import {toast} from "sonner";
jest.mock("@/lib/api", () => ({api:{get:jest.fn(),patch:jest.fn()}}));
jest.mock("@/AuthContext", () => ({useAuth:jest.fn()}));
jest.mock("sonner", () => ({toast:{success:jest.fn(),error:jest.fn()}}));
const member={id:"member",name:"Alice",email:"alice@example.com",role:"user"};
beforeEach(() => {
  jest.clearAllMocks();
  useAuth.mockReturnValue({user:{id:"admin",role:"admin"}});
  api.get.mockResolvedValue({data:[member,{id:"admin",name:"Admin",role:"admin"}]});
  api.patch.mockResolvedValue({data:{...member,active:false}});
});
afterEach(cleanup);

test("common user cannot load the directory", () => {
  useAuth.mockReturnValue({user:{id:"member",role:"user"}});
  render(<AccountAccess/>);
  expect(api.get).not.toHaveBeenCalled();
  expect(screen.queryByRole("button")).toBeNull();
});

test("suspension requires confirmation and preserves the account with a reactivation action", async () => {
  render(<AccountAccess/>);
  fireEvent.click(await screen.findByRole("button",{name:"Suspender conta"}));
  expect(api.patch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Cancelar"}));
  expect(api.patch).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"Suspender conta"}));
  fireEvent.click(screen.getByRole("button",{name:"Confirmar suspensão"}));
  await screen.findByRole("button",{name:"Reativar conta"});
  expect(api.patch).toHaveBeenCalledWith("/auth/users/member/active",{active:false});
  expect(screen.getByText("Alice")).toBeTruthy();
  expect(screen.queryByRole("button",{name:"Suspender conta"})).toBeNull();
});

test("reactivation submits true and explains that a new login is needed", async () => {
  api.get.mockResolvedValue({data:[{...member,active:false}]});
  api.patch.mockResolvedValue({data:{...member,active:true}});
  render(<AccountAccess/>);
  fireEvent.click(await screen.findByRole("button",{name:"Reativar conta"}));
  fireEvent.click(screen.getByRole("button",{name:"Confirmar reativação"}));
  await screen.findByRole("button",{name:"Suspender conta"});
  expect(api.patch).toHaveBeenCalledWith("/auth/users/member/active",{active:true});
  expect(toast.success).toHaveBeenCalledWith(expect.stringContaining("entrar novamente"));
});

test("failed mutation keeps the original account state and permits retry", async () => {
  api.patch.mockRejectedValue(new Error("private-provider-detail"));
  render(<AccountAccess/>);
  fireEvent.click(await screen.findByRole("button",{name:"Suspender conta"}));
  fireEvent.click(screen.getByRole("button",{name:"Confirmar suspensão"}));
  await waitFor(() => expect(toast.error).toHaveBeenCalled());
  expect(screen.queryByRole("button",{name:"Reativar conta"})).toBeNull();
  expect(toast.error).not.toHaveBeenCalledWith(expect.stringContaining("private-provider-detail"));
  expect(screen.getByRole("button",{name:"Confirmar suspensão"}).disabled).toBe(false);
});
