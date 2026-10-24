# Apresentação para Gabriela — roteiro fictício

Tempo sugerido: 20–30 minutos. Usar somente ambiente descartável com dados fictícios. Não apresentar o ambiente publicado como atualizado por este PR. Nenhuma instalação real foi alterada.

## Preparação

No IBIAG, entrar como administrador de teste; abrir Gestão → Da empresa ao embarque (/gestao/roteiro). A lista de etapas é um guia da visita, não altera status de pedidos. Todos os cadastros e módulos anteriores continuam disponíveis.

No ExportHub, usar apenas um ambiente isolado de teste com migrações do #59 aplicadas. A importação fica desativada por padrão; os testes automatizados habilitam a flag somente em seus próprios bancos descartáveis. Não habilitar na instalação/produção.

## Cenário comercial

Comprador: Demo Foods Portugal. Contato: Ana Demonstração, ana@example.test. Fornecedor: Demo Brasil. Produto: açaí em pó, 1.000 kg, 40 volumes de 25 kg, tara de 0,20 kg por volume. Incoterm FCA Brasil. Não pressupõe frete internacional nem tributos reais.

Compra fictícia R$ 87,50/kg; outros custos R$ 12,50/kg; margem sobre venda 20%; câmbio fictício R$ 5,00/USD; tributos zerados somente para o ensaio. Compra R$ 87.500; custo total R$ 100.000; venda R$ 125/kg = USD 25/kg; cotação/pedido/Commercial Invoice USD 25.000. Packing List: 1.000 kg líquidos e 1.008 kg brutos. Mudar para 1.500 kg deve resultar em USD 37.500, 60 volumes e 1.512 kg brutos. Quantidade zero deve impedir resultado válido. A página usa computePrice existente, não um cálculo paralelo.

## Percurso nativo IBIAG

1. CRM: criar/abrir empresa fictícia, país e contato; conferir responsável.
2. Fornecedor e produto: escolher a oferta do fornecedor correto, preço/kg, moeda, unidade, MOQ, ficha e certificados fictícios. Dados faltantes devem ser preenchidos explicitamente, sem inferência.
3. Calculadora: selecionar oferta, informar quantidade/custos/câmbio/margem e salvar. Reabrir e conferir a persistência.
4. Usar Criar cotação no cálculo salvo; escolher a mesma empresa, validade e condições; revisar e aprovar internamente.
5. Converter a cotação em um pedido. Repetir a tentativa deve conservar um único vínculo, sem criar pedido duplicado.
6. Criar Commercial Invoice do pedido, conferir origem/revisão e valor; visualizar/baixar PDF privado e aprovar.
7. Criar Packing List do mesmo pedido, conferir volumes/pesos e revisar; visualizar/baixar PDF privado e aprovar.
8. Registrar embarque manual; conferir pedido, transportador fictício, destino e datas.
9. Abrir Operação do dia → dossiê do pedido: conferir cotação, Invoice, Packing List e embarque. Alterar uma origem em teste deve produzir pendência de revisão, sem reescrever documentos anteriores.
10. Abrir qualidade documental e mostrar certificado vencido/ficha sem validade como pendência, nunca como aprovação automática.

O teste de navegador existente já percorre cálculo salvo, cotação, conversão única, documentos privados, Packing List, embarque, dossiê e qualidade com dados sintéticos. Este PR acrescenta a página guiada, simulação, limpeza das marcações e layout móvel ao mesmo percurso.

## Intercâmbio entre as duas aplicações

No Pipeline IBIAG, Exportar empresa para integração baixa somente a empresa selecionada. No ExportHub /integracao, conferir o arquivo; demo/crm-interchange-fixture.json também fornece uma amostra fictícia. Mostrar a prévia sem gravação; no teste isolado, mostrar importação liberada, confirmação de empresa existente e frase literal. Reenviar não deve duplicar. Mudar o arquivo de uma origem já importada exige revisão. Não importar dados reais durante a apresentação.

Esta ponte cobre empresas e contatos. Não apresentar como sincronização de preços, fornecedores, produtos, cotações, pedidos ou PDFs entre MongoDB e D1. Esses módulos têm fluxos nativos próprios, e unificar suas identidades e revisões continua pendente.

## Avaliação de Gabriela

Observar se encontra empresa, oferta, cálculo e documentos sem orientação; se entende onde revisar pendências; se consegue voltar ao pedido pelo dossiê; e se a operação funciona com a tela estreita. Registrar dificuldades e prioridades antes da liberação. Não enviar e-mail/WhatsApp ou acionar pesquisa paga.
