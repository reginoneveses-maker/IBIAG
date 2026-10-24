import React from "react";
import {render,screen} from "@testing-library/react";
import CommercialOnly from "./CommercialOnly";
jest.mock("react-router-dom",()=>({Link:({children})=><a>{children}</a>}));
let mockCurrent;
jest.mock("@/AuthContext",()=>({useAuth:()=>({user:mockCurrent})}));
test("commercial profile is explicit and does not require administrator role",()=>{
 mockCurrent={role:"user"};const view=render(<CommercialOnly><p>Quote screen</p></CommercialOnly>);
 expect(screen.queryByText("Quote screen")).toBeNull();
 mockCurrent={role:"user",commercial_profile:"commercial-operator-v1"};view.rerender(<CommercialOnly><p>Quote screen</p></CommercialOnly>);
 expect(screen.getByText("Quote screen")).toBeTruthy();
 mockCurrent={role:"user",commercial_profile:"owner"};view.rerender(<CommercialOnly><p>Quote screen</p></CommercialOnly>);
 expect(screen.queryByText("Quote screen")).toBeNull();
});
