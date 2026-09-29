# AgroBrasil Export CRM & Trade Intelligence — PRD

## Original Problem Statement
Preciso criar um app para prospecção de clientes pro meu negócio, eu vendo ingredientes do Brasil, ex: pó de acerola de açaí, sucos e pires de frutas tropicais, água de coco e seus derivados, nuts do brasil.

## User Choices (Feb 2026)
- Escopo: CRM completo + catálogo digital + busca de leads
- Público alvo: Indústria de bebidas, cosméticos, food service, distribuidores/importadores internacionais
- Templates manuais (sem IA)
- Sem autenticação (uso pessoal)
- Bilíngue PT/EN
- Extra: Buscar dados de exportação para descobrir compradores globais

## Personas
- Exportador brasileiro de ingredientes tropicais premium (dono do negócio, uso interno)

## Core Requirements
- Dashboard com KPIs (leads ativos, pipeline USD, taxa conversão, amostras enviadas)
- Catálogo bilíngue com HS Code, MOQ, embalagem, certificações, preço FOB/CIF
- Pipeline Kanban 6 estágios com filtros de indústria e busca
- Cadastro/edição/exclusão de leads + histórico de interações
- Biblioteca de templates PT/EN (introdução, follow-up, amostra, cotação)
- Inteligência de comércio exterior (registros de importadores globais) com "Adicionar ao CRM"
- Tarefas & follow-ups com data
- Toggle global PT/EN

## Implemented (2026-02-29)
- Backend FastAPI: /products, /leads, /interactions, /tasks, /templates, /trade-data, /dashboard/stats, /seed
- Frontend React: 6 páginas (Dashboard, Catalog, Pipeline, TradeIntel, Templates, Tasks)
- Design forest green (#0F382C) + amber ochre + warm sand, fontes Cabinet Grotesk + Inter + JetBrains Mono
- Seed automático de 8 produtos, 8 templates bilíngues, 12 registros de trade, 3 leads iniciais

## Backlog (P1/P2)
- P1: Drag-and-drop verdadeiro no Kanban (hoje via dropdown de estágio)
- P1: Export para CSV/PDF do pipeline
- P2: Integração real com ComexStat (dados oficiais MDIC)
- P2: Envio direto de email/WhatsApp via templates
- P2: Anexo de COAs e fichas técnicas nos produtos
