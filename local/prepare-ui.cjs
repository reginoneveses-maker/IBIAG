// Local builds must not need Google Fonts to render the application shell.
const fs = require("node:fs");
const html = "public/index.html";
fs.writeFileSync(html, fs.readFileSync(html, "utf8")
  .replace(/^\s*<link\b[^>]*https:\/\/fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*$/gm, ""));
const css = "src/index.css";
fs.writeFileSync(css, fs.readFileSync(css, "utf8")
  .replace(/^@import\s+url\(['"]https:\/\/fonts\.googleapis\.com[^\r\n]*\);\s*$/gm, ""));
