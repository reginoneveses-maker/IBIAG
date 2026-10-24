# Continuidade comercial em USD, BRL e EUR

Continuação isolada do PR #60 em 24/10/2026. Não houve migração ou alteração de dados reais.

## Comportamento implementado

A moeda escolhida na calculadora agora acompanha a cotação revisada, a aprovação interna, o pedido, o recebível e a Commercial Invoice. Não há consulta de câmbio, conversão inferida ou alteração da proposta IBIAG existente. Packing List continua sem preços e reutiliza as verificações de integridade do pedido.

Registros USD anteriores mantêm total_usd e o mesmo formato do snapshot público de invoice, para não invalidar hashes de documentos aprovados. Novas operações BRL/EUR usam currency e total_amount; total_usd permanece zero, nunca recebe um valor em reais ou euros. Não foi executada atualização de registros antigos.

A moeda do pedido salvo é imutável, inclusive depois de recebimento e embarque. Uma origem de cálculo USD continua USD. Um pedido criado de cotação revisada recebe moeda e valores do servidor, ignorando tentativa de substituir o snapshot pelo cliente. Clientes antigos que omitam os novos campos preservam a moeda e o total armazenados nas atualizações.

Pedidos, cotações e invoices mostram a moeda original; o cabeçalho dos pedidos apresenta totais separados por moeda. Trocar a moeda de um pedido manual novo limpa preços e não reaproveita o preço USD da oferta. Ao selecionar uma oferta em BRL/EUR, o preço deve ser informado ou vir de proposta revisada, sem inventar conversão.

O PDF da invoice mantém o logo, as cores, o layout e os campos existentes, com moeda correta nos cabeçalhos e no total. A proposta comercial do Claude não foi reconstruída nem alterada.

## Validação

- Testes HTTP percorrem BRL e EUR: CRM/oferta → calculadora → cotação → aprovação → pedido → confirmação → recebível → invoice aprovada/PDF → Packing List aprovada → planejamento de embarque. Conferem moeda, total, snapshot original e rejeição de troca de moeda.
- O mesmo cenário roda com administrador e perfil comercial; as variantes MongoDB usam somente bancos descartáveis na CI.
- Testes unitários verificam denominações incompatíveis, valores inválidos, moeda imutável, recebíveis e igualdade exata do snapshot USD legado.
- Testes de interface cobrem total por moeda, pedido EUR vindo da cotação, limpeza de preço ao trocar moeda e invoice EUR.
- Chromium percorre a tela integrada em USD, BRL e EUR, incluindo fechamento/reabertura do navegador, recuperação de rascunho, proposta original e largura de 390px.
- A CI completa deve estar aprovada no commit final; os resultados da versão anterior não substituem essa execução.

## Arquivos

Backend: sale_currency.py; business_workflow.py; integrated_workspace.py; server.py; commercial_quotations.py; commercial_invoices.py; commercial_invoice_pdf.py; operations_dashboard.py; workspace_reconciliation.py e testes.

Frontend: lib/saleCurrency.js; Orders.jsx; Quotations.jsx; CommercialInvoices.jsx; IntegratedQuotation.jsx e testes. Navegação: exporthub/scripts/test-native-integration-ui.cjs; workflow test.yml. Preparação: tools/release-preflight.cjs e roteiro de demonstração.

## Pendências que continuam reais

O suporte às três moedas remove a restrição técnica anterior a USD nesse fluxo; não conclui a conversão operacional do acervo D1/R2. O arquivo preservado e o planejador continuam sem gravar registros comerciais. Contatos independentes, vinculação revisada das ofertas/clientes, modelos setoriais/planilhas, memórias antigas ausentes e snapshots divergentes ainda exigem integração e ensaio representativo.

Não foi obtida uma cópia autorizada dos registros e bytes privados do acervo real. Homologação comercial/aduaneira por Gabriela, conta definitiva e validação da infraestrutura efetiva continuam pendentes. Não houve merge, publicação, serviço pago nem ativação de backup automático.
