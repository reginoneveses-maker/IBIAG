# ExportHub — IBIAG

Sistema interno em português do Brasil para cadastrar clientes, oportunidades, cotações, produtos, specs, embarques, tarefas e atividades. Acompanhamento manual: nenhuma conexão com Siscomex, bancos, MAPA, ERPs ou transportadoras.

## Instalar e executar

Requer Node 22.13+ e pnpm conforme package.json.

```sh
npm run install:ci
npm run dev
```

As migrações já estão versionadas; gere novas apenas após alterar db/schema.ts. D1 usa a binding DB e R2 a binding BUCKET, declaradas em .openai/hosting.json. O serviço de hospedagem provisiona os recursos e aplica as migrações. Em desenvolvimento local, aplique as migrações no D1 local com Wrangler antes de testar os cadastros. As APIs exigem identidade autenticada; não exponha o preview ou invente cabeçalhos de identidade em produção. Não são necessárias variáveis de ambiente ou chaves de integrações nesta versão.

## Estrutura

- app/: páginas, layout e rotas HTTP.
- app/api/records/[collection]/: coleções persistidas com revisão otimista.
- app/api/records/transaction/: gravações atômicas entre coleções.
- app/api/crm/files/: PDFs por negociação.
- components/exporthub/crm/: funil, fichas, agenda, relatórios, configuração e importação.
- app/api/specs/: PDFs e metadados.
- app/api/backup/: exportação JSON dos dados.
- components/exporthub/: navegação, dashboard, CRM, calculadora, catálogo, fichas, importação CSV e specs.
- services/: acesso à API, precificação e exportação CSV.
- types/: modelos de setores, tarefas, clientes, embarques, documentos, alertas, atividades, oportunidades e cotações.
- data/: portfólio e definições dos setores. Os antigos exemplos estão preservados como referência de desenvolvimento e não são inseridos no banco.
- db/: esquema, autenticação de APIs e validação Zod.
- drizzle/: migrações e metadados versionados.
- public/products/ e public/portfolio/: fotos e portfólio original.

## Rotas

/ abre o dashboard com dados cadastrados. /produtos abre os 58 itens do portfólio IBIAG. /setores/comercial/crm abre oportunidades. /setores/comercial/precificacao abre a calculadora. /setores/[slug] contém tarefas e atividades dos dez setores: comercial, logistica, documentacao, financeiro, compras, atendimento, inteligencia, juridico, qualidade e ti.

## Como usar

1. Produtos: busque o ingrediente e abra a ficha. Preencha fornecedor, fabricante, origem, embalagem, validade, armazenamento, composição, certificações, prazo e custo em BRL/kg com dados confirmados. Informações ausentes permanecem não informadas. O conteúdo original do portfólio não é reescrito.
2. Specs: envie PDF de até 20 MB indicando o fornecedor e o tipo (Padrão IBIAG ou Original do fornecedor). Baixe os arquivos autenticados na ficha do produto. PDFs são salvos em R2 e metadados em D1. Não há conversão automática para padrão IBIAG.
3. CRM: use as abas Negociações, Empresas, Contatos, Tarefas, Relatórios e Configurações. Cadastre empresas com vários contatos e negócios vinculados. Configure funis, etapas, probabilidades, campos personalizados e responsáveis. Mova negócios arrastando ou pelo seletor de etapa; registre ganhos, perdas com motivo, interações e follow-ups. Arquive e restaure sem apagar o histórico. Use filtros, visões salvas, seleção em lote, modelos de mensagem, metas e relatórios por moeda. Cotações usam a calculadora existente; PDFs da negociação ficam na aba Arquivos.
4. Importação: salve o Excel como CSV UTF-8, com cabeçalhos empresa, pais, contato, email, telefone e produto. A prévia informa empresas e duplicados por empresa + país antes da confirmação. Máximo de 10.000 linhas e 3 MB de CSV; confirme o mapeamento e a prévia. Empresas são deduplicadas por nome e país, contatos por e-mail ou nome e telefone. Criar negociações na importação é opcional. A gravação aceita até 8 MB de dados serializados por requisição. XLSX não é importado diretamente.
5. Precificação: use Produtos ou Serviços do modelo IBIAG, preencha custos indiretos e faturamento mensal, custos diretos, mão de obra, margem, impostos e câmbio. Na modalidade Produtos, escolha fornecedor cadastrado para listar seus produtos e custo. Ou use o portfólio sem fornecedor confirmado ou preenchimento manual. Informe quantidade, custos, moeda, câmbio, margem, despesas e tributos. Salve uma cotação e opcionalmente vincule-a à oportunidade. Reabra ou exporte a memória posteriormente.
6. Embarques: no dashboard cadastre cliente, rota, modal, data, ETA, carga, valor USD e status. Edite manualmente o acompanhamento. Valor exportado corresponde aos embarques marcados como concluídos, não a receita contabilizada ou recebida.
7. Setores: crie tarefas com responsável, cliente e prazo, altere o status, registre atividades e exporte CSV. Dashboard mostra tarefas vencidas e vencendo na data de Fortaleza.
8. Backup: Exportar backup dos dados baixa JSON com coleções, portfólio e índices dos specs e anexos comerciais. A Central de arquivos (/arquivos) permite buscar e baixar specs IBIAG/originais e anexos comerciais/setoriais. Backup com PDFs (/api/backup/complete) gera ZIP autenticado com os dados e todos os PDFs: até 1.000 documentos ou 500 MB. Verifica existência e tamanho antes de iniciar e transmite os arquivos progressivamente. O ZIP não tem senha; proteja a cópia. A restauração é manual; não há backup externo programado.

