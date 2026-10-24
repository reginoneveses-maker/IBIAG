// Carrega módulos TypeScript do projeto (com o alias @/) em scripts Node, sem build.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),ts=require('typescript');
const root=path.resolve(__dirname,'..','..'),cache={};
function load(file){
 file=path.resolve(file);if(cache[file])return cache[file].exports;
 if(file.endsWith('.json'))return JSON.parse(fs.readFileSync(file,'utf8'));
 const m={exports:{}};cache[file]=m;
 const req=name=>name.startsWith('@/')?load(resolveTs(path.join(root,name.slice(2)))):name.startsWith('.')?load(resolveTs(path.resolve(path.dirname(file),name))):require(name);
 vm.runInThisContext('(function(require,module,exports){'+ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,resolveJsonModule:true}}).outputText+'\n})')(req,m,m.exports);
 return m.exports;
}
function resolveTs(base){return fs.existsSync(base+'.ts')?base+'.ts':fs.existsSync(base+'.json')?base+'.json':base}
module.exports={load,root};
