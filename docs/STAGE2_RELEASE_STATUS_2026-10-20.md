# Etapa2 — situação de entrega e liberação

Atualização20/10/2026 UTC. **Implementações em candidato de revisão; etapa2 ainda sem aceite de produção.** Não representa100% do ExportHub ou conclusão da etapa1. Os requisitos históricos completos das conversas “Análise do ExportHub”/“Criar plataforma ExportHub” não foram recuperados: a pesquisa retornou erro das conversas e apenas o manual de outro artefato. Contrato operacional atual está em STAGE2_OPERATIONS.md; este relatório não inventa critérios de aceite históricos.

## Entregas na mesma linha de desenvolvimento

| Entrega | PR | Implementado/testado | Integrado/publicado |
| --- | --- | --- | --- |
| Empresa do CRM →pedido |44| Identidade canônica, vínculo/histórico e proteção de exclusão | Incluído no candidato; sem merge na main/deploy |
| Cálculo salvo →pedido |45| Revisão/memória canônica, rascunho sem conta, stale409 | Incluído no candidato; sem merge/deploy |
| Embarque completo manual |46| Responsável, rota, datas, cinco estados, histórico e estoque/financeiro únicos | Incluído no candidato; sem merge/deploy |
| Visual IBIAG |47| Logo vetorial/foto/cores da apresentação, telas desktop/móvel | Incluído no candidato; sem merge/deploy |
| Cotação e aprovação interna |48| Condições preservadas e conversão única em pedido | Incluído no candidato; sem merge/deploy |
| Commercial Invoice e PDF |49| Memória pública, conferência, aprovação/cancelamento e PDF privado | Incluído no candidato; sem merge/deploy |
| Packing List e PDF |50| Volumes/pesos/embalagem/alocação exata, aprovação e PDF privado | CI39352304799 passou; sem merge/deploy |
| Operação do dia +percurso até recebimento |51| Indicadores/pendências e teste de um único processo até estoque/recebimento | CI39353860272 passou; sem merge/deploy |

Branch candidata operations/operational-dashboard-20261020, SHAbed8008ced775f236b27d0e8c69f2c920e0dd7a3. A composição por branches sequenciais contém os vínculos acima; não equivale a PRs integrados na main. Main foi conferida emc9e2b6508c3f791e0b7ec2ba9863a9a0bf5dae6a. Aplicação publicada permanece na versão anterior. Nenhum serviço de produção foi criado/reiniciado/reconfigurado; não foram ativados novos serviços pagos, provedores ou backups.

## Verificação

Packing List:514 testes backend +56 subtestes, sem skips, MongoDB real descartável e Docker;321 UI, build e Chromium passaram. Evidências em STAGE2_PACKING_LIST_VALIDATION_2026-10-20.md e packing-review-2026-10-20/.

Candidato com painel: local361 backend +48 subtestes/171 skips de ambiente;328 UI/20 suítes e build passaram. **CI39353860272 passou**:532 backend +56 subtestes, sem skips, MongoDB real descartável/Docker;328 UI/20 suítes, build e Chromium. Evidências e telas em STAGE2_OPERATIONS_VALIDATION_2026-10-20.md.

Importação e deduplicação conservadora de CRM/portfólio já existiam; não foram recriadas. Suíte cobre CSV/XLSX, propriedade por usuário, zeros iniciais, repetição sem duplicar registros, limites antes de escrita, arquivos inválidos e permissões, inclusive Mongo descartável. Relatórios financeiros existentes permanecem separados por moeda. Isso não importa nem homologa cadastros comerciais reais.

## O que falta para liberar e fechar o aceite

1. Executar a auditoria autenticada **somente leitura** no backend/banco existente, conforme STAGE1_OPERATOR_HANDOFF.md, sem compartilhar segredos. As ferramentas Railway atuais foram conferidas e não oferecem SSH/terminal/shell; OAuth de metadados não dá acesso de execução ou conexão ao banco privado. Usuário deixou essa ação operacional para20/10, no seu fuso.
2. Comprovar banco efetivamente usado, privilégios, persistência e caminho/montagem de storage. No inventário anterior, o Mongo foi identificado sem volume associado; isso exige validação antes de qualquer restart/migração. Não anexar volume vazio nem reiniciar banco para “resolver” sem preservar os dados. Nenhum backup está autorizado/ativado.
3. Comprovar cadeia de proxy/IP e configuração de confiança real, CORS/segredos/rotas, ingressos corretos e plano de retorno antes de publicar. A pipeline valida código isolado, não a rede de produção. Não fazer merge na main com deploy automático como atalho para obter shell.
4. Homologar login/acessos/recuperação com contas autorizadas de administração e equipe e o processo oportunidade→cotação→pedido→embarque→documentação→recebimento com dados conferidos; validar também importação/deduplicação e relatórios no contexto da operação.
5. Definir critérios ainda não recuperados do escopo original e desenho de arquivo de auditoria permanente. Os históricos limitados atuais não podem ser anunciados como arquivo permanente. Envio/aceite do comprador, assinatura, embarques parciais/devoluções e integrações externas dependem de requisitos/homologação próprios; nenhum foi inferido/ativado.

**Não há uma nova autorização pendente para continuar o código.** Há dependências técnicas de acesso operacional, preservação/persistência e homologação, e escopo histórico não recuperado. Sem essas provas, publicar como sistema pronto contrariaria a exigência do usuário de segurança e validação em produção.