## Agenda, modelos e automações comerciais

A agenda permite criar, editar, concluir e reabrir tarefas. Exportar ICS gera um arquivo para importar no calendário; não sincroniza automaticamente. Regras configuradas criam follow-ups ao cadastrar ou mover um negócio para a etapa escolhida, evitando duplicar uma tarefa aberta da mesma regra. Elas só executam durante essas ações: não existe processamento agendado em segundo plano.

Modelos substituem dados da empresa e negociação. Botões de e-mail, telefone e WhatsApp abrem seus aplicativos; enviar, receber e registrar automaticamente mensagens não está implementado. Registre as interações manualmente no histórico.

Os relatórios separam moedas e incluem negócios ganhos, taxa de ganho entre fechados, ticket, previsão ponderada, motivos de perda, ciclo com datas conhecidas e metas por responsável. Distribuição por etapa é o estado atual, não uma conversão histórica. Não há conversão cambial automática nem contabilização bancária.

## Calculadora IBIAG (modelo Excel V1)

A tela principal em Comercial → Precificação reproduz as abas Produtos e Serviços de `Precificador Ibiag V1.xlsx`. Não expõe o arquivo original no site. Novos cálculos começam sem faturamento ou câmbio presumidos; o botão **Carregar exemplo do Excel** preenche explicitamente os números demonstrativos e não grava nada. **Novo cálculo** limpa o formulário e preserva cotações salvas.

Produtos: custos indiretos mensais editáveis / faturamento mensal determinam o percentual indireto. Custos diretos e mão de obra (custo/hora × horas) são rateados entre os produtos proporcionalmente às quantidades. Cada linha tem fornecedor, produto/forma, quantidade e custo unitário, em uma unidade comum (`kg` ou `unidades`). Fornecedor cadastrado filtra produtos; o custo cadastrado só é sugerido quando pertence ao mesmo fornecedor.

A fórmula segue o Excel, sem arredondamentos intermediários:

- Base da linha = quantidade × custo unitário + (quantidade / quantidade total) × (custos diretos + mão de obra).
- Preço BRL = base / (1 − percentual indireto) / (1 − margem) / (1 − impostos selecionados).
- Preço convertido = preço BRL / câmbio manual. Preço unitário = preço convertido / quantidade.

Serviços: base = custos específicos + mão de obra própria + mão de obra terceirizada / (1 − impostos da terceirizada). Aplica os mesmos três divisores; preço/hora divide o total pelas horas próprias dedicadas. Custos indiretos e faturamento são compartilhados entre os modos, como os vínculos entre abas do Excel. Margem e impostos dos modos são independentes.

Os impostos da modalidade são percentuais selecionáveis, somados para o divisor final da fórmula. O modelo de origem considera Simples Nacional e não implementa apuração oficial, créditos ou outras bases fiscais. PTAX, frete e impostos são informados manualmente. Números inválidos, denominadores zero/negativos, custos negativos, horas/quantidades inválidas e overflow bloqueiam o cálculo.

**Salvar cotação** guarda em D1 o snapshot versionado `workbookPricing` com os custos, parâmetros e linhas; **Reabrir** recalcula a mesma memória e salvar gera uma nova cotação. O vínculo opcional atualiza o valor/produto da negociação e mantém sua etapa. **Exportar memória CSV** inclui resumo, resultados por item, estrutura de custos, mão de obra e impostos. Serviços, propostas em unidades e múltiplos itens não iniciam automaticamente um embarque de um único produto em kg; a regra é aplicada também no servidor.

