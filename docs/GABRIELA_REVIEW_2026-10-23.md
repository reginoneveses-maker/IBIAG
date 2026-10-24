# Candidato isolado ExportHub / IBIAG — 23/10/2026

## Preservação e base revisada

Nenhum merge na main, deploy, atualização da instalação, alteração em dados reais, serviço pago, API cobrada ou backup automático foi executado.

- Main observada: c9e2b6508c3f791e0b7ec2ba9863a9a0bf5dae6a.
- Claude: claude/empresa-chatgpt-system-nge71t em 7d5ecb5524ec4c55844b3865d17836ee77d6c628. Oito commits exclusivos, incluindo fórmula da planilha, assistente EXW/DAP, legado em leitura, equipe e recuperação.
- Candidato React/Python: cadeia #28 → #44–#52 → #54 → #55 → #56 → #57, acrescida de improvements/catalog-crm-local em 158f237. #53 é preservação operacional separada, não executada nem incorporada.
- Branch de trabalho: improvements/gabriela-demo-20261023. Composição local com dois pais preserva o histórico Claude e o candidato existente. Não substitui nenhuma das branches de origem.
- As aplicações permanecem separadas: frontend/backend React/FastAPI/MongoDB e exporthub Vinext/D1/R2. Composição sem conflito de texto NÃO unifica bancos, identidade, deploy ou fluxos. Não há migração automática entre elas.

## Implementação desta entrega

1. Segurança: leitura JSON limitada durante o streaming em três rotas de gravação; JSON/UTF-8 inválidos retornam 400 e excesso retorna 413. Revisões exigem inteiros seguros. Perfis desconhecidos não ganham leitura. Autorizações existentes e origem da requisição permanecem obrigatórias.
2. Integridade: vínculos CRM/contatos/cotações/operações/tarefas/processos são validados antes de gravar; exclusões que criem novos órfãos são recusadas. Órfãos legados inalterados não são apagados ou migrados. Referências consultadas participam do guard transacional de revisão: mudança concorrente reverte tudo. A cotação já vinculada não pode perder sua operação para permitir duplicação.
3. Saúde: GET /api/health e /saude, restritos ao proprietário. Consulta banco, presença de binding de armazenamento, revisões e resumo documental sem valores comerciais, notas, caminhos ou e-mails. Limites documentais retornam 413, sem resumo parcial. Não testa conteúdo/acessibilidade de PDFs nem disponibilidade de transportadoras.
4. Qualidade: validade explícita em registros de documentação/qualidade, vencidos, janela de 30 dias, data inválida, certificação sem validade e ausência de referência de anexo. Não atribui validade a specs, não infere aprovação nem conformidade.
5. Trade Intelligence React/Python: ignora negativas/hipóteses na cláusula publicada, não usa recorte sugerido pela IA para remover uma negação, normaliza domínio/porta/ponto final para deduplicar. Usuário do ingrediente é potencial comprador; vendedor permanece identificado como fornecedor. Compra/importação e intenção comercial nunca são presumidas.
6. Rotina: atalhos CRM → cálculo/cotação → processo comercial → documentação → logística, reutilizando telas existentes. Nenhum recurso anterior foi retirado. A UI nova não cria um pedido formal adicional no ExportHub; conserva o modelo de operação existente.
7. Cópias automáticas: código de preservação do Claude continua disponível, porém desativado por padrão. Somente ALLOW_AUTOMATIC_SAFETY_BACKUPS=true no servidor o habilita, mediante autorização separada. Exportação e recuperação manuais permanecem. Nenhuma variável publicada foi alterada.

## Verificação executada localmente

