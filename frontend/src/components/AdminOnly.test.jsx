import React from "react";
import {render,screen,cleanup} from "@testing-library/react";
import {MemoryRouter} from "react-router-dom";
import {useAuth} from "@/AuthContext";
import AdminOnly from "./AdminOnly";
jest.mock("@/AuthContext",()=>({useAuth:jest.fn()}));
afterEach(cleanup);
test("denied users cannot mount a protected page or start its API effects",()=>{
  const load=jest.fn();
  function ProtectedPage(){React.useEffect(()=>{load();},[]);return <p>Financial page</p>;}
  useAuth.mockReturnValue({user:{role:"user"}});
  render(<MemoryRouter><AdminOnly><ProtectedPage/></AdminOnly></MemoryRouter>);
  expect(screen.getByRole("alert")).toBeTruthy();
  expect(screen.queryByText("Financial page")).toBeNull();
  expect(load).not.toHaveBeenCalled();
});
test("administrator can open the protected page",()=>{
  useAuth.mockReturnValue({user:{role:"admin"}});
  render(<MemoryRouter><AdminOnly><p>Financial page</p></AdminOnly></MemoryRouter>);
  expect(screen.getByText("Financial page")).toBeTruthy();
});
