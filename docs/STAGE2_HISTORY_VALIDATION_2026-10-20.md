# Histórico operacional completo — evidências de validação

20/10/2026 UTC. Repositório reginoneveses-maker/IBIAG, PR draft [52](https://github.com/reginoneveses-maker/IBIAG/pull/52), base PR51. Entrega em branch candidata; sem merge na main ou deploy. O código funcional foi aprovado no SHA `5dca8276bdd59bb83f876d957acca3a39b5fdaf1`, árvore `0ed5f7982875bdccfa99ec0a1e7f92a56253c390`. A verificação adicional de acesso ao botão Fechar no celular está no SHA `43715ff26f66666b130d2a67c9d18ef68a8beab4`, árvore `fa776a70bce579628f4723a873bfda76c61532cd`.

## Implementado

Cotações, Commercial Invoices, Packing Lists e embarques usam uma única linha do tempo privada com autor, instante, motivo e alterações. Consulta em páginas de20 eventos, até50 por requisição e512KiB de eventos por página, sem truncamento silencioso. Cursores têm MAC com finalidade separada do login, recurso/tipo/versão vinculados e expiração de15min; exigem Bearer administrativo em cada leitura. Revisão alterada entre páginas gera409 e pede atualização. Erros preservam os eventos já carregados. A interface exibe texto seguro e campos de negócio, sem HTML fornecido pelo registro.

Ao atingir32 eventos ou96KiB, um bloco copia somente eventos antigos já confirmados para operation_history no mesmo banco. A referência ao bloco e a nova alteração são confirmadas juntas pelo CAS do registro de origem, sob a trava existente. Falhas de inserção, CAS ou lease não geram revisão fictícia. Cópias não referenciadas podem permanecer, mas não entram na consulta; retry reutiliza o bloco determinístico. Não exige transação entre coleções, replica set, índice novo, tarefa recorrente, TTL, serviço externo ou backup. Blocos acessados têm conteúdo e sequência conferidos; corrupção/ausência gera409. Metadados internos não entram na memória comercial do pedido.

Não há rota de excluir/restaurar histórico. SHA256 detecta divergência dos blocos consultados, sem afirmar prova externa/WORM contra quem controla o banco. Erros ou legado inválido exigem revisão e preservam o registro. Novos comandos de negócio continuam validando versão, origem e permissões; histórico não altera preço, estoque ou recebimento.

## Testes locais

372 testes backend passaram, com48 subtestes;182 skips por indisponibilidade local de MongoDB/Docker, explicitamente não tratados como validação desses caminhos.334 testes UI em21 suítes e build passaram. Após ajuste de aceitação de BSON Int64 e recusa do cursor como token de login, os11 cenários direcionados passaram novamente, com11 repetições Mongo marcadas skip local. A CI final abaixo usa Mongo descartável real.

O arquivo backend/test_operation_history.py contém11 cenários repetidos com Mongo na CI: quatro tipos, paginação integral sem duplicação,61 eventos de invoice e106 de embarque em limiares padrão, permissões401/403, cabeçalhos privados, GET sem escrita, falha de insert, CAS após insert, perda de lease, retry, concorrência, cursores falsos/expirados/cruzados/recusados como login, mudança de versão, blocos ausentes/adulterados, tamanho máximo/continuação e legado inválido preservado. Uma só conta financeira e memória comercial sem arquivo interno são verificadas.

Os seis testes novos de OperationHistory cobrem texto seguro, páginas, falha com preservação dos itens, resposta tardia de outro documento, versão alterada e atualização sem duplicar. Chromium cria34 revisões sintéticas, verifica20 na primeira página e34 após continuar, alcança o evento inicial e o mais recente e atualiza sem duplicar. Percurso anterior CRM→cálculo→cotação→pedido→embarque→Invoice/Packing→painel/documentos continua ativo; base descartável e dados sintéticos.

## Pipeline e revisão visual

[CI39357981603](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39357981603), SHA5dca827: backend118417142558 e frontend118417142330 concluídos com sucesso. **554 testes backend +56 subtestes, sem skips;334 UI/21 suítes, build compilado e Chromium passaram.**

Artefato12236261275 confirmou head5dca827. ZIP3359920 bytes; digest SHA256 `7a41fe2d962a85e2914d98f6005f759be2cbb3323eb0a2eb3f6f958c595475d1` conferido antes de ler somente os dois PNG esperados, com limites de tamanho e magic PNG. Desktop194698 bytes, SHA256 `2a8f4308c6c8c44be4704064ca68d9590b26de29bdc1109c20a7a9c52b104ffb`. Móvel78320 bytes, SHA256 `b9ca2bc7df4aba6b445ca61b7210a429d22e867a86f9059cb52e79f55f96a975`.

Ambas as imagens foram inspecionadas. Na primeira captura móvel, os controles finais do diálogo ficaram parcialmente fora da imagem. A validação foi ampliada para rolar até Fechar e conferir a posição dentro da tela de390×844. O check adicional passou na [CI39383648571](https://github.com/reginoneveses-maker/IBIAG/actions/runs/39383648571), SHA43715ff: backend118498284057 e frontend118498284244 concluídos com sucesso. **554 backend +56 subtestes sem skips,334 UI/21 suítes, build e Chromium passaram novamente**, incluindo a posição acessível do botão Fechar no celular. A mudança adicional é somente no teste/captura; nenhum novo comportamento de negócio foi acrescentado.

Artefato final12246731781 confirma head43715ff. ZIP3354063 bytes, SHA256 `b5535ac19047066bf603d6d220267bfb24a45307f6479f4a02fb4fbc203ee09d`, conferido antes da extração limitada dos dois PNG esperados. Desktop194198 bytes, SHA256 `6adc5249523773bcea5661964ccc008f31ee291b192358c66be3bc071176f44e`; móvel71188 bytes, SHA256 `ae02484bfdb1e5d0ee91955138d67c0cd369dbe1a665c8b5208eb68882f80106`. As capturas finais foram inspecionadas e estão em history-review-2026-10-20/. A imagem móvel final mostra o controle Fechar dentro da tela; rolagem interna mantém os eventos e ações acessíveis. Capturas anteriores foram substituídas pelas correspondentes ao SHA final, sem apresentar imagem intermediária como evidência final.

## Segurança e liberação

Revisão de acesso: apenas admin; owning CRM user comum permanece403. Cursor não autentica. Respostas privadas/no-store; nenhum dado de custo, fornecedor ou arquivo interno é acrescentado ao snapshot comercial por esta mudança. Hash e contadores são conferidos no caminho alcançável; leitura não varre cópias órfãs nem grava no banco. A janela recente fica limitada sem apagar eventos antigos confirmados. Falhas não são convertidas em histórico vazio ou sucesso.

Nenhuma base de produção, credencial ou URI foi usada nos testes/evidências. Nenhum novo serviço pago, provedor, crédito ou backup foi ativado. Main permaneceu em c9e2b6508c3f791e0b7ec2ba9863a9a0bf5dae6a na conferência desta continuação. O candidato não está na aplicação publicada.

Permanecem pendentes a sessão de execução para auditoria somente leitura no backend real, privilégios/autenticação do banco, dbPath/montagem/persistência, storage privado, cadeia real de proxy/IP e homologação com contas autorizadas. Inventário Railway repetido: backend e Mongo online, sem volumes associados e sem patch staged. Não reiniciar Mongo/anexar volume vazio/migrar para contornar o diagnóstico. A ausência de volume é sinal de investigação, não prova isolada de perda de dados.

Histórico completo destes quatro tipos não equivale a auditoria global de todos os módulos, armazenamento comprovadamente permanente, aceite comercial ou conclusão integral das etapas1/2. Política de retenção e monitoramento de crescimento ainda depende da operação. Contrato técnico em docs/OPERATION_HISTORY.md na branch do PR52; roteiro operacional em STAGE1_OPERATOR_HANDOFF.md.
