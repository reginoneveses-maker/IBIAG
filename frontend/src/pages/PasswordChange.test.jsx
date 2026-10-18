import React from "react";
import {render, screen, fireEvent, waitFor, cleanup} from "@testing-library/react";
import PasswordChange from "./PasswordChange";
import {useAuth} from "@/AuthContext";
import {toast} from "sonner";
jest.mock("@/AuthContext",()=>({useAuth:jest.fn()}));
jest.mock("sonner",()=>({toast:{error:jest.fn(),success:jest.fn()}}));
const changePassword=jest.fn();
beforeEach(()=>{jest.clearAllMocks();useAuth.mockReturnValue({changePassword});changePassword.mockResolvedValue();});
afterEach(cleanup);
function fill(confirmation="updated-password") {
  fireEvent.change(screen.getByLabelText("Senha atual"),{target:{value:"old-password"}});
  fireEvent.change(screen.getByLabelText("Nova senha"),{target:{value:"updated-password"}});
  fireEvent.change(screen.getByLabelText("Confirmar nova senha"),{target:{value:confirmation}});
  fireEvent.submit(screen.getByRole("button").closest("form"));
}
test("requires matching confirmation before submitting",()=>{
  render(<PasswordChange/>);fill("different-password");
  expect(changePassword).not.toHaveBeenCalled();
  expect(toast.error).toHaveBeenCalled();
});
test("submits current and new password and clears all password inputs",async()=>{
  render(<PasswordChange/>);fill();
  await waitFor(()=>expect(toast.success).toHaveBeenCalled());
  expect(changePassword).toHaveBeenCalledWith("old-password","updated-password");
  expect(screen.getByLabelText("Senha atual").value).toBe("");
  expect(screen.getByLabelText("Nova senha").value).toBe("");
  expect(screen.getByLabelText("Confirmar nova senha").value).toBe("");
});
test("failed request clears password inputs without exposing raw errors",async()=>{
  changePassword.mockRejectedValue(new Error("private-error-canary"));
  render(<PasswordChange/>);fill();
  await waitFor(()=>expect(toast.error).toHaveBeenCalled());
  expect(toast.error).not.toHaveBeenCalledWith(expect.stringContaining("private-error-canary"));
  expect(screen.getByLabelText("Senha atual").value).toBe("");
  expect(screen.getByLabelText("Nova senha").value).toBe("");
});