Cotações anteriores continuam reabrindo sua fórmula original, com taxas fixas ou percentuais e bases manuais. Não são migradas nem recalculadas silenciosamente. O assistente de pedidos em texto fica em uma seção expansível, usa o cálculo direto de exportação anterior e é identificado como independente do rateio mensal do modelo Excel.

Arquivos: `types/workbook-pricing.ts`, `services/workbook-pricing.ts`, `components/exporthub/WorkbookPricing.tsx`. Validação: `node scripts/test-workbook-pricing.cjs` compara todas as colunas calculadas dos três produtos e os resultados de Serviços com valores salvos no Excel, além de testar rateio, ativação de impostos, câmbio, limites, snapshot e bloqueios de operações. Fixtures contêm apenas os exemplos do arquivo.

## Persistência e acesso

D1 armazena coleções JSON versionadas em blocos de até 160.000 caracteres e metadados dos arquivos; R2 armazena PDFs. APIs exigem conta ChatGPT autenticada; acesso ao site permanece privado. Não há usuários por cargo ou permissões setoriais granulares: todas as contas autorizadas no site têm acesso ao workspace. Não amplie o acesso sem considerar isso. Conflitos de revisão retornam erro 409 sem sobrescrever dados; recarregue antes de refazer a alteração. O CRM normaliza os registros já persistidos, preservando oportunidades e cotações antigas. Dados que estavam apenas no navegador não são migrados automaticamente. Tarefas vinculadas, histórico e regras de follow-up são gravados em lote atômico com verificação de revisão.

## Fotos e dados do portfólio

Os 58 itens foram conferidos contra o PDF original de 2026 (nome, formas, orgânico e MOQ). Disponibilidade orgânica não comprova certificação por produto. Fotos externas são ilustrativas da forma física e não identificam lote, fornecedor ou concentração IBIAG. Imagens inadequadas ou com embalagem de marca foram removidas; itens sem foto adequada mostram pendência. Fontes estão nas fichas e em data/products.json.

## Validar e evoluir

```sh
npx tsc --noEmit
node scripts/test-crm-logic.cjs
npm run build
node scripts/test-crm-http.mjs
```

Os testes HTTP usam banco e arquivos locais isolados e identidade fictícia somente no worker local, sem alterar dados publicados.

Validação realizada: importação e deduplicação de 2.000 empresas e contatos, preservação de cotações, agenda ICS, precificação, gravação acima de 2 MB, transações atômicas e rejeição integral de conflitos, anexos comerciais e specs, TypeScript, build Worker e smoke HTTP com autenticação, cinco coleções, leitura após gravação, rejeição de conflito e dados inválidos, origem de escrita, upload/download de PDF e backup. Rotas e bundles JavaScript responderam corretamente. Teste de cliques em navegador não estava disponível nesta sessão; a faixa “Interface ativa” confirma a montagem do cliente.

Evolução: separar as coleções em tabelas relacionais para volumes maiores; acrescentar auditoria por registro, permissões por cargo, exclusão controlada, restauração automática, operações documentais e financeiras próprias e integrações verificadas. O sistema não substitui processamento fiscal, bancário ou aduaneiro oficial.

## Embalagens, paletização e cotação logística

Na ficha de cada produto, cadastre opções por fornecedor: cidade e endereço de coleta, caixa/tambor/saco, pesos líquido e bruto, medidas externas em cm, conservação e possibilidade de empilhamento. Paletização exige base, tara, orientação confirmada, embalagens por camada, camadas máximas, altura e peso bruto máximos. Não inserimos medidas ou custos de fornecedores sem confirmação.

A calculadora usa embalagens inteiras: arredonda a quantidade de volumes para cima e mostra o excedente. O preço não é ajustado silenciosamente. O botão “Usar quantidade embalada” atualiza os kg cotados. Pallets parciais têm altura calculada pelas camadas ocupadas, mantendo a base cadastrada. Peso bruto inclui a tara de cada pallet. A cubagem usa as medidas externas dos volumes efetivamente enviados. O cadastro de camadas não é um otimizador geométrico de arranjo: confirme a disposição com o fornecedor. Não inclui envoltórios ou folgas adicionais não cadastrados.

Escolha retirada na fábrica, entrega na origem, transporte ao porto de destino ou porta do cliente e informe o local nomeado, destino, carga pronta e prazo. A seleção indica o escopo de custos; não substitui o Incoterm e as condições contratuais. Entrega em terminal não equivale a entrega a bordo. Compare o mesmo escopo e confirme obrigações de seguro, despacho, desembaraço e importação.

