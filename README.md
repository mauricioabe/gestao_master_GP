# Gestao de Projetos SAD

Primeira entrega do novo sistema independente de Gestao de Projetos SAD. A aplicacao permite cadastrar e acompanhar projetos, consultar contratos existentes no Radar Financeiro-Orcamentario e persistir os vinculos sem duplicar nem alterar os contratos de origem.

## Arquitetura

- Frontend: React 18, TypeScript, Material UI, TanStack Query e Vite.
- Backend: FastAPI, SQLAlchemy 2, Pydantic 2 e Alembic.
- Banco de escrita: MySQL 8, schema `gestao_projetos_sisfron`.
- Integracao: consulta direta e isolada ao schema `gestao_custos_sisfron`.

O stack e os padroes de navegacao seguem o Radar Financeiro. A interface usa uma identidade azul propria, inspirada na referencia visual fornecida.

## Protecao da base do Radar

O sistema nao cria tabelas, chaves estrangeiras, views, triggers, procedures ou qualquer outro objeto em `gestao_custos_sisfron`.

A integracao possui tres barreiras:

1. URL de conexao separada, destinada a um usuario MySQL com somente `SELECT`.
2. Cada conexao e aberta com `SET SESSION TRANSACTION READ ONLY`.
3. Um guard de SQL rejeita `INSERT`, `UPDATE`, `DELETE`, DDL e comandos de permissao antes da execucao.

Os IDs dos contratos e os dados necessarios para exibicao ficam em `project_contracts`, dentro de `gestao_projetos_sisfron`. Nao existem chaves estrangeiras entre schemas.

> A criacao do usuario MySQL de leitura deve ser feita por um DBA, fora deste projeto. Nenhum script deste repositorio concede ou altera permissoes na base de custos.

## Configuracao local

Requisitos: Python 3.12+, Node.js 20+ e MySQL 8.

1. Copie a configuracao local: `Copy-Item .env.example .env`.
2. Ajuste `COST_DATABASE_URL` no `.env` para um usuario com privilegio `SELECT` apenas.
3. Crie somente o novo schema com `mysql -u root -p < database/bootstrap.sql`.
4. No backend, execute `pip install -e ".[test]"`, `alembic upgrade head` e `uvicorn app.main:app --reload --port 8011`.
5. Antes do primeiro acesso, crie o Gestor do Programa com `python scripts_create_manager.py`, dentro da pasta `backend`.
6. No frontend, execute `npm install` e `npm run dev`.

Interface: `http://localhost:5174`  
Documentacao da API: `http://localhost:8011/docs`

## Funcionalidades entregues

- painel gerencial com quantitativos e progresso medio;
- cadastro, edicao, busca e filtro de projetos;
- situacao, prioridade, responsavel, periodo e percentual de progresso;
- consulta de contratos diretamente no Radar;
- vinculo N:N entre projetos e contratos, sem duplicar o cadastro de contratos;
- layout responsivo com menu no padrao estrutural do Radar;
- autenticacao JWT, sessao protegida e administracao de usuarios;
- controle de acesso por perfil para Gestor do Programa, Gerente de Projetos, Supervisor do Projeto, Analista de Projetos e Equipe de Projeto;
- modulos futuros sinalizados no menu para a evolucao incremental.

## Perfis e permissoes

- **Gestor do Programa:** acesso integral e administracao de usuarios.
- **Gerente de Projetos:** gerencia projetos, subprojetos, cronogramas e documentos.
- **Supervisor do Projeto:** consulta projetos e gerencia subprojetos, cronogramas e documentos.
- **Analista de Projetos:** consulta projetos e gerencia subprojetos, cronogramas e documentos.
- **Equipe de Projeto:** consulta projetos e atualiza cronogramas.

Defina um `JWT_SECRET` exclusivo e seguro no `.env` antes de disponibilizar o sistema em producao. O token expira conforme `JWT_EXPIRE_MINUTES`.

## Validacao

```powershell
cd backend
pytest
cd ..\frontend
npm run build
```

Os testes do backend incluem a verificacao explicita de que comandos de escrita e DDL sao bloqueados na conexao da base de custos.

## Proximas etapas

- integracao da autenticacao ao provedor de identidade institucional;
- indicadores historicos e alertas;
- relatorios e exportacoes.
