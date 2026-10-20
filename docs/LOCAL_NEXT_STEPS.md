# Roteiro da IBIAG local após importação

Revisão do código em 20/10/2026, candidato de amostras baseado na instalação 79a885f37e605c65aaec3ca2cd5c6be208c81bae. Não é auditoria do computador ou dos dados importados pelo Claude. Presença no código não comprova preenchimento, configuração externa ou homologação de cada função.

## Base existente

| Área | Evidência no projeto | Limite relevante |
|---|---|---|
| CRM e tarefas | Pipeline, ImportCRM, Tasks, vínculo de empresa ao pedido | Conferir duplicidades, responsáveis e contagens após importar |
| Produtos e fornecedores | Catalog, Produtos, FornecedoresHub, ofertas e Specs | Cadastro e documentos não equivalem a rastreabilidade de lotes |
| Preços e comercial | Precos, PriceCalculator, Quotations, Orders | Aprovações explícitas; homologar condições comerciais com casos reais |
| Documentos | Documentos, Specs, CommercialInvoices, PackingLists | Organização e PDFs comerciais não constituem integração aduaneira |
| Operação | Shipments, Operations, Inventory | Embarque manual; não comprova tracking automático nem lotes completos |
| Financeiro | Financeiro e rotas finance/cashflow | Não presumir conciliação bancária, câmbio ou contabilidade completos |
| Certificações | Certificacoes e rotas certifications | Interface reutilizada no hub; cadastro/validade não provam aprovação de qualidade |
| Contas | AccountAccess, PasswordChange, controles admin/usuário | Perfis por função/setor exigem desenho e testes específicos |
| Amostras | PR #55, Samples e rotas samples | Versão separada, ainda não instalada; sem baixa de estoque ou cobrança |

Fontes internas: frontend/src/App.js; frontend/src/pages/gestao/Documentos.jsx, Specs.jsx, Certificacoes.jsx; backend/server.py; docs/STAGE2_OPERATIONS.md; docs/SAMPLE_REQUESTS.md.

## Ordem proposta de trabalho

1. **Conferir a importação concluída.** Comparar totais por tipo, amostra de cadastros, vínculos fornecedor/produto/cliente e abertura de arquivos. Pedir ao processo de importação um resumo com origem, importados, ignorados e erros. Não executar outra importação em paralelo.
2. **Preservar e testar recuperação.** O download administrativo existente inclui banco e GridFS. Gerar a cópia fora de uma janela de importação/escrita e validar restauração em banco isolado vazio. Definir destino e retenção antes de implementar rotina local. Um volume Docker persistente não é um backup externo. Nenhum backup ou agendamento foi executado nesta revisão.
3. **Integrar e homologar amostras.** Após a importação e cópia validada, atualizar a instalação de forma controlada e percorrer uma solicitação identificada como teste. Validar os vínculos e a ausência de estoque/financeiro automáticos.
4. **Qualidade e documentos por produto/fornecedor.** Reutilizar Central de Documentos, Specs e certificações. Desenhar revisão, validade, responsáveis e pendências; distinguir documento cadastrado de documento conferido/aprovado. COA anexado não significa lote liberado.
5. **Lotes e rastreabilidade.** Desenhar recebimento por lote, validade, COA, bloqueio/liberação, reserva, saída e devolução. Não deduzir histórico de lote a partir do saldo atual nem alterar estoque sem reconciliação.
6. **Dossiê de exportação.** Definir lista de documentos por processo e destino, versões conferidas, responsáveis e pendências, reutilizando Invoice/Packing List e embarque. Exigências específicas precisam de validação operacional; não aplicar uma lista universal.
7. **Integrações.** Siscomex é projeto próprio: levantar a operação e serviços oficiais necessários, ambiente de testes, autenticação e credenciamento aplicáveis, regras de acesso e respostas de erro. Comex Stat é consulta estatística e não substitui uma integração operacional com Siscomex. E-mail, transportadoras e bancos também precisam de escopo e configuração próprios. Não solicitar ou guardar certificados/senhas em texto livre.
8. **Acesso de funcionário.** Definir quais funções pode ler e alterar; depois testar usuários distintos. Acesso remoto exigirá transferência validada, HTTPS e revisão de acesso. Não abrir portas do computador como atalho.

## O que pode avançar durante a importação

Desenvolvimento em branch separada, testes com dados sintéticos e documentação. Aguardar o término para alterações no banco instalado, atualização/recriação de contêineres, restauração, limpeza ou movimentação de pastas da instalação.

## Critérios para próxima atualização local

- Importação finalizada e resumo disponível.
- Cópia íntegra e recuperação isolada conferida.
- Versão atual e configuração local preservadas em procedimento controlado.
- Testes automatizados do candidato aprovados.
- Teste funcional após atualização: login, CRM, produto/fornecedor, arquivo privado e amostra.
- Plano de retorno compatível com os dados; não restaurar por cima da base ativa.

O guia local registra que nenhum backup recorrente foi ativado. docs/BACKUP.md descreve ferramentas e um histórico de workflow remoto, incluindo uma pausa posterior; isso não configura uma rotina no Windows.
