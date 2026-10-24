# Continuação isolada — 24/10/2026

Base: PR #59 (ef5deeee), dependente de #58. Histórico e funcionalidades do Claude preservados. Os mesmos 25 PRs continuam abertos. PRs #19–#27 já sobrepostos à composição #28 não devem ser reaplicados individualmente; #53 permanece separado e não executado.

O ambiente Linux da etapa anterior ficou indisponível antes de enviar os commits 0bcc91b/a5bfe22. Estes commits não foram recuperados nem se devem confundir seus resultados locais anteriores com a validação atual. O checkout Windows anterior, com alterações ainda não commitadas, foi preservado. Esta ramificação foi reconstruída sobre o head remoto exato do #59 em outro diretório.

O administrador exporta a empresa explicitamente selecionada no Pipeline. POST /api/crm-transfer/export aceita 1–25 IDs únicos, rejeita seleção incompleta/ambígua e exporta somente nome, país, site, segmento e contato informado. Sem owners, notas, valores, documentos ou contatos inferidos; zero gravações na origem.

/integracao conserva a prévia existente e acrescenta uma importação controlada. Correspondência por nome/país exige confirmação explícita da empresa ativa. Não sobrescreve campos de empresas/contatos existentes. Origem alterada, país ausente, ambiguidade de contato e identidade repetida exigem revisão. Até 25 empresas/2 MiB; limite transacional pode exigir lotes menores.

O servidor permite gravar somente com ALLOW_CRM_IMPORT exatamente true, proprietário e mesma origem, confirmação literal e hash da prévia vinculado ao arquivo/revisão/usuário. A gravação usa a transação e a auditoria existentes. Reenvio reconhece origem/hash; não duplica nem desfaz edições posteriores. Conflitos exigem nova conferência; sem retries automáticos. Flag não configurada em instalação/produção.

Nesta reconstrução, a proveniência fica em commercial.interchangeLinks, campo adicional da coleção existente (sem tabela/migração nova). É gravada atomicamente com empresas/contatos e preservada pelo backup/restaurador manual existente. Endpoints genéricos não podem alterar/remover essa proveniência ou apagar os registros vinculados. Não se deve executar restauradores antigos sem validação dos vínculos.

Não transfere automaticamente fornecedores, produtos, preços, cotações, pedidos, arquivos, identidades ou permissões entre MongoDB e D1. Os módulos nativos existentes continuam preservados. Unificação dos dois bancos e autenticação, conciliação histórica e homologação em dados reais permanecem pendentes. Testes sintéticos não significam homologação da instalação.

Autorização do usuário: enviar somente esta ramificação, abrir PR em rascunho e executar CI. Não integrar main, publicar, alterar dados reais, ativar despesas ou backups automáticos.
