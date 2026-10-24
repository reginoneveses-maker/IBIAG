# Continuidade da cotação e conciliação do acervo — 24/10/2026

Atualização posterior: docs/MULTICURRENCY_CANDIDATE.md descreve o suporte a USD/BRL/EUR. As referências abaixo à restrição USD registram a etapa anterior.

Continuação do PR #60, branch improvements/crm-import-20261024. Esta etapa não publica nem importa dados reais.

## Cotação: fornecedor, fichas e certificados

A consulta fica na mesma página da cotação. Ao escolher ou retomar um ingrediente, a tela lê o contato do fornecedor, as condições descritivas registradas e os documentos efetivamente vinculados à oferta.

A API /api/integrated/offers/{id}/context reutiliza product_offer_documents e as regras existentes de arquivos privados/proprietário. Não publica PDFs nem inclui observações internas no retorno. Documentos ambíguos, ausentes ou não visíveis são sinalizados; não são escolhidos arbitrariamente nem removidos. A validade dos certificados usa quality_rows. Certificado vencido é aviso e não impede salvar cotação.

Visualizar usa a abertura autenticada e a identificação de assinatura já existentes, com PDF/imagem em Blob privado. Fechar o documento mantém os campos da cotação. Uma resposta atrasada de outro ingrediente é descartada; URLs temporárias são liberadas. Falha de consulta permite nova tentativa sem limpar o formulário.

Foi corrigida uma lacuna do endpoint nativo de arquivos: o operador comercial agora consegue abrir certificado publicado no cadastro de certificações. A checagem de arquivo privado do CRM continua anterior à liberação; usuário comum sem o perfil não ganhou esse acesso.

A página integrada também deixa a cotação manual disponível durante a consulta inicial e em caso de falha de catálogo/clientes/registros salvos. Cada leitura tem timeout e aviso próprio; recuperar uma fonte limpa só o aviso correspondente. Novas leituras não descartam registros recém-salvos no estado local.

O histórico passou a usar cursor de data/ID, vinculado ao usuário, em páginas de 100 cotações. Não usa offset que pule registros quando novas cotações entram. A interface oferece Carregar cotações anteriores e une os resultados por ID, sem duplicar cotações. Rascunhos mantêm seu limite explícito de 100 por usuário.

## Preparação implementada para o acervo antigo

backend/workspace_reconciliation.py aceita o formato exporthub-v1 que o endpoint manual de exportação existente já produz. A CLI lê somente os arquivos explicitamente informados. Não lê credenciais, não abre conexão MongoDB, não altera a aplicação nem chama serviços externos.

O plano inventaria CRM, contatos, negociações, preços/perfis, cotações/rascunhos, tarefas, documentos, processos setoriais, embarques, specs e anexos. Preserva o JSON original inteiro, inclusive campos e módulos desconhecidos. Valores antigos não são recalculados.

Verifica IDs duplicados, referências ausentes, revisões, registro de origem CRM, vínculos explicitamente revisados, tamanho e hash dos arquivos. Correspondência por nome/país é sugestão; nunca autoriza gravação automática. A exportação JSON sozinha contém índices, não os bytes dos PDFs: arquivo ausente impede declarar o pacote completo.

O plano também aponta impedimentos para conversão operacional: contatos independentes sem modelo equivalente no lead nativo, ofertas/clientes ainda sem mapeamento revisado, memória de revisão ausente, snapshots divergentes, planilhas com serviço/unidade diferente de kg/múltiplos itens e moedas diferentes de USD no fluxo legado. Não resolve essas diferenças apagando campos ou substituindo valores.

### Ensaio de preservação

As funções stage_synthetic_archive e recover_synthetic_archive só aceitam banco com nome ibiag_rehearsal_* e marcador synthetic-only/synthetic=true já existente. Não há endpoint de importação nem CLI que grave em banco. Não existe ativação para banco de produção.

O ensaio usa coleções próprias, com gravação imutável e chunks de 1 MiB. O manifesto é publicado somente depois de verificar todos os bytes. Uma interrupção deixa o pacote incompleto indisponível; repetir o ensaio reaproveita somente chunks idênticos. Dado diferente é rejeitado, sem sobrescrever ou apagar. O tamanho BSON do manifesto é conferido antes de qualquer chunk ser escrito.

A recuperação verifica hashes/tamanhos e entrega exatamente o JSON e os arquivos de entrada. Os registros nativos, preços aprovados, identidades e permissões ficam intactos. O ensaio não agenda backups nem cria serviços.

## Demonstração exclusivamente fictícia

Os arquivos de demo/workspace-reconciliation são sintéticos. Os anexos .bin são bytes de teste para preservação; não são fichas técnicas comerciais válidas.

Exemplo de análise offline:

```text
python backend/workspace_reconciliation.py --backup demo/workspace-reconciliation/exporthub.json --native-inventory demo/workspace-reconciliation/native-inventory.json --links demo/workspace-reconciliation/reviewed-links.json --files-manifest demo/workspace-reconciliation/files-manifest.json --files-root demo/workspace-reconciliation/files --output plano-novo.json
```

