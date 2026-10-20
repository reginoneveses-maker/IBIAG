# Packing List do pedido

Entrega da etapa2, sobre a Commercial Invoice (PR49). Código em revisão, sem publicação/homologação de produção. Não substitui as pendências da etapa1.

## Uso

Administração → Pedidos → Criar / ver Packing List, ou Gestão → Packing Lists. A central de documentos oferece acesso à mesma área privada; não há cópia em pastas compartilhadas. Somente administradores acessam as sete rotas HTTP, inclusive PDF e preparação.

A preparação é somente leitura. Pedido deve ser único, não arquivado, com workflow habilitado e estado confirmado/embarcado/entregue. Reaproveita as verificações de integridade comercial existentes; a memória retida contém apenas referência, comprador/país, data, Incoterm e descrição/unidade/quantidade de cada item. Não guarda preço, custo, fornecedor ou condições financeiras. Invoice e Packing List são documentos diferentes ligados ao mesmo pedido; não existe invoice obrigatória ou associação fictícia entre números de documentos.

Preencha emitente, endereços, responsável e grupos de volumes. Cada grupo contém marcas distintas, embalagem, número de volumes, pesos líquido/bruto em kg, cubagem opcional em m³ e alocações dos itens. **Pesos, cubagem e quantidades alocadas são totais do grupo**, sem multiplicação pelo número de volumes. Marcas podem informar intervalos físicos; o sistema não deduz intervalos, selos, lotes, dimensões, país de origem ou pesos por embalagem. Unidades vêm do pedido e não são convertidas em peso automaticamente.

Rascunhos permitem preenchimento incompleto, mas já recusam excesso de quantidade, itens inválidos/repetidos no grupo, marcas repetidas, bruto menor que líquido e cubagem informada não positiva. Para aprovar, todos os dados obrigatórios devem estar preenchidos, cada grupo precisa de pesos positivos e **cada item do pedido completo deve ter exatamente sua quantidade distribuída**. Quantidades usam strings decimais validadas (até12 casas), somadas com Decimal sem tolerância ou arredondamento implícito. Pesos/cubagem individuais limitados a1e12; grupos até100, volumes por grupo até100000, itens por grupo até100. Totais de peso/cubagem permanecem desconhecidos quando qualquer grupo omite a respectiva medida; o PDF do rascunho mostra “Not provided”, sem inferir zero.

Aprovação interna exige versão atual, motivo e confirmação explícita da conferência física/cadastral. Não mede cargas, assina, envia a terceiros, cria embarque parcial, confirma outra venda ou movimenta estoque/financeiro. Não afirma aceitação aduaneira ou validação legal no destino. Nome do responsável é digitado, sem assinatura eletrônica.

## Integridade e acesso

- Identificador/referência são únicos inclusive após cancelamento; só um documento ativo por pedido. Rascunho pode ser editado, aprovado é imutável, cancelamento é terminal e deixa histórico. Para corrigir aprovado, cancele e prepare outro número.
- Campos extras são proibidos; autor, datas técnicas, estado, memória, totais e histórico são do servidor. Versão otimista e trava de negócio existente protegem gravações concorrentes e competição com alterações de pedido.
- Pedido com Packing List ativa não pode alterar dados presentes na memória, cancelar ou arquivar. Mudanças de pagamento/logística permanecem possíveis se não alterarem os itens/comprador/referência preservados. Alteração externa incompatível bloqueia aprovação/download aprovado. A UI preserva entrada ao receber conflito e não repete decisões automaticamente.
- Histórico limitado a50 eventos e registro a256KiB; atingido o limite, exige revisão administrativa. Sem migração ou índice novo executado em produção.
- PDF gerado sob autenticação, `private, no-store`, `nosniff`, nome controlado sem dados de caminhos; sem token na URL, serviço externo, upload ou HTML executável. Renderer aplica outra lista explícita de campos públicos e escapa todos os textos. Download confere novamente versão após renderização, recusando PDF superado por decisão simultânea.
- Logo vetorial e cores existentes da IBIAG; mesmos fonts latinos locais da invoice. Caracteres não suportados são recusados antes de aprovar. Limites de30 páginas e2MiB. Renderização incompatível retorna erro controlado sem gravar aprovação. Rascunho/cancelado recebem marca em todas as páginas; cópias já baixadas não podem ser revogadas.
- Prévia usa blob autenticado em object; URLs são revogadas e respostas tardias não sobrescrevem outro documento/decisão. Sem novos serviços, créditos, backups ou acesso a dados reais.

## Testes e limites

`backend/test_packing_lists.py`:19 cenários HTTP repetidos também com MongoDB descartável na CI. Cobrem acesso em todas as rotas, preparação sem escrita, exclusão de dados privados, validação estrita, referências/versão, precisão, distribuição por item, múltiplos grupos, pesos/cubagem, aprovação explícita, imutabilidade/cancelamento, concorrência, bloqueios do pedido, financeiro único, drift externo, PDF privado/determinístico/escapado, cancelamento durante renderização, paginação, falhas do renderer, glyphs, limites e PDF multipágina.

`PackingLists.test.jsx`:14 cenários de interação, payload sem memória/totais forjados, grupos manuais, aprovação/dirty/confirmação, conflitos, rascunho existente, paginação/repetição, resposta tardia, prévia/revogação. Browser real percorre pedido entregue → grupos → aprovação recusada por249/250kg → correção → prévia → aprovação → PDF → recarga; confere financeiro único e telas desktop/móvel. `tools/render_packing_list_review.py` gera PDFs sintéticos sem DB/rede/credenciais para inspeção visual com Poppler.

Resultados locais, CI e evidências serão registrados no PR. Skips locais não comprovam os casos reais. Embarques parciais/devoluções, assinatura/envio, dimensões calculadas, carga de dados comerciais, homologação com contas autorizadas e liberação em produção continuam fora desta entrega.


## Atualização: histórico completo em páginas

O fluxo HTTP agora rotaciona os eventos antigos em blocos no mesmo banco, mantendo uma janela recente limitada e a consulta de todas as revisões. Os limites locais mencionados acima continuam como proteção das funções internas e de dados inválidos; não exigem descartar alterações antigas para salvar uma nova revisão válida. Ver OPERATION_HISTORY.md para atomicidade da referência, permissões, limites de bytes, falhas/retry e pendências de durabilidade em produção.