Baixe ou copie a solicitação de frete e envie ao despachante/agente de carga. Nenhuma mensagem é enviada pelo sistema. Registre as alternativas recebidas: agente, modal, terminais, serviço/navio/viagem, saída, chegada, cutoff, validade, disponibilidade confirmada pelo agente, referência e custos totais em BRL. Se a fonte fornecer outra moeda, converta e confira os valores antes de registrar. Campo em branco é custo desconhecido; 0 significa inclusão ou ausência de cobrança confirmada.

A comparação destaca o menor total registrado somente entre alternativas com custos exigidos, validade vigente, disponibilidade declarada como confirmada e datas compatíveis. Isso não escolhe automaticamente o melhor porto do mundo, não procura navios, não garante espaço e não reserva carga. Propostas são vinculadas à carga/percurso: alteração de quantidade, embalagem, destino ou carga pronta exige revisão da resposta. “Aplicar custos” substitui frete, seguro, despacho e outros custos da calculadora; depois salve a cotação no CRM. A cotação guarda uma cópia da embalagem, do estudo e da alternativa aplicada. Cotações antigas continuam funcionando sem estudo logístico.

Peso volumétrico é opcional com divisor fornecido pela transportadora; o maior entre peso real e volumétrico é indicativo, sem mínimos, arredondamentos ou regras específicas do serviço. Para marítimo LCL/FCL, registre a proposta real do agente: não extrapolamos uma tarifa por kg ou m³.

## Conexões com prestadores — ainda não implementadas

`FreightProviderAdapter` em services/logistics.ts define o ponto de extensão de consulta. Não existem adaptadores ativos, APIs simuladas, credenciais, chamadas externas ou pesquisas automáticas de navios nesta versão.

- Despachante/agente: inicialmente solicitação padronizada e registro da resposta. Próxima etapa pode usar e-mail autorizado ou API do prestador, preservando a referência, validade e escopo.
- DHL Express: conta comercial ativa e autorização no portal MyDHL API; acesso de testes e produção, consulta de serviços, tarifas de conta e validação de endereços. Não confundir Express com serviços marítimos DHL Global Forwarding.
- FedEx: conta e acesso aprovado no portal de desenvolvedores, configuração do produto compatível, tarifas e prazos. Cotação de tarifa não comprova disponibilidade; cargas e serviços têm APIs/regras próprias.
- Marítimo: agente/consolidador e armadores com acesso autorizado a programação e tarifas. Programação de navio não comprova espaço, preço ou aceitação da carga. Consolidar trecho terrestre, terminal, LCL/FCL, transbordos, seguros, taxas, cutoff e entrega.

Fontes oficiais: https://developer.dhl.com/api-reference/dhl-express-mydhl-api ; https://developer.fedex.com/api/pt-br/catalog/rate/docs.html ; https://developer.maersk.com/api-catalogue/ocean-commercial-schedules/Learn-more ; https://academy.iccwbo.org/incoterms/article/place-of-delivery-risk-transfer-global-trade-contracts/ .

Os campos de custos exigidos consideram seguro em CIF/CIP, desembaraço e tributos em DDP e despacho em FCA na fábrica. Isso é uma checagem de preenchimento, não uma validação completa das obrigações contratuais ou cobertura de seguro. Modal aéreo/rodoviário com FOB/CFR/CIF fica inelegível na comparação.

## Assistente de cotações por pedido em texto

Em Comercial → Precificação, expanda Assistente de cotações e logística em texto. A seção aceita pedidos como “Cota 300 kg de pó de açaí saindo da fábrica de Belém para Nuremberg na Alemanha. Preço no porto de origem e no porto de destino”. Clique em Interpretar pedido. O leitor é local, baseado em palavras-chave (kg/toneladas, saindo/partindo, para/pra e porto de origem/destino); não é um chatbot com modelo de linguagem conectado. Corrija no formulário frases que ele não identificar.

Confirme a forma exata do ingrediente: extrato em pó e liofilizado são produtos diferentes. O sistema sugere candidatos e não resolve essa ambiguidade sem você. Embalagem, origem, fornecedor e custo vêm do cadastro; complete endereço e peso/medidas primeiro. Nenhum dado de fornecedor é inventado. As caixas são inteiras e sobra exige ajuste explícito da quantidade.

Informe carga pronta, destino e condições comerciais. Respostas de frete já salvas podem ser reutilizadas apenas para a mesma carga, embalagem, fornecedor, destino e data, com referência e validade vigentes. O menor total válido registrado é carregado; confirme seus custos e condições. Se não existir resposta compatível, preencha os valores e dados confirmados do agente. Não há busca de navios, portos ou tarifas externas nesta versão.