O destino de saída deve ser novo; a CLI não sobrescreve arquivos. Código de saída 0 significa pacote apto ao ensaio sintético, não migração concluída. Código 2 significa pendências no plano. businessReady, businessWrites e identityWrites permanecem false.

Para Gabriela: abrir Criar cotação IBIAG, selecionar fornecedor/ingrediente e cliente, informar quantidade, consultar a ficha na mesma tela e voltar; conferir aviso de certificado vencido fictício; salvar rascunho, reabrir o navegador, retomar e gerar a proposta. Para o ensaio histórico, mostrar o plano e a recuperação isolada; não utilizar dados reais ou a base publicada.

## Validação desta etapa

Testes locais aprovados:
- 3 testes de contexto: privacidade CRM, acesso comercial ao certificado, usuário comum negado, campos privados omitidos, validade, duplicidades e leitura sem mutação.
- 13 testes de conciliação/arquivo em mock: formato existente, bytes exatos, campos desconhecidos, snapshot antigo sem recálculo, arquivos ausentes/alterados, IDs/mapeamentos ambíguos, CLI offline/traversal/sem sobrescrita, interrupção/retomada, corrupção, guard do destino e limite antes da gravação.
- Histórico com mais de 200 cotações, inclusão entre páginas, cursor inválido e separação de usuários.
- Chromium com API FastAPI sintética: ficha interna, manutenção da quantidade, aviso de certificado vencido, falha e recuperação de catálogo, fechamento completo/reabertura do navegador, rascunho, proposta IBIAG e 390px sem overflow.
- TypeScript e 12 regressões existentes da calculadora.

A CI repete os cenários aplicáveis com MongoDB real descartável, roda todos os testes de frontend/backend/ExportHub, os testes de respostas atrasadas/falhas da consulta e o build candidato. Usar a CI do commit final como evidência, não a aprovação da versão anterior.

## Arquivos modificados nesta etapa

- API e testes: backend/integrated_workspace.py, backend/server.py, backend/integrated_browser_fixture.py, backend/test_integrated_workspace.py e backend/test_quote_context.py.
- Preservação: backend/workspace_reconciliation.py, backend/test_workspace_reconciliation.py, .gitattributes e os dados sintéticos de demo/workspace-reconciliation/.
- Interface: frontend/src/components/QuoteSourceContext.jsx e seu teste, frontend/src/pages/gestao/IntegratedQuotation.jsx, exporthub/components/exporthub/logistics/QuoteCompletion.tsx e o artefato recompilado frontend/src/integration/quote-components.js.
- Navegação/CI: exporthub/scripts/test-native-integration-ui.cjs, .github/workflows/test.yml e os relatórios desta etapa. O modelo proposalHTML IBIAG permaneceu sem alteração.

## O que ainda não está concluído

- O acervo real D1/R2 não foi exportado, conciliado, copiado ou modificado. É necessária uma cópia autorizada dos registros e dos arquivos autenticados para executar o ensaio representativo.
- O plano e o arquivo preservado não convertem automaticamente os módulos antigos em registros operacionais nativos. Resolver os impedimentos de modelo/mapeamento continua sendo trabalho técnico, antes de qualquer migração real.
- Pedidos/documentos legados permanecem em USD. Propostas BRL/EUR continuam disponíveis; nenhuma conversão é inventada.
- Conteúdo/conformidade dos certificados e termos comerciais dependem de revisão humana; o painel verifica metadados.
- Homologação da Gabriela, sua conta definitiva, destino público/HTTPS, segredos, persistência e recuperação no destino continuam pendentes.

Não é correto afirmar que resta somente publicar. Não houve merge na main, publicação, alteração de dados reais, ativação de cobrança ou backups automáticos.

## Continuação: identidade comercial e retomada após resposta perdida

A gravação repetida da mesma cotação agora reconhece o registro imutável antes de consultar novamente os vínculos do catálogo e CRM. Assim, uma alteração cadastral posterior não transforma uma gravação já concluída em falha de confirmação. Um conteúdo diferente com o mesmo ID continua rejeitado.

Novas cotações guardam a identidade da empresa e o país do CRM separadamente do snapshot comercial. A preparação para pedido verifica esses dados novamente e recusa divergências, sem alterar a proposta, os valores ou o cadastro. Cotações anteriores continuam compatíveis e verificam o nome disponível no snapshot; não se inventa um país histórico. Alterações de contato não impedem a continuidade.

Regressão automatizada cobre mudança de empresa, mudança de país, repetição após resposta perdida, ausência de pedido indevido, preservação exata do registro e retomada com identidade restaurada. O teste também é herdado pelo perfil comercial e pelas variantes MongoDB descartáveis da CI. Nenhum dado real foi utilizado. A CI do novo commit deve ser consultada antes de atribuir aprovação a esta continuação.
