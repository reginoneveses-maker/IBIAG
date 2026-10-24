# Versões documentais e prévia de integração

Candidato isolado empilhado sobre o PR #58. Não altera main, instalação, ambiente publicado ou dados reais. Não ativa serviços, pesquisas pagas ou cópias automáticas.

## PDFs imutáveis
- Cada atualização cria outro ID em specs e outro objeto specs/ID. O original e todos os links antigos continuam válidos.
- GET/POST /api/specs/{id}/versions consulta o grupo ou adiciona uma revisão. Escrita exige owner/editor, mesma origem, versão conferida, motivo e PDF de até 20 MB. Multipart é limitado durante o streaming, inclusive sem Content-Length.
- Produto, tipo e fornecedor vêm do original no servidor; não podem ser trocados pelo formulário de atualização.
- Metadados e auditoria são atômicos em D1, usando o guard existente e unicidade de revisão. Conflitos retornam 409, sem retry automático.
- Um erro de transporte após commit é reconciliado antes de qualquer limpeza. Se o resultado do banco permanecer desconhecido, o objeto é preservado para revisão manual. Isso pode deixar um objeto órfão, mas evita apagar PDF potencialmente confirmado.
- SHA-256 identifica bytes das novas versões e é conferido no download. Originais legados sem hash permanecem explicitamente desconhecidos; não são regravados.
- Visualização em nova aba e download autenticado continuam privados. Assinatura PDF/hash não são antivírus, aprovação técnica ou certificação de autenticidade.
- Validade é informada, nunca extraída/inferida. O painel de saúde considera apenas a versão atual de cada grupo. Original antigo continua no histórico mesmo após vencer.
- Limite de 500 versões por grupo; excedentes são recusados. Não há exclusão ou sobrescrita.

## Exportação e recuperação
A exportação manual completa continua exporthub-complete-v1 e inclui todos os PDFs, acrescida de documentVersioning=spec-revisions-v1 e specRevisions. O verificador atual valida cadeia, identidade, datas e hashes antes de restaurar. O restaurador atual recupera os metadados e confere os arquivos num destino local vazio. Backups antigos sem versões continuam aceitos. Use ferramentas desta versão: restauradores antigos não conhecem as relações de revisão. Nenhuma exportação/recuperação real foi executada.

## Integração sem gravação
backend/crm_transfer.py transforma uma lista de leads previamente exportada/autorizada em ibiag-crm-transfer-v1, somente com identidade da empresa e contato explícito. Não consulta banco, API ou provedor. Omite notas, owners, valores, estágio, cotações, decisões inferidas e credenciais.

A tela /integracao e POST /api/integration/preview são do proprietário. Aceitam até 2 MB e 1.000 empresas. Comparam nome/país normalizados com empresas existentes e retornam novas/correspondentes/ambíguas. Não salvam nem importam; não presumem que correspondência de nome é a mesma entidade. O formulário não executa migração. Não são aceitos backups completos, permissões ou campos extras.

As duas aplicações continuam com identidades e bancos próprios. Unificar autenticação, contas, preços, pedidos, documentos e mapeamentos exige uma etapa de migração explícita. Esta prévia não é uma ponte de escrita nem sincronização.

## Migração e liberação
0009_spec_revisions.sql está versionada para aplicação futura no ambiente autorizado. Não foi executada na instalação ou produção. Novas tabelas são aditivas e os registros existentes não são modificados. O código novo exige essa migração antes de executar os endpoints; banco sem tabela retorna falha, não um resumo verde. A migração de schema não é um backup. A execução depende de liberação separada; não publicar automaticamente.

## Verificação
O CI inclui TypeScript/build, testes de HTTP/SQLite, D1/R2 reais descartáveis, exportação/restauração das versões, permissões, concorrência, falha antes/depois do commit, hash divergente, datas e prévia sem escrita. A interface tem um teste Chromium com rede sintética para conflito, preservação do formulário, ausência de retries, nova revisão explícita e perfil leitor. A suíte React/Python anterior também permanece no workflow. Consulte o PR para resultados do SHA final; não confundir testes sintéticos com homologação de dados ou infraestrutura reais.

O ambiente Windows foi desconectado durante esta etapa. A validação e as capturas desta alteração são executadas pelo CI, sem alterar o computador do usuário.
