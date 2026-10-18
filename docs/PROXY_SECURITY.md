# Login e proxy reverso — validação pendente

O container inicia por `python serve.py`. Por padrão ignora cabeçalhos
encaminhados, inclusive `FORWARDED_ALLOW_IPS` herdado do ambiente. O login usa
`request.client.host`; o IP bruto não é salvo no contador de tentativas.

Somente após verificar a topologia, configurar `TRUSTED_PROXY_IPS` com os IPs
exatos dos proxies imediatamente anteriores ao backend, separados por vírgula.
Não usar `*`, sub-redes ou nomes DNS: o Uvicorn fixado em 0.25 usa IPs literais.
Sem IPs estáveis verificados, manter a configuração padrão e não declarar a
limitação individual por IP validada para produção.

O proxy deve sobrescrever X-Forwarded-For com o IP real do cliente ou acrescentar
o cliente à direita de uma cadeia sanitizada. A aplicação deve ser inacessível
por caminhos que permitam a um atacante se apresentar como proxy confiável.
Não confiar em um endereço compartilhado por workloads não confiáveis.

## Evidência necessária antes de integrar/publicar

1. Identificar o proxy, seus IPs de saída e todos os caminhos até o backend.
2. Confirmar como ele sobrescreve/acrescenta X-Forwarded-For.
3. Em ambiente isolado, verificar que dois clientes recebem limites separados.
4. Confirmar que cabeçalhos falsos enviados diretamente ou pelo proxy não mudam
   a identidade usada pelo limitador.
5. Confirmar 429 após 30 tentativas por IP e após 5 por conta na janela fixa de
   15 minutos, inclusive com workers concorrentes e MongoDB real.
6. Validar também o comando efetivo de inicialização: um override da hospedagem
   pode ignorar o entrypoint do Dockerfile.

Testes automatizados usam o middleware real do Uvicorn, sem infraestrutura,
contas de produção ou serviços pagos. Eles não comprovam a topologia publicada.
