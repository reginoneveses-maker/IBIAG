# Etapa2 — Cotações comerciais: validação de desenvolvimento

## Candidato e estado

PR48: https://github.com/reginoneveses-maker/IBIAG/pull/48

Branch operations/commercial-quotation-20261019, encadeada à design/ibiag-presentation-brand-20261019 (PR47). SHA final8fc434745e2dc01f3ed7e5d76bab35b66a08e9fd, árvorec1171aecf2b0e8c0d04764fef109e864f0b26325. A base de apresentação permanece no SHA37affcf752ae8c5c80456ae6839edbdaca662b9c. O PR fica como rascunho; não foi integrado em main nem implantado em produção.

## Implementado

Cotações administrativas criadas a partir dos cálculos salvos, com cliente do CRM, referência, validade, Incoterm, pagamento, entrega e observações. Memória do cálculo conferida/recalculada no servidor e preservada, com versões e histórico de até50 eventos/256KiB.

Salvar rascunho, aprovar internamente e preparar pedido são ações distintas. Aceite do comprador não é inferido. Cotação aprovada e vigente gera somente um pedido em rascunho; confirmar venda e registrar embarque continuam no fluxo existente. Não são criados contas, movimentos ou reservas pela simples cotação/aprovação. O pedido preserva cliente, Incoterm, quantidade, preço e condições aprovados.

Lista, filtros, paginação, histórico e atalhos estão integrados a Gestão/CRM, Preços e Pedidos. Erros mantêm o formulário sem repetição automática de escrita. Respostas tardias são descartadas. Cálculos e pedidos manuais existentes continuam disponíveis.

## Revisão de segurança e integridade

- Todas as seis operações HTTP de cotações exigem administrador; testes tentam acesso anônimo, proprietário comum, terceiro e cabeçalho de papel forjado.
- Modelos de entrada são estritos e rejeitam propriedades extras, versões booleanas, NUL e limites excessivos. O servidor controla autor, histórico, status, valores e memória.
- Criação confere revisão SHA256 do cálculo e unicidade da referência/id. Edição e decisões usam a versão armazenada, comparação na gravação e motivo obrigatório.
- Conversão refaz aprovação, validade UTC, referência do CRM, produto, fornecedor e oferta ativa/produto/fornecedor/unidade; não confia na conferência anterior do navegador.
- A trava compartilhada serializa decisões e pedidos. A conversão grava somente o pedido; a existência de orders.source_quote_id deriva o vínculo da cotação, sem um segundo estado sujeito a gravação parcial. Pedidos cancelados/arquivados também bloqueiam repetição.
- Exclusão de CRM/cálculo/produto/oferta/fornecedor referenciados e substituição destrutiva do portfólio ficam bloqueadas. Os bloqueios usam a mesma trava de escrita.
- Cliente antigo que omite os campos novos não apaga vínculos. Snapshots falsificados são descartados. Rótulos aprovados são preservados mesmo após atualização de catálogo; mudanças incompatíveis de referência/unidade bloqueiam nova conversão.
- Falha antes da gravação não deixa registro parcial e devolve erro sem canário privado; histórico cheio/tamanho excessivo preservam o documento anterior.
- Não foram criados serviços, índices/migrações de produção, provedores pagos, backups ou permissões novas no banco.

## Testes locais

Python3.12: pytest -q backend com configuração fixa de2 workers/loadscope:310 aprovados,48 subtestes aprovados,120 skips por dependências de MongoDB/Docker ausentes. Os17 cenários HTTP novos passaram em base sintética; suas17 variantes de MongoDB real são skips locais declarados.

Frontend:296 testes aprovados em17 suítes; build compilado com DISABLE_EMERGENT_OVERLAY=true. Sintaxe do roteiro Chromium validada. Chromium não foi executado localmente por indisponibilidade do binário; a pipeline executa esse fluxo.

Os testes novos cobrem criação sem movimento, origem/identidade/valores canônicos, estrita validação, edição versionada, aprovação/congelamento, validade, acesso administrativo, exclusões, concorrência de decisões/conversões/cancelamento, erro redigido, limites, renomeação do catálogo, alteração de unidade depois da conferência e duplicação após cancelar/arquivar pedido. Interface cobre ações explícitas, payload mínimo, imutabilidade, conflito sem repetição, resposta tardia, recuperação da lista e origem ambígua do pedido.

## Pipeline e evidência visual

Pipeline final concluída com sucesso: https://github.com/reginoneveses-maker/IBIAG/actions/runs/39345946397 . SHA8fc434745e2dc01f3ed7e5d76bab35b66a08e9fd confirmado no artefato. Backend:430 testes e56 subtestes, sem skips, incluindo MongoDB7 descartável e verificações Docker. Frontend:296 testes em17 suítes, build compilado e fluxo completo Chromium aprovados. Jobs118378450415 (backend) e118378450140 (frontend), ambos success. A execução39345461574 aprovou430 testes backend e56 subtestes, sem skips, no SHA43f721f. O primeiro fluxo de Chromium39345328693 parou ao localizar o nome acessível de Incoterm; corrigido com aria-label explícito. A revisão da captura também identificou preço unitário exibido sem suas casas decimais; corrigido reutilizando priceMoney da calculadora, incluindo teste de preço com quatro casas e total com centavos. Execuções anteriores não substituem o candidato final.

Captura do mesmo SHA inspecionada visualmente: [cotação aprovada](quotation-review-2026-10-20/quotation-desktop.png). Preço unitário exibe US$4,26 e total US$1.065,00 para250kg, com aprovação interna identificada. São dados sintéticos, sem operação ou comprador real. Artefato12231317213, digest ZIP11a10a0908c661da59eca4a067c45657cd9363ca8aa6a791a917e6a064b1e53b; PNG SHA2568f67aa97fcc3e25dafcc8140ae0c21c37987663e8046d58a269c57a39577def7. Captura persistida nesta branch de auditoria porque o artefato do CI expira em1 dia.

O roteiro de navegador foi ampliado para cálculo→cotação→aprovação interna→edição posterior do cálculo→pedido único, validando memória preservada, bloqueios na interface e na API e ausência de conta financeira duplicada. Rede externa é bloqueada, dados são sintéticos e o cenário existente de CRM/documentos/embarques/acesso é preservado.

## Pendências de liberação

A etapa1 permanece aberta: acesso autenticado de leitura ao backend/banco privado existente, autenticação e persistência efetivas do MongoDB, armazenamento privado, proxy reverso/IP, ingressos legados, publicação do SHA testado e fluxos com contas autorizadas. Ver STAGE1_OPERATOR_HANDOFF.md. Nenhuma dessas evidências de produção é substituída pelos testes acima.

Não inclui PDF comercial, envio, assinatura/aceite externo, vários itens, parcelamento ou devolução. Documentos operacionais Invoice/Packing List e indicadores ainda exigem implementação/homologação próprias. Esta entrega integra os componentes apenas na branch de revisão; não significa plataforma100% concluída ou liberada para operação.