Gerar propostas monta os cenários solicitados numa única ação: FCA/FOB na origem e CFR/CIF no destino, com portos/terminais nomeados. Custos de entrega a bordo precisam de confirmação para FOB/CFR/CIF. CIF exige seguro informado; cobertura e obrigações contratuais precisam de revisão. Câmbio, margem, comissões e tributos são os valores informados, sem taxas oficiais automáticas. Valores originais em outra moeda precisam ser convertidos e conferidos em BRL antes do registro de frete.

Salvar cenários registra cotações na coleção comercial e no histórico da negociação, preservando o valor do negócio até escolher a proposta aceita. Baixar propostas gera HTML independente com os preços de venda e dados da carga, sem revelar margem ou custo de compra. Abra o arquivo e use Imprimir / salvar como PDF. É um rascunho para revisão; condições de pagamento e cobertura de seguro devem ser confirmadas antes do envio. O sistema não envia mensagens nem reserva embarques.

Nuremberg ou outra cidade é um destino de referência. Os portos são os informados na proposta recebida; não há seleção geográfica automática. As propostas ao porto de destino excluem importação, taxas locais não incluídas no frete e transporte até o endereço do cliente. Esta primeira versão cobre os dois cenários portuários; retirada na fábrica e porta do cliente continuam na calculadora logística detalhada.

Testes adicionais: interpretação de pedido e toneladas, ambiguidade de formas, geração conjunta de cenários, quantidades/embalagens, preço e custos por trecho, validade de frete, exigência de dados confirmados, rejeição de custos negativos e escape do documento exportado.

## Preparação antes do frete

O assistente calcula o plano de embalagem e preço-base antes de receber transporte, sem exigir porto, navio, datas ou tarifa para essa preparação. A leitura usa as opções cadastradas da origem e prefere o fornecedor principal; a recomendação minimiza excedente de kg, depois cubagem e peso bruto. Não é uma otimização de custo de embalagem: tarifas e disposição física precisam ser confirmadas.

Na ficha do produto, registre custo BRL/kg, aliases usados nos pedidos, moeda, câmbio, margem e despesas percentuais padrão. O câmbio salvo é manual e precisa estar vigente. Formas ambíguas continuam exigindo confirmação; um alias único permite associar o pedido ao produto certo. Com todos esses dados salvos, interpretar o pedido já prepara a carga e o preço-base. Campos ausentes são exibidos como pendência.

O painel “Cotação preparada · frete pendente” mostra plano, medidas dos volumes, peso bruto, cubagem, preço-base por kg e total. Esse preço inclui produto, margem, comissões e tributos selecionados, mas não custos logísticos. Não é uma oferta final FCA/FOB/CFR/CIF e não é salvo nem exportado como proposta comercial completa. Recebendo os custos confirmados (transporte, terminal, despacho e seguro quando aplicável), atualizar gera os cenários com frete. O modelo visual da proposta do usuário aguarda o documento de referência para adaptação.

## Recuperação e validação operacional

A ficha de produto distingue carregamento e erro, permite tentar novamente e valida custo, câmbio, moeda e percentuais antes de salvar. Embalagens salvas em formato inválido ficam sinalizadas e preservadas até revisão. Gravações comerciais têm proteção contra cliques repetidos.

Quando uma API retorna sessão ausente, a interface oferece “Entrar novamente” por navegação direta com ChatGPT. A autenticação continua exigindo identidade fornecida pelo servidor; e-mail isolado não autoriza acesso. Respostas incompletas e falhas no upload mostram mensagens de recuperação, sem apagar os campos preenchidos. Conflitos entre janelas continuam exigindo recarregar os registros antes de gravar.

## Áreas setoriais operacionais

Os dez setores têm registros próprios com formulário, busca, filtros, indicadores, histórico, arquivamento e restauração. A coleção autenticada `sectorRecords` preserva vínculos por ID com produtos, negociações e embarques. Tarefas podem ter `recordId`; arquivos PDF por processo usam D1 `sector_files` e R2 `sector/`, com download privado. Novas migrações Drizzle são aplicadas pelo fluxo de publicação. Não há backfill ou inserção de dados fictícios nos registros do usuário.

Logística permite cadastrar/editar embarques no próprio setor. Financeiro e compras mostram valores por moeda e tipo, sem somar moedas diferentes. O dashboard inclui documentos pendentes e prioridades dos processos. `/ajuda` contém o manual de uso. Inteligência armazena estudos/fontes e empresas informadas; não executa prospecção externa. Controles jurídicos, de qualidade e compliance dependem de revisão humana e não substituem sistemas oficiais.

