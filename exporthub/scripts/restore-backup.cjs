#!/usr/bin/env node
// Uso: node scripts/restore-backup.cjs IBIAG_backup.zip --state .wrangler/state-restaurado
// Restaura em um ambiente LOCAL vazio (pasta de estado do Wrangler/Miniflare) e confere o resultado. Nunca sobrescreve dados.
const fs=require('node:fs'),{restoreBackup}=require('./lib/backup.cjs');
const [file,flag,state]=process.argv.slice(2);
if(!file||flag!=='--state'||!state){console.error('Uso: node scripts/restore-backup.cjs <backup.zip> --state <pasta de estado nova>');process.exit(2)}
restoreBackup(fs.readFileSync(file),state).then(r=>{for(const w of r.warnings)console.log('Aviso:',w);console.log(`Restauração conferida: ${r.collections} coleções e ${r.files} PDFs idênticos ao backup, em ${state}.`);console.log('Acessos da equipe e histórico de auditoria não fazem parte do backup: o proprietário entra pelo e-mail cadastrado e convida as demais pessoas de novo.')}).catch(e=>{console.error(e.message);process.exit(1)});
