# IBIAG — escopo e estado do sistema

O sistema reúne CRM de prospecção de ingredientes brasileiros e Gestão da IBIAG, com autenticação administrativa, documentos, portfólio, ofertas por fornecedor, especificações, preços, compras, pedidos, estoque, contas financeiras e notas fiscais.

## Dados carregados e limites

- Portfólio oficial: 136 produtos, 24 fornecedores e 145 ofertas, com textos de preço e comissão da fonte preservados.
- Acervo: 657 PDFs cadastrados; documentos técnicos, comerciais, societários, logísticos e certificados. Há versões antigas; cadastro não comprova vigência ou certificação atual.
- CRM: 1.233 novos cadastros importados e quatro atualizados na importação registrada. São contatos e candidatos, sem comprovação automática de compras atuais.
- Arquivos fora do escopo IBIAG foram desconsiderados. As pendências de revisão e fontes de dados constam no índice mestre de 02/10/2026.

## Funções

- CRM: pipeline com mudança de estágio, cadastro de contatos e decisores, histórico de interações, tarefas, templates PT/EN e importação de planilhas.
- Comércio exterior: consulta oficial agregada por NCM, país, volume e valor FOB no Comex Stat. Esses dados não identificam empresas importadoras.
- Pesquisa web: busca de empresas e possíveis decisores, com evidências e status a validar. Requer serviço externo configurado; resultados não são compradores verificados.
- Documentos: área e seção unificadas, visualização e download, classificação, lixeira e restauração administrativa.
- Portfólio: ofertas vinculadas por produto/fornecedor, preços originais, comissões, anexos técnicos e materiais comerciais.
- Pedidos e compras: itens, quantidades, preços calculados no servidor, moedas, datas, estoque próprio opcional e contas vinculadas. Ver docs/FLUXOS_OPERACIONAIS.md.
- Estoque: físico, reservado e disponível; ajustes administrativos e movimento derivado dos registros de origem.
- Financeiro: contas por moeda, marcação do pagamento, períodos futuro/histórico e visão prevista/realizada.
- Fiscal: cadastro e anexos de notas de entrada/saída e leitura de XML NF-e. Não emite ou transmite NF-e à SEFAZ.
- Fornecedores: cadastro, contratos, certificados e vencimentos; autenticidade e vigência dependem de conferência do documento.
- Recuperação: download administrativo completo e ferramenta de restauração isolada com preservação dos PDFs. Ver docs/BACKUP.md.

## O que não está comprovado por uma compilação

A compilação e os testes automatizados não comprovam todas as funções em produção, a validade dos contatos/certificados, a configuração de serviços externos nem a execução diária de backup. Essas verificações devem constar no registro de validação com evidências reais.

Envio automático de email/WhatsApp, emissão fiscal, assinatura eletrônica, processamento de pagamentos e leitura fiscal integral a partir de PDFs não foram implementados por estes fluxos. Templates e lançamentos são registros internos. Devoluções de estoque e estornos financeiros efetivos exigem fluxos próprios; a aplicação impede reversões implícitas depois de movimentação concluída.

Credenciais ficam fora do código e da documentação. Registro público de usuários fica desativado por padrão; novos usuários são criados pelo administrador.