Validação: `npx tsc --noEmit`, `node scripts/test-crm-logic.cjs`, build pelo helper Sites e `node scripts/test-crm-http.mjs` após build. O teste HTTP utiliza banco e bucket locais isolados, incluindo CRUD de cada setor, anexos PDF, revisão e conflitos.

## Identidade visual IBIAG

Logo original extraído sem redesenho do PDF de portfólio enviado: `public/brand/ibiag-logo.png`. Azul RGB 16/68/150 (`#104496`) e amarelo-lima RGB 202/213/27 (`#CAD51B`), com azul profundo e fundos claros para a interface. Cores de risco e atenção continuam semânticas. Propostas HTML incorporam o logo para funcionar sem conexão.

## Cotação → operação integrada

Na lista de cotações salvas, Criar operação solicita confirmação da proposta escolhida e prazos. `POST /api/operations` lê a cotação no servidor, valida a confirmação, compara quantidade/valor/moeda e grava cinco coleções atomicamente: embarque, quatro processos (coordenação logística, Invoice, Packing List e previsão a receber), quatro tarefas, vínculo/histórico comercial e atividade. A cotação guarda `operationId`; repetição é recusada com o vínculo existente. Nenhuma etapa é marcada como ganha, paga, reservada ou emitida automaticamente. Não há emissão oficial de documentos.

Embarques suportam BRL/USD/EUR. Registros antigos sem moeda preservam a interpretação anterior USD. Totais e gráfico são calculados por moeda, sem conversão automática. O detalhe de embarque reúne links de cotação, negociação, produto e dossiê. O manual traz o roteiro de apresentação com dados anonimizados; segurança empresarial e integrações externas continuam etapas separadas.

### Central de arquivos e histórico básico

A migração 0006 acrescenta audit_events para solicitações de downloads e exportações. /api/audit retorna as últimas 100 solicitações para usuários autorizados. O log não confirma a conclusão da transferência, não cobre todas as alterações nem é uma auditoria independente ou imutável. Falha ao registrar bloqueia a exportação/download. O ZIP usa CRC32, nomes UTF-8 e verificação de tamanho; a validação HTTP abre o ZIP com Python zipfile e compara o hash dos PDFs originais. Nenhum dado do usuário é inserido ou alterado pelo teste isolado.

### Proteção contra telas com dados desatualizados

Cada tela que grava registros cria sua própria sessão com `createRecordSession()`. Leituras e gravações de outra tela não atualizam as revisões usadas por um formulário antigo. Um conflito mantém os dados gravados e retorna orientação de recarga; não há tentativa automática de sobrescrever ou mesclar. Gravar sem carregar uma coleção primeiro é bloqueado. Teste de regressão: `node scripts/test-workspace-sessions.cjs`, com dois editores, uma tela observadora, conflitos em transações e recarga explícita.

As requisições de registros têm limite de 60 segundos e mensagens para falha de conexão. Uma resposta incompleta ou revisão inválida não é aceita como confirmação de gravação. Falhas de renderização oferecem tentar novamente, início e manual; a recuperação pode perder campos ainda não salvos. Arquivos PDF mantêm seu fluxo próprio, sem esse limite de registros.


### Upload de vários PDFs
Specs de produtos, anexos de negociações e processos aceitam até 20 PDFs por seleção, 20 MB por arquivo e 100 MB no total. Selecione arquivos individuais; pastas e ZIP não são importados. Todos os PDFs da seleção usam a mesma ficha e, nos specs, o mesmo fornecedor e tipo (IBIAG ou original). Para outro produto ou tipo, faça outra seleção. O envio é sequencial, com limite de cinco minutos por arquivo e resultado individual. Parar após este arquivo preserva os confirmados e deixa os próximos pendentes. Mantenha a tela aberta; sair interrompe a fila depois do arquivo em andamento. Falhas de conexão ou confirmações incompletas ficam como Verificar: atualize a lista antes de reenviar, pois o servidor pode ter salvo. Arquivos confirmados ou incertos não são reenviados automaticamente.
Validação específica: `node scripts/test-pdf-upload.cjs`, além dos testes HTTP isolados de specs IBIAG/originais e backup integral.