- TypeScript completo: node node_modules/typescript/bin/tsc --noEmit --incremental false — passou.
- Build ExportHub: node scripts/run-framework.mjs build — passou; warnings de bundle >500 kB e classificação estática de rotas do framework permanecem.
- 13 testes novos HTTP/regras/SQLite: scripts/test-health-integrity.cjs — passaram, sem skips.
- D1 local real descartável: scripts/test-health-d1.cjs — passou; rollback integral de conflito, sem auditoria fantasma e saúde sem escrita.
- Dez suítes preservadas do Claude passaram: CRM, navegação, uploads PDF, produto/cotação, variantes, preço unificado, planilha, sessões, membros (D1 local real) e verificação/restauração de backup em destino descartável. Nenhum backup de produção foi feito.
- 40 testes Python: test_buyer_discovery, test_buyer_qualification, test_discovery_jobs — passaram; fontes/provedores simulados, sem consultas externas pagas. Python Windows executado em modo UTF-8.
- Demonstração: sete seções navegadas em Chromium local, 1440 e 390px, zero overflow horizontal, zero erro JavaScript e zero requisição externa. Capturas em demo/.
- O CI foi ampliado para branches improvements/** e um job ExportHub. Estado do CI remoto deve ser consultado no PR; os testes locais NÃO equivalem à suíte completa MongoDB/Docker/React do repositório.

## Demonstração para Gabriela

Abra demo/gabriela.html diretamente no navegador. Arquivo autônomo, dados fictícios, sem rede, salvamento, envio ou cálculo. Reutiliza os componentes de atalhos e saúde, com cenários ilustrativos para as demais etapas. É uma demonstração da organização, não uma homologação do sistema autenticado. Regeneração: node exporthub/scripts/build-gabriela-demo.cjs (a partir da raiz com dependências instaladas em exporthub).

## PRs abertos e dependências

A revisão usa os SHAs registrados em GABRIELA_PR_SNAPSHOT.json. O teste git merge-tree não alterou branches remotas nem fez merges reais desses PRs.

| PR | Base | Head | Composição com o candidato |
|---|---|---|---|
| #57 | operations/quality-local-20261020 | operations/dossier-local-20261020 | Sem conflito textual |
| #56 | operations/samples-local-20261020 | operations/quality-local-20261020 | Sem conflito textual |
| #55 | local/windows-first-20261020 | operations/samples-local-20261020 | Sem conflito textual |
| #54 | operations/document-history-20261020 | local/windows-first-20261020 | Sem conflito textual |
| #53 | operations/document-history-20261020 | operations/preservation-safe-copy-20261020 | Sem conflito textual |
| #52 | operations/operational-dashboard-20261020 | operations/document-history-20261020 | Sem conflito textual |
| #51 | operations/packing-list-20261020 | operations/operational-dashboard-20261020 | Sem conflito textual |
| #50 | operations/commercial-invoice-20261019 | operations/packing-list-20261020 | Sem conflito textual |
| #49 | operations/commercial-quotation-20261019 | operations/commercial-invoice-20261019 | Sem conflito textual |
| #48 | design/ibiag-presentation-brand-20261019 | operations/commercial-quotation-20261019 | Sem conflito textual |
| #47 | operations/order-shipment-20261019 | design/ibiag-presentation-brand-20261019 | Sem conflito textual |
| #46 | operations/price-order-draft-20261019 | operations/order-shipment-20261019 | Sem conflito textual |
| #45 | operations/crm-order-link-20261019 | operations/price-order-draft-20261019 | Sem conflito textual |
| #44 | security/stage1-integration-review-20261018 | operations/crm-order-link-20261019 | Sem conflito textual |
| #28 | main | security/stage1-integration-review-20261018 | Sem conflito textual |
| #27 | main | security/discovery-credit-guard-20261018 | Conflito ao reaplicar |
| #26 | main | security/crm-owner-isolation-20261018 | Conflito ao reaplicar |
| #25 | main | security/password-input-validation-20261018 | Conflito ao reaplicar |
| #24 | main | security/task-owner-isolation-20261018 | Conflito ao reaplicar |
| #23 | main | security/bounded-import-uploads-20261018 | Conflito ao reaplicar |
| #21 | main | security/safe-api-errors-20261018 | Conflito ao reaplicar |
| #20 | main | security/unique-session-tokens-20261018 | Conflito ao reaplicar |
| #19 | main | security/login-ip-rate-limit-20261018 | Conflito ao reaplicar |

Os conflitos dos PRs #19–#27 são reaplicações de alterações antigas já compostas e revistas em #28. Não integrar esses PRs individuais por cima do candidato. Todos contêm sobreposições com backend/server.py ou módulos de segurança/interface; o snapshot registra os resultados. #53 compõe textualmente, mas sua execução operacional continua fora desta entrega.

## Pendências e limites

- Homologação ponta a ponta das duas aplicações com identidade e dados reais, após escolher a aplicação a apresentar/usar e definir uma migração explícita. Não há equivalência automática entre os dois bancos.
- Auditoria autenticada do ambiente real, persistência/storage/proxy, contas/perfis, dados legados e recuperação de desastre continuam pendentes; não há certificado de segurança nem liberação para produção.
- O novo guard é otimista e conservador: mudanças em outra coleção podem exigir recarga. Campos operacionais existentes continuam com o modelo de autorização por workspace; não foram introduzidas permissões por setor ou por cliente no ExportHub.
- Saúde é do proprietário. Gabriela como editora continua com os módulos comerciais existentes; não se concedeu acesso real nem enviou convite.
- Validade/versionamento por PDF individual, cobertura de certificado por produto/lote, conteúdo de specs e autenticidade de anexos exigem modelagem/validação adicional. O painel usa somente metadados existentes.
- Trade Intelligence do ExportHub continua como registro manual de pesquisa. O filtro automático aprimorado pertence à aplicação React/Python existente; não há integração nova nem busca paga habilitada.
- A demonstração offline não exercita login, banco, geração documental e gravação pelo navegador; estes dependem de ambiente isolado autenticado e homologação completa. Os testes HTTP e D1 usam identidades sintéticas controladas.
- Publicação, merge na main, ativação de cópias automáticas/serviços/APIs e mudanças na instalação dependem da autorização do usuário.
