import React from "react";
import {render, screen, fireEvent, cleanup, act} from "@testing-library/react";
import {AuthProvider, useAuth, api} from "./AuthContext";

jest.mock("axios", () => ({create: () => ({
  get: jest.fn(), post: jest.fn(),
  interceptors: {request: {use: jest.fn()}},
})}));

function Session() {
  const {user, logout, loading} = useAuth();
  const [result, setResult] = React.useState("");
  return <><span>{loading ? "loading" : user ? "signed in" : "signed out"}</span>
    <button onClick={async () => setResult(String(await logout()))}>Logout</button>
    <output>{result}</output></>;
}
beforeEach(() => {
  localStorage.clear(); jest.clearAllMocks();
  api.get.mockResolvedValue({data:{id:"user"}});
});
afterEach(cleanup);

test("logout revokes captured token and clears local session immediately", async () => {
  localStorage.setItem("token", "old-session");
  let complete;
  api.post.mockReturnValue(new Promise(resolve => {complete=resolve;}));
  render(<AuthProvider><Session/></AuthProvider>);
  await screen.findByText("signed in");
  fireEvent.click(screen.getByText("Logout"));
  expect(localStorage.getItem("token")).toBeNull();
  expect(screen.getByText("signed out")).toBeTruthy();
  expect(api.post).toHaveBeenCalledWith("/auth/logout", null,
    {headers:{Authorization:"Bearer old-session"}, timeout:10000});
  localStorage.setItem("token", "new-session");
  complete({data:{ok:true}});
  await screen.findByText("true");
  expect(localStorage.getItem("token")).toBe("new-session");
});

test("failed remote revocation is reported without restoring browser session", async () => {
  localStorage.setItem("token", "old-session");
  api.post.mockRejectedValue(new Error("offline"));
  render(<AuthProvider><Session/></AuthProvider>);
  await screen.findByText("signed in");
  fireEvent.click(screen.getByText("Logout"));
  await screen.findByText("false");
  expect(localStorage.getItem("token")).toBeNull();
  expect(screen.getByText("signed out")).toBeTruthy();
});

test("logout without a token does not send an unauthenticated request", async () => {
  render(<AuthProvider><Session/></AuthProvider>);
  await screen.findByText("signed out");
  fireEvent.click(screen.getByText("Logout"));
  await screen.findByText("true");
  expect(api.post).not.toHaveBeenCalled();
});

test("an in-flight session check cannot restore user after logout", async () => {
  localStorage.setItem("token", "old-session");
  let finish;
  api.get.mockReturnValue(new Promise(resolve => {finish=resolve;}));
  api.post.mockResolvedValue({data:{ok:true}});
  render(<AuthProvider><Session/></AuthProvider>);
  fireEvent.click(screen.getByText("Logout"));
  await screen.findByText("true");
  await act(async () => { finish({data:{id:"old-user"}}); });
  expect(screen.getByText("signed out")).toBeTruthy();
});

test("request interceptor preserves the captured logout session", () => {
  expect(typeof requestInterceptor).toBe("function");
  localStorage.setItem("token", "new-session");
  expect(requestInterceptor({headers:{Authorization:"Bearer old-session"}}).headers.Authorization)
    .toBe("Bearer old-session");
  expect(requestInterceptor({headers:{}}).headers.Authorization).toBe("Bearer new-session");
});
const requestInterceptor=api.interceptors.request.use.mock.calls[0][0];
