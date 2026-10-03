const { chromium } = require("playwright");
const { spawn } = require("node:child_process");
const path = require("node:path");
const assert = require("node:assert/strict");
const root = path.resolve(__dirname, "../..");
const server = spawn(process.env.PYTHON || "python", ["backend/browser_fixture.py"], {cwd: root, stdio: ["ignore", "inherit", "inherit"]});
const base = "http://127.0.0.1:8765";
(async () => {
  let browser;
  try {
    let ready = false;
    for (let i=0; i<100; i++) {
      if(server.exitCode !== null) throw new Error("Test server exited");
      try { ready = (await fetch(base+"/login")).ok; } catch {}
      if(ready) break;
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    assert(ready, "Test server did not start");
    browser = await chromium.launch({headless:true, args:["--no-sandbox"]});
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    const errors=[];page.on("pageerror", e=>errors.push(e.message));
    const login = await page.request.post(base+"/api/auth/login", {data:{email:"test@example.com",password:"browser-test"}});
    assert.equal(login.status(),200);
    const {access_token}=await login.json();
    await page.addInitScript(token=>localStorage.setItem("token",token),access_token);
    await page.goto(base+"/prospects/trade");
    await page.getByPlaceholder("Produto, ex.: Acerola Powder").fill("Acerola");
    await page.getByPlaceholder("País, ex.: Estados Unidos").fill("Portugal");
    await page.getByRole("button",{name:"Buscar compradores",exact:true}).click();
    await page.getByText("ABC-Ingredients",{exact:true}).waitFor();
    assert.equal(await page.getByRole("link",{name:"Fonte da empresa",exact:true}).getAttribute("href"),"https://example.com/company");
    await page.getByRole("button",{name:"Buscar decisor",exact:true}).click();
    await page.getByText("ana@example.com",{exact:true}).waitFor();
    await page.getByRole("button",{name:"Adicionar ao CRM",exact:true}).click();
    await page.getByRole("link",{name:"Ver empresa no CRM",exact:true}).click();
    await page.getByRole("heading",{name:/ABC-Ingredients/}).waitFor();
    await page.getByText(/E-mail do decisor: ana@example.com/).waitFor();
    await page.reload();
    await page.getByRole("heading",{name:/ABC-Ingredients/}).waitFor();
    await page.getByRole("link",{name:"Gerenciar documentos desta empresa"}).click();
    await page.getByLabel("Nome da nova subpasta").fill("Produtos/Acerola/COA");
    await page.getByRole("button",{name:"Criar pasta",exact:true}).click();
    await page.getByRole("button",{name:"Produtos",exact:true}).click();
    await page.getByRole("button",{name:"Acerola",exact:true}).click();
    await page.getByRole("button",{name:"COA",exact:true}).click();
    await page.getByRole("button",{name:"Novo documento",exact:true}).click();
    assert.equal(await page.getByLabel("Pasta de destino").inputValue(),"Produtos/Acerola/COA");
    await page.getByPlaceholder("Título",{exact:true}).fill("Laudo Acerola");
    await page.locator('input[type="file"]:not(.hidden)').setInputFiles({name:"coa.pdf",mimeType:"application/pdf",buffer:Buffer.from("%PDF-1.4 fixture")});
    await page.getByRole("button",{name:"Salvar documento",exact:true}).click();
    await page.getByText("Laudo Acerola",{exact:true}).waitFor();
    const downloadPromise=page.waitForEvent("download");
    await page.getByRole("button",{name:"Baixar Laudo Acerola",exact:true}).click();
    const download=await downloadPromise;assert.equal(download.suggestedFilename(),"coa.pdf");
    await page.reload();
    await page.getByText("Laudo Acerola",{exact:true}).waitFor();
    await page.getByRole("button",{name:"Classificar Laudo Acerola",exact:true}).click();
    await page.getByLabel("Pasta do documento").fill("Produtos/Acerola/Arquivados");
    await page.getByRole("button",{name:"Salvar classificação",exact:true}).click();
    await page.getByText(/Produtos\/Acerola\/Arquivados/).waitFor();
    await page.reload();
    await page.getByText(/Produtos\/Acerola\/Arquivados/).waitFor();
    assert.deepEqual(errors,[]);
    console.log("PASS browser: search → decision → CRM → reload → company documents → folder upload → download → move → reload");
  } finally {
    if(browser) await browser.close();
    server.kill("SIGTERM");
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
