# Preparação operacional e recuperação — 24/10/2026

Continuação isolada do PR #60. Não é uma declaração de liberação. Código, dados reais, main e instalação permanecem preservados.

## Corrigido: Salvar rascunho

O botão agora usa PUT /api/quote-drafts/{id}. A atualização modifica apenas o rascunho sobre o snapshot comercial mais recente, preservando alterações em CRM, propostas, perfis e vínculos. A versão própria do rascunho impede substituir edições feitas em outra janela. Repetição do mesmo pedido é idempotente; o mesmo identificador não confirma conteúdo diferente. A resposta perdida após commit é conferida antes de reportar falha. Só há retry interno quando o guard transacional comprova que nada foi escrito.

O ID é mantido mesmo se a resposta falhar, evitando criar outro rascunho ao repetir a mesma tentativa. Em conflito, o formulário continua preenchido; é possível retomar a versão salva ou salvar uma cópia explicitamente. A versão comercial da tela só é atualizada junto dos dados efetivamente confirmados pelo servidor. Não há autosave: é preciso clicar em Salvar rascunho / Salvar e continuar depois.

## Testes específicos

- HTTP/SQLite: alterações não relacionadas preservadas; conflito no mesmo rascunho; concorrência de rascunhos diferentes; duplicidade/reenvio; conteúdo divergente para o mesmo token; resposta perdida após commit; viewer/anônimo/cross-origin rejeitados; estrutura inválida rejeitada.
- D1 local real, em diretório descartável: salvar rascunho incompleto e cotação revisada, encerrar completamente o runtime, recriar o runtime sobre a persistência de teste e comparar campos, valores aprovados e permissões.
- Chromium: encerrar todo o navegador e abrir outro processo sem reaproveitar seu estado; buscar o rascunho no servidor, retomar e concluir. Seguem os testes de cálculo, confirmação cadastral, PDF e tela 390px.
- Regressões do PR #60, Claude, cálculos, documentos, permissões e vínculos permanecem no workflow.

Essas verificações usam fixtures. Não comprovam o armazenamento, volume, disponibilidade ou recuperação da instalação real.

## Infraestrutura candidata

compose.candidate.yaml é uma alternativa isolada para validação: projeto/volume distintos, MongoDB autenticado, usuário da aplicação readWrite apenas em ibiag_candidate, banco e API sem portas públicas, interface somente em 127.0.0.1:8788. Credenciais são exigidas por variáveis, sem senha padrão. Cadastro público, documentação da API e descoberta paga desativados. Nenhum container/volume foi criado por esta preparação.

A CI valida a sintaxe do Compose com credenciais fictícias, sem iniciar os serviços. Isso não equivale a build/execução pública homologada. Não usar o arquivo legado docker-compose.production.yml como autorização ou referência pronta para publicar: ele ainda registra Mongo sem credenciais e exposição direta da API; foi preservado para revisão.

node tools/release-preflight.cjs faz somente inspeção de arquivos de código e lista migrações/impedimentos. Não lê segredos, não se conecta a bancos/infraestrutura, não aplica migrações nem publica. --require-ready retorna falha enquanto faltam verificações reais. Um resultado sourceChecksPassed não implica releaseReady.

## Pendências técnicas e de homologação

| Área | Situação |
|---|---|
| Cotação manual e proposta IBIAG | Implementadas e testadas com fixtures; avaliação de Gabriela pendente |
| Rascunho / fechamento e reabertura | Testado no navegador e D1 descartáveis; volume e recuperação reais não inspecionados |
| Fluxo nativo IBIAG CRM → cálculo → cotação → pedido → Invoice/Packing → embarque/dossiê | Regressão integrada existente preservada; não equivale a sincronização entre aplicações |
| Ponte entre aplicações | Empresas/contatos explícitos; catálogo, fornecedores, preços, documentos, pedidos e autenticação MongoDB/D1 ainda separados |
| Identidades e fonte oficial de catálogo/preços/revisões | Integração técnica pendente; não há garantia de consistência automática entre bancos |
| Publicação | Domínio, TLS, proxy, CORS efetivo, segredos e plataforma ainda não validados |
| Migrações e acervo real | Não executados; recuperação e conciliação históricas pendentes |
| Gabriela | Homologação e configuração do perfil/acessos pendentes |
| APIs externas e despesas | Não ativadas nem testadas com credenciais reais |

Não é correto afirmar que basta criar o usuário e publicar. Existem pendências técnicas de integração e infraestrutura além da homologação. Nenhum merge, deploy, dado real, serviço pago ou backup automático foi autorizado ou acionado.
