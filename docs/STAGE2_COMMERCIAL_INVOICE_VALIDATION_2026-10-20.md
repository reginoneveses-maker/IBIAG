# Etapa2 — Commercial Invoice: validação de desenvolvimento

## Candidato

PR49: https://github.com/reginoneveses-maker/IBIAG/pull/49

Branch operations/commercial-invoice-20261019, encadeada à operations/commercial-quotation-20261019 (PR48, SHA8fc434745e2dc01f3ed7e5d76bab35b66a08e9fd). Candidato final 08dcc7878d1d3e8d5d1bd478c8bd06aef73c4208; árvore92eb734ec220f75e5571ac4f0752704b5c328fac. Mantido em rascunho; não integrado em main nem implantado em produção. Main conferida emc9e2b6508c3f791e0b7ec2ba9863a9a0bf5dae6a.

## Implementação e integração

Commercial Invoice em USD com conferência do pedido confirmado/embarcado/entregue, dados do emitente, endereços do comprador/destinatário, condições, local do Incoterm, origem/classificação por item e representante digitado. Nada ausente é inferido. Preparação, salvar rascunho, conferir PDF e aprovação interna são ações distintas.

Memória explícita dos valores do pedido, histórico limitado, controle de versão, uma invoice ativa por pedido e PDFs privados no padrão da apresentação IBIAG, com logo vetorial e cores. Atalhos nos pedidos, menus e central de documentos. NF-e e seu financeiro existentes não são duplicados; a invoice não cria nova venda, estoque ou conta.

Rascunho recebe DRAFT em cada página; cancelado recebe CANCELLED. Aprovação congela condições e dados. Cancelamento conserva referência/histórico e permite novo número. Não há envio ou assinatura gerada e aprovação interna não certifica documentos para despacho.

## Revisão de segurança

- Todas as sete operações HTTP administrativas: preparação, lista, detalhe, criação, edição, decisão e PDF. Tentativas anônimas, proprietário comum, terceiro e papel forjado são recusadas.
- Modelos estritos com limites de campos, datas, versões, índices e códigos. Cliente não envia valores, snapshot, status, histórico ou nome comercial do comprador. Autor/data/versão vêm do servidor.
- Snapshots por lista explícita, sem custos, margens, fornecedores, notas privadas ou objetos completos de preço/cotação. Condições comerciais legadas malformadas são recusadas antes de copiar dados para o documento.
- Trava compartilhada e CAS serializam criação/decisão/edição de pedido. Venda com invoice ativa não pode ser alterada comercialmente, cancelada ou arquivada; logística/pagamento legítimos continuam sem duplicar contas.
- Condições de pagamento/entrega originadas da cotação aprovada não podem ser reescritas na invoice, com bloqueio na interface e na API; teste HTTP percorre cotação real→aprovação→pedido→invoice e comprova preservação sem custos privados. Aprovar confere versão comercial SHA256 e renderiza o PDF antes de gravar. Erro de glifo/layout não deixa aprovação parcial. Falhas de biblioteca não retornam texto privado.
- Geração verifica a versão novamente antes de devolver o PDF; cancelamento concorrente impede devolver aprovação antiga. A interface descarta PDFs tardios após decisões e consultas antigas após trocar documento.
- PDF em memória, rota autenticada, no-store/nosniff, filename controlado e URLs blob revogadas. Não armazena cópia no acervo compartilhado, cria URL pública ou ativa storage/provedor.
- Texto escapado, sem recursos do usuário carregados como HTML/imagem/link, sem JavaScript/anexos/links ativos. Fontes locais e logo vetorial existente. Metadados usam data da revisão; bytes determinísticos por versão.
- Limites de50 eventos/256KiB,100 itens,30 páginas/2MiB por PDF; quantidade/preço até12 casas e limite10^12; total até10^12 USD. Casos longos e precisão acima de quatro casas foram testados.

## Testes locais

Python3.12, pytest com configuração fixa de2 workers/loadscope:333 aprovados,48 subtestes aprovados,143 skips declarados por dependências MongoDB/Docker ausentes. Os23 cenários HTTP novos passaram em base sintética; suas23 variantes MongoDB são skips locais declarados, posteriormente executados com sucesso na pipeline real.

Frontend:307 testes em18 suítes aprovados; build compilado. Cobertura de preparo sem gravação, payload mínimo, documento existente, confirmação/motivo, edição pendente, conflito sem repetição, prévia privada/limpeza de URL, consultas/PDF tardios e recuperação de lista.

