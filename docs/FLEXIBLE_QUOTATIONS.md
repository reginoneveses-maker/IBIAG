# Cotação com cadastro incompleto

Implementação isolada no PR #60. Esta regra substitui o impedimento de concluir propostas por falta de cadastro. Os módulos, a fórmula sequencial, o logo, as cores e o template proposalHTML do Claude são preservados. Não foi publicada ou aplicada a dados reais.

## Fluxo para Gabriela

A tela de Precificação agora oferece Concluir cotação · preencher pendências aqui. Escolha um ingrediente para carregar o cadastro ou informe produto/fornecedor manualmente. O assistente em texto também oferece Continuar manualmente sem sair desta cotação, transferindo os campos existentes sem limpar o formulário de origem.

Campos carregados e manuais são identificados. Alterações manuais são preservadas ao carregar outro cadastro, com aviso de revisão. Quantidade, preço em BRL/kg, moeda/câmbio, margem, despesas, rateio indireto e custos necessários ao Incoterm precisam de valor ou confirmação explícita. Zero é aceito quando confirmado; vazio nunca vira zero em um custo essencial. Rateio indireto pode ser informado na cotação sem configurar faturamento mensal da empresa.

Preço vencido, MOQ, prazo e condições comerciais ausentes produzem avisos. Embalagens, medidas e paletização desconhecidas aparecem como a confirmar; não produzem pesos/cubagem fictícios. Custos de embalagem/pallet devem ser confirmados como incluídos ou informados como adicional total. Custos logísticos devem corresponder ao cenário escolhido; CIF inclui seguro e DAP inclui destino/endereço e transporte final. Informações inválidas ainda precisam ser corrigidas; não se trata de autorizar números inconsistentes.

O recálculo usa calculateUnifiedPrice existente e ocorre a cada alteração. Dados cadastrados de comissão, embalagem e custos por quantidade são carregados e escalados; correção manual prevalece. Na nova conclusão manual, preço unitário usa quatro casas e total duas casas sobre quantidade × preço unitário; a regra fica registrada no snapshot. Cotações antigas não são recalculadas.

## Rascunhos e atualização opcional

Salvar rascunho incompleto / Salvar e continuar depois persiste strings vazias e campos parciais em commercial.quoteDrafts. Não exige uma cotação calculável. Retomar rascunho carrega os campos e exige nova revisão de atualidade. Salve antes de sair; a consulta à ficha pode abrir outra aba, mantendo a cotação preenchida. Não há promessa de autosave se a aba for fechada sem salvar.

Limite de 100 rascunhos no workspace, 150.000 caracteres por memória. Sem exclusão/truncamento automático. A validação aceita formulário incompleto mas rejeita estrutura inválida, IDs repetidos e excesso de tamanho. Permissões e conflito de revisão são os mesmos do módulo comercial. São rascunhos do workspace, não um cofre privado por usuário.

Por padrão, preenchimento manual vale somente nesta cotação. Para atualizar também a ficha, é necessário selecionar essa opção e confirmar novamente. Atualiza somente campos explicitamente oferecidos: fornecedor, preço BRL/kg, MOQ/prazo/validade preenchidos e embalagem válida. Outros dados, produtos, PDFs e certificados são preservados. Alteração concorrente da ficha impede sobrescrita e conserva o formulário. Não atualiza automaticamente uma base global de fornecedores separada ou o outro aplicativo MongoDB.

## Proposta e memória aprovada

O template existente recebe os dados revisados e continua com o logo e a identidade IBIAG. Foram adaptados valores desconhecidos, termos informados, precisão por kg e comportamento em tela estreita; o modelo não foi reconstruído. Permite prévia em iframe isolado, baixar o HTML existente e imprimir/salvar PDF pelo navegador. O teste gera um PDF real em Chromium a partir do mesmo HTML. Nenhum envio de e-mail/WhatsApp é feito.

Cada conclusão cria novo ID. completionReview registra fonte automática/manual, valores de origem, formulário da aprovação, pendências, data e regra de arredondamento. O servidor reconcilia os valores de novas cotações com a fórmula. Cotações revisadas não podem ter a memória/valores removidos ou substituídos por APIs genéricas; vínculo operacional continua permitido. Reabrir mostra o snapshot sem recalcular e permite visualizar/PDF novamente.

## Verificação

12 testes de regras/HTTP/SQLite: cadastro ausente, opcionais, zero versus vazio, câmbio/custos, preço vencido/MOQ, impostos incompletos, comissão e embalagem escaladas, preservação manual, template/escape, rascunhos, permissões, conflito e valores imutáveis.

Teste Chromium sobre Commercial e API SQLite reais em fixture: rascunho/reload/retomada; recálculo; nenhuma atualização cadastral por padrão; confirmação extra; preservação do snapshot; proposta original; PDF real; layout 390px; passagem do assistente para preenchimento manual sem perder valores. TypeScript e regressões de CRM/precificação/documentos são mantidos no workflow. Resultados finais devem ser conferidos no SHA do PR.

## Limites preservados

Produção e dados reais não foram alterados. Não há merge, deploy, custos externos ou backups automáticos. A integração entre aplicações continua limitada às empresas/contatos desta etapa; identidade, preços, produtos, fornecedores e documentos entre MongoDB e D1 ainda exigem integração posterior. A nova regra não representa homologação real pela Gabriela.
