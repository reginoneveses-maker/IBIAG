const path=require('node:path'),fs=require('node:fs');
const esbuild=require('esbuild');
const root=path.resolve(__dirname,'../..'),hub=path.join(root,'exporthub');
(async()=>{
const common={bundle:true,alias:{'@':hub},logLevel:'warning',legalComments:'none',minify:true};
await esbuild.build({...common,entryPoints:[path.join(hub,'integration/native-entry.ts')],platform:'browser',banner:{js:'/* eslint-disable */'},format:'esm',jsx:'automatic',external:['react','react-dom','react/jsx-runtime','lucide-react'],outfile:path.join(root,'frontend/src/integration/quote-components.js')});
await esbuild.build({...common,entryPoints:[path.join(hub,'integration/engine-entry.ts')],platform:'node',format:'cjs',target:'node22',outfile:path.join(root,'backend/generated/quote-engine.cjs')});
})().catch(e=>{console.error(e);process.exitCode=1});