### Segurança e recuperação — 12/10/2026
O acesso do Site continua privado e restrito ao proprietário. A tabela workspace_members vincula a conta ao ID estável do Site. O e-mail inicial do proprietário, confirmado na política de acesso, só é usado para o primeiro vínculo; outro ID com o mesmo e-mail não substitui o vínculo. O cadastro é feito no primeiro acesso autorizado após a migração 0007. A identidade depende dos cabeçalhos confiáveis do gateway Sites; não exponha o Worker diretamente com cabeçalhos arbitrários.
Permissões no servidor: owner lê/grava/exporta/administra; editor lê/grava; viewer lê. Não existe ainda interface de convites/gestão por setor. Nenhum colega foi adicionado. Alterar acesso no Site não concede automaticamente associação no banco.
As respostas usam nosniff, no-referrer, restrição de câmera/microfone/localização e CSP para bloquear plugins HTML, alteração de base e envio de formulário a outro domínio. Não é uma CSP completa contra XSS; scripts inline do framework continuam permitidos. Todas as APIs recebem private/no-store. Escritas rejeitam Origin diferente e Sec-Fetch-Site cross-site; ausência de ambos continua permitida para clientes internos autenticados.
Gravações de coleções e uploads geram audit_events dentro da mesma transação D1 dos dados/metadados. Conflitos não geram evento de sucesso. O histórico identifica coleção/arquivo e ator, sem copiar conteúdo confidencial. Não é imutável e não descreve cada campo alterado.
Antes de cada escrita nas coleções existentes, uma cópia JSON é gravada no R2 sob safety-backups/. Se falhar, a escrita não acontece. Cópias de lotes são por coleção; não representam um backup global consistente. Conflitos podem gerar cópias extras. Não há agendamento, retenção com exclusão, cópia fora do provedor nem inclusão automática dos PDFs/índices/permissões/auditoria. O crescimento de armazenamento deve ser acompanhado. Central de arquivos lista/baixa as cópias, verifica SHA-256 e exige owner. Nunca reenviar um snapshot direto como backup completo.
Recuperação: conferir formato, coleção, dados e data; baixar backup completo do estado atual; validar registros pelo schema; aplicar a coleção com revisão atual por procedimento técnico autorizado. O teste HTTP restaura uma coleção a partir do snapshot em banco isolado e confirma igualdade; não testa desastre do provedor nem restauração integral em produção.
Pendências: auditoria independente, antivírus/quarentena por serviço escolhido, backup completo periódico em destino independente com retenção e exercício integral de recuperação, gestão de membros por interface/setor, avaliação de contratos de privacidade/retencão do provedor e MFA na conta pessoal. Não declarar conformidade LGPD, certificação ou ausência de risco.


### Variações do portfólio
`data/product-catalog.ts` reúne as linhas originais e as opções explicitadas em `data/product-variants.json`. O catálogo e os seletores usam as variações ativas. Identificadores originais de grupos são preservados para registros e documentos anteriores; os links para a ficha geral continuam acessíveis pelas variações. Não copiamos automaticamente preços, fornecedores, embalagens ou specs dos grupos para seus filhos. Os novos IDs possuem fichas próprias na coleção products e specs próprios. As categorias acompanham a forma selecionada. Faixas 4–6%, 8 a 10% e corte 5/10 são preservadas. As colunas agregadas NFC/purê e clarificado/concentrado não comprovam opções individuais: continuam rotuladas conjuntamente até confirmação por specs. Opção orgânica continua como atributo, sem duplicar itens convencional/orgânico ou atribuir certificações do rodapé.


### Fotos por forma do ingrediente
A revisão fotográfica utiliza arquivos externos baixados sem gerar imagens sintéticas. `data/product-photos.json` mantém a origem e a descrição visual; `public/products/real-2026` contém 38 novos arquivos. Há fotos em 77 dos 88 cards. A mesma aparência pode ser compartilhada entre teores do mesmo ingrediente/forma; a fotografia não comprova teor, concentração, processo, fornecedor, lote ou certificação. Imagens de bebidas servidas são identificadas como apresentação ilustrativa, não como comprovação de concentração industrial. Não usamos embalagens de marcas de terceiros. Origem da foto não cadastra fornecedor nem transfere informações de saúde/certificações para o produto. Os grupos de apresentações diferentes exigem uma associação explícita, evitando aplicar foto de cajá a cajá-umbu, de pó a casca ou de mate verde ao tostado. Alguns fornecedores usam marcas d'água na própria foto do ingrediente; a autoria continua identificada.
Pendentes: açaí soft mix UHT, babaçu, cajá-umbu, polpa integral de coco verde, água de coco clarificada/concentrada, graviola cortada, complexo de café verde, jambu em pó/cortado e limão nas duas apresentações. Imagens disponíveis foram rejeitadas quando mostravam embalagem, produto/espécie diferente, apresentação incompatível ou não puderam ser obtidas. Fotos do fornecedor/produção são preferíveis para fechar essas pendências.


