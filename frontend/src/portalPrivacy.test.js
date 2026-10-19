import fs from "fs";
import path from "path";

const html = fs.readFileSync(path.resolve(__dirname, "../public/index.html"), "utf8");

test("portal entry point contains no inline scripts or externally executable scripts", () => {
  const document = new DOMParser().parseFromString(html, "text/html");
  // CRA injects the locally built bundles later; the checked-in shell needs no
  // executable vendor scripts or inline tracking/configuration.
  expect(document.querySelectorAll("script")).toHaveLength(0);
  expect(document.querySelector("#root")).not.toBeNull();
});

test("portal shell does not hide runtime errors or create tracking globals", () => {
  expect(html).not.toMatch(/posthog|emergent-main\.js|stopImmediatePropagation|preventDefault\(\)/i);
  const document = new DOMParser().parseFromString(html, "text/html");
  expect([...document.querySelectorAll("*")].flatMap(element =>
    [...element.attributes].filter(attribute => /^on/i.test(attribute.name)))).toHaveLength(0);
});
