# Backup e recuperação — ExportHub IBIAG

Plano objetivo, com o que existe hoje e o que **não** existe. Todo backup contém dados confidenciais (clientes, specs, preços) e **não tem senha**: guarde em local protegido.

## O que cada cópia protege

| Cópia | Onde | Conteúdo | Limites |
|---|---|---|---|
| **Backup com PDFs** (ZIP) | Central de arquivos → *Backup com PDFs* (só o proprietário) | Dados de todas as coleções + todos os PDFs (specs, anexos de negociações e processos) + CRC32 de cada arquivo | Até 1.000 PDFs ou 500 MB por ZIP |
| **Backup dos dados** (JSON) | Central de arquivos → *Backup dos dados* | Dados e índices; **sem PDFs** | Não restaura documentos |
| **Cópias automáticas** | Central de arquivos (rodapé) | Versão anterior de cada coleção, guardada antes de cada gravação | Não inclui PDFs, equipe nem auditoria; não é independente do sistema |

**Fora de todos os backups:** acessos da equipe (convites e perfis) e histórico de auditoria. Depois de uma restauração, o proprietário entra pelo e-mail cadastrado e convida as demais pessoas de novo.

## Rotina recomendada

1. **Semanal** (sexta, fim do dia): baixar o *Backup com PDFs*. Antes também de qualquer importação grande (CRM) ou mudança de estrutura.
2. **Conferir na hora**, com o ZIP já baixado: `node scripts/verify-backup.cjs IBIAG_backup_AAAA-MM-DD.zip`. Só considere o backup válido se terminar com *Backup íntegro* (exit 0). Registro de início no histórico **não prova** que o download terminou.
3. **Guardar duas cópias** em lugares diferentes (por exemplo, pasta criptografada no computador + drive protegido). Manter as últimas 8 semanais e uma por mês durante 12 meses.
4. **Mensal**: simulado de restauração (abaixo). Um backup que nunca foi restaurado não é garantia.
5. **Pessoas**: só o proprietário baixa backups. Ao remover alguém (Central de arquivos → *Equipe e acessos*), o acesso é cortado na hora, mas o que a pessoa já viu ou copiou não é recolhido; dê acesso só a quem precisa e prefira *leitura* quando bastar.

## Simulado de restauração (mensal, ~15 min)

Requer Node 22+, `pnpm install` feito em `exporthub/`.

```sh
node scripts/verify-backup.cjs IBIAG_backup_AAAA-MM-DD.zip
node scripts/restore-backup.cjs IBIAG_backup_AAAA-MM-DD.zip --state .wrangler/state-simulado
```

A restauração grava em um ambiente **local e vazio** (pasta de estado do Wrangler). Ela recusa destino com dados e recusa backup com erro, antes de gravar qualquer coisa. Ao terminar, confere: conteúdo e revisão de cada coleção, IDs, e SHA-256 de cada PDF contra o ZIP. Para abrir o resultado no navegador, aponte o ambiente de desenvolvimento para essa pasta de estado e entre com o e-mail do proprietário.

Registre no fim: data, arquivo usado, resultado (*conferida* / erro) e quem fez.

## Metas honestas

- **Perda máxima aceitável (RPO):** o intervalo desde o último backup válido — até 7 dias com a rotina semanal. Dados de coleções têm também a cópia automática anterior a cada gravação, mas ela não substitui o backup (mesmo sistema, sem PDFs).
- **Tempo de recuperação (RTO):** horas, com assistência técnica. O sistema hospedado atual não oferece a este projeto um comando de restauração sobre a produção: a restauração testada recria os dados em um ambiente local ou em outra hospedagem. Voltar para a produção hospedada exige acesso técnico à hospedagem e deve ser planejado antes de ser preciso.
- **Não coberto:** falha do próprio provedor sem backup recente; arquivos alterados antes do backup; PDFs acima dos limites do ZIP (use os downloads individuais).

## Simulado já executado

Em 14/10/2026, em ambiente de desenvolvimento: PDFs enviados pela API real, ZIP baixado pelo endpoint real (`/api/backup/complete`), conferido com `verify-backup`, restaurado em pasta nova com `restore-backup` e comparado: coleções com a mesma revisão, nomes com acentos preservados e os PDFs idênticos (SHA-256) aos arquivos enviados. Segunda restauração no mesmo destino foi recusada. Testes automáticos: `node scripts/test-backup-restore.cjs`.