## Cadastro de produto para preparar cotações

Produtos → Ver ficha do produto → Informações operacionais contém seções de produto/fornecedor/disponibilidade, preço e condições, comissão, transporte, custos além do frete, impostos e embalagens/paletização. O cadastro é privado em `products`; cada variação conserva seu próprio ID e ficha. Dados ausentes podem ser salvos como pendentes; embalagens precisam de pesos/medidas válidos para salvar. Opções recém-criadas continuam visíveis durante o preenchimento, mesmo incompletas, e não desaparecem na validação.

- Preço por kg com moeda e câmbio do fornecedor, validade do preço, MOQ, prazo em dias, forma/processamento, código, contato e endereço de coleta. Preços anteriores sem moeda mantêm BRL. Condições e descontos por quantidade são observações para conferência; não há seleção automática de uma tabela de descontos textual.
- `quoteSettings` versionado: revenda ou comissionamento, comissão a pagar/receber, percentual, base produto/receita, inclusão e condições de pagamento; modais permitidos, modal padrão, Incoterm de referência e porto preferido; taxas, despacho, seguro e custos de destino com base fixa/kg/embalagem/pallet; tributos padrão com as bases do cálculo direto.
- Cada embalagem tem pesos líquido/bruto, dimensões externas, materiais, conservação/faixa de temperatura, restrições, endereço, empilhabilidade e informação sobre fracionamento. Custo de embalagem e de pallet/proteção pode estar incluído, ser extra ou permanecer desconhecido. Paletização mantém camadas, embalagens por camada, limites de altura/peso e tara. A estimativa usa embalagens fechadas e pallets completos/parciais; autorização de fracionamento é informativa e não inventa pesos/medidas de uma embalagem aberta.

O assistente carrega preço convertido, margem, despesas, comissão, tributos, origem/porto/modal padrão e custos não relacionados a frete. Comissão a pagar só é acrescida quando não estiver incluída; a receber é um registro interno sem acréscimo ao preço. Comissionamento usa margem de revenda zero. Preço vencido, MOQ insuficiente, câmbio ausente, modal incompatível e preço de fornecedor diferente bloqueiam a preparação/finalização pertinente. Comissão, embalagem e pallet adicionais entram no preço salvo, preservando a memória de custos aplicada.

Os subtotais por cenário incluem os custos não relacionados a transporte já cadastrados ou informados; frete e custos ainda desconhecidos são destacados como pendências. Campos de frete/disponibilidade/portos/datas permanecem manuais, sem consulta a transportadoras. Os cenários automáticos deste assistente são FCA/FOB e CFR/CIF; os demais Incoterms são cadastrados como referência e a tentativa de finalizar um pedido com essas condições é bloqueada. O leitor reconhece teores explícitos e não confunde suco com pó; se extrato/liofilizado ou fornecedor continuar ambíguo, pede confirmação. O assistente mantém o cálculo direto; não transforma silenciosamente seus tributos/bases no modelo mensal do Excel.

Teste: `node scripts/test-product-quote.cjs` cobre cadastro→cotação, 1.000 kg, embalagens/pallets/peso/cubagem, comissão sem duplicação, câmbio, validade, MOQ, custos desconhecidos, bases de rateio, variantes, modal, persistência validada e valores com frete confirmado. Os snapshots de cotações anteriores continuam preservados.

## Motor de preço do assistente (unificado com a planilha)

`services/unified-pricing.ts` calcula as cotações do assistente com a fórmula sequencial da planilha IBIAG, compartilhada com o precificador (`applyWorkbookFormula` em `services/workbook-pricing.ts`).

- Base = produto + frete + seguro + documentos + outros custos + tributos de custo (valor fixo ou % sobre produto/operação/base informada, quando marcados para somar ao preço).
- Preço = base ÷ (1 − indiretos) ÷ (1 − margem) ÷ (1 − tributos sobre o preço − comissões/despesas). A margem incide sobre o preço antes de tributos, como na planilha; no motor anterior incidia sobre o preço final, então os mesmos números agora geram preços um pouco maiores.
- Os custos indiretos vêm do padrão da empresa (Precificador → Salvar como padrão da empresa), salvo em `commercial.pricingProfile`. Sem ele, o assistente mostra só uma prévia sinalizada e bloqueia a proposta final.
- Cada cotação nova guarda `pricingModel` (taxas usadas). Cotações antigas não são recalculadas; `calculatePrice` continua disponível para a calculadora legada.

Teste: `NODE_PATH=$PWD/node_modules node scripts/test-unified-pricing.cjs`.
