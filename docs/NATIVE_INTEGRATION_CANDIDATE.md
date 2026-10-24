# Integração nativa de cotação — candidata em desenvolvimento, 24/10/2026

## Implementado

A rota /gestao/cotacao-integrada usa a sessão IBIAG/FastAPI existente. O perfil explícito commercial-operator-v1 permite operar sem papel admin, com menu filtrado; não concede usuários, backups, exclusões, cadastro genérico ou financeiro. Ativação/revogação só por administrador com confirmação e invalidação das sessões. Nenhuma conta real foi criada ou alterada. Reutiliza QuoteCompletion e QuoteSummary do ExportHub e o proposalHTML IBIAG original, por empacotamento reproduzível; não depende de outro login, servidor Next, D1 ou importação do CRM para o novo percurso.

Clientes/contatos vêm de leads; ingredientes, fornecedores e preços vêm de products, suppliers e product_offers com seus IDs originais. Busca limitada com aviso de mais resultados; referências duplicadas/ausentes são sinalizadas sem exclusão. Ofertas em outra unidade são sinalizadas: o precificador reutilizado opera em kg.

A cotação aceita pendências e valores manuais, recalcula pelo motor sequencial existente e gera a proposta IBIAG para visualização/PDF. O servidor executa o mesmo motor compilado, recebe o estado confirmado e calcula os valores; não aceita totais enviados pelo navegador. O executor Node é fixo, sem shell, com JSON limitado, timeout e concorrência limitada.

Rascunhos e cotações novas ficam em coleções MongoDB integradas, vinculados ao usuário; não modificam o CRM ou o catálogo ao salvar. Rascunhos têm versão própria, pedido idempotente e rejeição de conflito. Valores revisados são imutáveis. Consultar o workspace e salvar não requer D1.

Atualizar ficha exige duas confirmações na tela; API exige confirmação, revisão da origem e whitelist. Atualiza o preço da oferta canônica e o perfil comercial da oferta, com registro do valor anterior; mantém PDFs, certificados e demais campos. Nenhuma atualização foi aplicada a dados reais durante o desenvolvimento.

Continuar uma proposta USD cria um rascunho no módulo nativo de cotações, preservando o snapshot e vínculo de origem, sem aprovação ou pedido automáticos. O mesmo comando retorna a mesma cotação. Aprovação, conversão única em pedido, Commercial Invoice, Packing List, PDFs privados, embarques, histórico e recebimento usam os serviços nativos existentes.

## Testes

- Oito testes HTTP locais passaram: leitura direta/sem mutação, sessão/permissões, rascunho incompleto/reabertura/CAS/idempotência/isolamento, cálculo no servidor/snapshot, atualização confirmada/conflito/preservação dos documentos, cotação→aprovação→pedido, BRL/EUR sem conversão USD inventada e referências duplicadas preservadas.
- Inclui percurso HTTP completo até Invoice/Packing List/PDF/embarque/recebimento. Repetição em MongoDB real descartável integra a CI; testes locais utilizaram mongomock.
- Chromium com a página integrada real e API FastAPI sintética: fornecedor→ingrediente→cliente, preço automático, rascunho, encerramento completo do Chromium e recuperação em outro processo, conclusão manual, proposta IBIAG salva, continuidade para aprovação e tela 390px sem overflow. Capturas inspecionadas.
- Testes adicionais do perfil: login preserva papel user, operador percorre cotação→pedido→Invoice/Packing/PDF→embarque; somente administrador registra recebimento financeiro. Usuários/backups/exclusões/financeiro negados; convite não é criado; concessão/revogação invalida sessões. 19 testes locais mais recentes passaram (19 casos com Mongo real ficaram para CI).
- TypeScript e 12 regressões da cotação manual passaram localmente.
- CI completa é obrigatória no commit final; não atribuir a esta versão a aprovação do commit anterior.

## Arquivos principais

backend/commercial_access.py; backend/test_commercial_profile.py; frontend/src/components/CommercialOnly.*; backend/integrated_workspace.py; backend/generated/quote-engine.cjs; backend/server.py; backend/Dockerfile; backend/test_integrated_workspace.py; backend/test_integrated_journey.py; backend/integrated_browser_fixture.py.
exporthub/integration/*; exporthub/scripts/build-native-integration.cjs; exporthub/scripts/test-native-integration-ui.cjs; exporthub/services/quote-completion.ts; exporthub/components/exporthub/logistics/QuoteCompletion.tsx.
frontend/src/integration/quote-components.js; frontend/src/pages/gestao/IntegratedQuotation.*; frontend/src/App.js; frontend/src/components/Layout.jsx; .github/workflows/test.yml.

Artefatos gerados são versionados para o build da interface e da API; a CI recompila e verifica igualdade com os fontes. Não editar os artefatos manualmente.

## Demonstração sintética

1. Entrar com operador comercial fictício do ambiente de teste. Abrir Criar cotação IBIAG.
2. Buscar cliente do CRM. Filtrar fornecedor e carregar seu ingrediente.
3. Informar 1000 kg, custo BRL 17,50/kg, margem 20%, câmbio BRL 5/USD; confirmar zero comissões e indiretos somente no cenário fictício.
4. Confirmar embalagem incluída, local EXW e valores. Resultado USD 4,375/kg e USD 4.375,00. Campos opcionais continuam a confirmar.
5. Salvar rascunho incompleto, fechar navegador, abrir nova sessão, retomar e revisar preços.
6. Salvar cotação revisada. Visualizar proposta original IBIAG e imprimir/salvar PDF.
7. Preencher validade, pagamento e entrega para preparar aprovação. Abrir Cotações, aprovar internamente e converter uma vez em pedido.
8. Revisar Invoice e Packing List com dados físicos reais do cenário, gerar PDFs privados, registrar etapas de embarque e consultar dossiê/histórico.
9. Testar conflito em outra janela e atualização cadastral somente no banco sintético.

## Pendências reais — não declarar pronto

- A nova jornada principal é nativa e usa uma identidade. O histórico já existente no ExportHub/D1, seus módulos paralelos e documentos R2 permanecem preservados, mas não foram conciliados/migrados para MongoDB. Ainda não é a unificação de todo o acervo.
- O pedido/documentos legados trabalham em USD. BRL/EUR geram propostas, mas exigem nova cotação USD com câmbio confirmado para continuidade. Não há conversão silenciosa.
- Preços conhecidos são carregados. Embalagens/paletização descritivas não viram medidas inventadas; dependem de perfil estruturado confirmado. Outros padrões comerciais não configurados permanecem manuais.
- Perfil comercial de menor privilégio implementado e testado; ativação na conta definitiva e homologação da matriz de acesso por Gabriela seguem pendentes. O perfil permite consultar/operação comercial global, mas mantém o CRM completo sob as regras de proprietário existentes; a seleção para cotação expõe só campos comerciais de contato.
- Hospedagem pública, TLS, domínio, segredos, volume persistente, recuperação real e homologação de Gabriela permanecem sem validação no destino.
- Migração histórica: preparar conciliação por IDs, relatório de diferenças e revisão humana em cópia isolada; recuperar ambos os acervos e objetos privados em ensaio antes de propor qualquer execução real. Nenhuma migração foi acionada.
- Não foram iniciados serviços, contêineres locais, backups automáticos ou APIs pagas; nenhum merge ou deploy.

PR #60 continua em rascunho, branch improvements/crm-import-20261024, base #59 → #58. Os heads dos PRs abertos permaneceram nos commits revisados no início desta retomada; Claude é ancestral preservado. Reaplicar #19–#27 sobre #28 continua indevido por sobreposição; #53 segue separado e não executado.
