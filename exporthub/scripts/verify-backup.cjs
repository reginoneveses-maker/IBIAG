#!/usr/bin/env node
// Uso: node scripts/verify-backup.cjs IBIAG_backup_AAAA-MM-DD.zip
const fs=require('node:fs'),{verifyBackup}=require('./lib/backup.cjs');
const file=process.argv[2];if(!file){console.error('Informe o arquivo ZIP do Backup com PDFs.');process.exit(2)}
const result=verifyBackup(fs.readFileSync(file));
if(result.summary){const s=result.summary;console.log(`Backup de ${s.exportedAt}: ${s.collections} coleções, ${s.files} PDFs (${(s.bytes/1048576).toFixed(1)} MB) — ${s.specs} specs, ${s.crmFiles} anexos de negociações, ${s.sectorFiles} anexos de processos.`)}
for(const w of result.warnings)console.log('Aviso:',w);
for(const e of result.errors)console.error('ERRO:',e);
console.log(result.errors.length?`\nBackup NÃO confiável (${result.errors.length} erro(s)).`:'\nBackup íntegro: ZIP, CRC dos PDFs, tamanhos, dados validados e vínculos conferidos.');
process.exit(result.errors.length?1:0);
