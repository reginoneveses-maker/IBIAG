# Pausa de pesquisa externa e consumo de créditos

`ALLOW_PAID_DISCOVERY` tem padrão `false`. Sem configuração explícita `true`
no servidor, ficam bloqueadas novas pesquisas externas, jobs, repetições, busca
de decisores e enriquecimento de leads. O cliente não pode habilitar o recurso
por JSON, query string ou papel administrativo. A resposta explica que pesquisas
externas estão pausadas; não expõe chaves ou detalhes do provedor.

Salvar um candidato no CRM continua disponível: preserva os contatos enviados,
registra o enriquecimento como pausado e não chama o provedor. Consultar resultados
anteriores e solicitar cancelamento continuam permitidos, com autenticação.

Esta mudança não habilita a variável na hospedagem. Ativá-la exige autorização
explícita do responsável pelos custos e validação da conta do provedor. A flag
não substitui quotas por usuário, orçamento/limites no provedor nem auditoria.
Não cancela automaticamente trabalhos já iniciados por uma versão anterior e
não suspende a cobrança de infraestrutura que já estava em execução.

Testes exercitam os endpoints com provedores substituídos e verificam ausência
de chamadas quando desabilitado. A fixture de navegador e os testes de pesquisa
habilitam apenas seus provedores falsos para preservar as regressões; isso não
habilita o serviço na produção. Não são consultadas credenciais reais.