PDFs: exemplo sintético aprovado com uma página e teste de estresse DRAFT com25 itens em cinco páginas, ambos renderizados com Poppler. Todas as seis páginas inspecionadas: logo, cabeçalhos repetidos, marcas DRAFT, tabelas, totais, acentos e notas sem sobreposição/corte. O teste HTTP paginado confirma todos os25 itens, cabeçalhos/marca em cada página e total. Parser verifica precisão, metadados, ausência de dados internos/ações ativas e repetibilidade.

[Renderização do exemplo sintético](invoice-review-2026-10-20/commercial-invoice-pdf.png). [PDF exclusivamente de QA, sem validade comercial](invoice-review-2026-10-20/commercial-invoice-synthetic.pdf). Gerados por tools/render_commercial_invoice_review.py, sem banco, credenciais, startup ou rede. PDF regenerado a partir do código final produziu os mesmos bytes; SHA25608f54db96b34854ab9c16220520de70e52ad3e9a95ac2e4b228d23a8f2b848ca. Dados/registro fiscal contêm identificação explícita de teste; nenhum comprador ou operação real é representado.

## Pipeline

Pipeline final concluída com sucesso: https://github.com/reginoneveses-maker/IBIAG/actions/runs/39350024610 . SHA08dcc7878d1d3e8d5d1bd478c8bd06aef73c4208 confirmado no artefato. Backend:476 testes e56 subtestes, sem skips, job118391767722. Frontend:307 testes em18 suítes, build e fluxo completo Chromium aprovados, job118391767950. Ambos os jobs success. A execução39348911123 aprovou474 testes backend e56 subtestes sem skips, no SHAe8f4c39. A execução inicial39348755294 havia aprovado472 testes e56 subtestes. Ambas pararam no Chromium após a aprovação da invoice, ao localizar o nome acessível de um campo textarea preenchido. Rótulos explícitos foram acrescentados aos campos, preservando o teste de comportamento. Após o ajuste de rótulos, a execução39349715519 (SHAdc62fd7) aprovou também frontend/build/Chromium, incluindo PDF baixado, recarga, bloqueio da venda e capturas desktop/mobile. O candidato final acrescenta preservação das condições aprovadas com teste completo de integração. Execuções anteriores não substituem a validação do SHA final.

[Interface desktop](invoice-review-2026-10-20/commercial-invoice-desktop.png) e [interface mobile](invoice-review-2026-10-20/commercial-invoice-mobile.png) do SHA final, inspecionadas após download. Artefato12232667184, ZIP SHA25644c43a6d79bce453ce7c80895cf19ba360430233558b4401a25182294cbae4a3. Capturas persistidas na branch de auditoria porque o artefato do CI expira em1 dia. PNG desktop SHA256a8fac6d34ab95687933fd6627d5ee7f649d94261b0fcc5061409f5cb8341774e; mobile SHA2567cb358a31b862460ad01c042efc0b547845d5f9c0eacc036f978aefa35121bd8.

Chromium ampliado: pedido entregue→invoice→prévia/baixar PDF DRAFT→aprovação interna→baixar PDF aprovado→tentativa de alterar pedido bloqueada→recarregar, com validação de bytes/texto reais do download e ausência de outra conta. Inclui captura de interface desktop/mobile e preserva os cenários anteriores de CRM/cotação/embarques/documentos/acesso. Rede externa bloqueada e fixture sintética.

## Pendências e limites

Etapa1: auditoria autenticada do backend/banco privado existentes, autenticação/persistência do MongoDB, storage privado, proxy reverso/IP, ingressos legados, implantação do SHA validado e fluxos publicados com contas autorizadas. Ver STAGE1_OPERATOR_HANDOFF.md. Não há evidência de produção nesta entrega.

A fonte embarcada cobre os caracteres latinos dos exemplos, sem suporte universal a outros alfabetos; glifos ausentes são recusados antes de aprovar. Sem validação cadastral/fiscal/aduaneira automática, assinatura, envio, Packing List, fracionamento ou devoluções. Requisitos do destino e classificações precisam de conferência da operação. Empacotamento/Packing List permanece uma entrega seguinte, com dados reais de volumes, pesos e medidas.

Nenhum merge em main, deploy, migração/índice, reinício, backup, alteração de rede ou ativação paga executados. Integração entre componentes na branch revisada não equivale a plataforma concluída ou liberada.
