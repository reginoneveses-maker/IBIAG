// Loads project TypeScript in isolated verification scripts; optional stubs are test-only.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),ts=require('typescript');
const root=path.resolve(__dirname,'..','..');
function createLoader(stubs={}){const cache={};
 function load(file){file=path.resolve(file);if(cache[file])return cache[file].exports;
 if(file.endsWith('.json'))return JSON.parse(fs.readFileSync(file,'utf8'));
 const m={exports:{}};cache[file]=m;
 const req=name=>Object.prototype.hasOwnProperty.call(stubs,name)?stubs[name]:name.startsWith('@/')?load(resolveTs(path.join(root,name.slice(2)))):name.startsWith('.')?load(resolveTs(path.resolve(path.dirname(file),name))):require(name);
 vm.runInThisContext('(function(require,module,exports){'+ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,resolveJsonModule:true,jsx:ts.JsxEmit.ReactJSX}}).outputText+'\n})')(req,m,m.exports);return m.exports;
 }return load;
}
function resolveTs(base){return ['.ts','.tsx','.json',''].map(ext=>base+ext).find(f=>fs.existsSync(f))||base}
module.exports={load:createLoader(),createLoader,root};
