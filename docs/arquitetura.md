# Arquitetura e modelo de integracao

## Limites de responsabilidade

| Componente | Responsabilidade | Acesso a dados |
|---|---|---|
| Frontend React | Navegacao, formularios e paineis | API HTTP apenas |
| API FastAPI | Regras de projetos e vinculos | Duas sessoes isoladas |
| `gestao_projetos_sisfron` | Projetos e vinculos | Leitura e escrita |
| `gestao_custos_sisfron` | Origem oficial dos contratos | Somente leitura |

## Integracao dos contratos

O relacionamento validado para a primeira entrega e N:N: um projeto pode utilizar varios contratos e um contrato pode estar associado a varios projetos. O identificador oficial `contrato.cod_contrato` e preservado em `project_contracts.external_contract_id`.

O vinculo inclui um snapshot descritivo para rastreabilidade, mas a lista de contratos disponiveis sempre e consultada na origem. Nao ha FK entre schemas, evitando acoplamento de implantacao e qualquer necessidade de modificar a base do Radar.

## Modelo inicial

- `projects`: cadastro e acompanhamento do projeto.
- `project_contracts`: vinculo local com o identificador externo do contrato.

As migracoes Alembic utilizam exclusivamente `PROJECT_DATABASE_URL`, cuja validacao exige o nome `gestao_projetos_sisfron`. A URL de custos e usada somente pela engine protegida de consulta.

## Decisoes para evolucao

- Reaproveitar regras de negocio do `mc2-project`, mas reconstruir os modulos no stack do Radar.
- Migrar dados por modulo, com conciliacao e rollback documentados.
- Implementar atividades e dependencias depois da validacao do cadastro e dos vinculos desta entrega.
- Adicionar autenticacao/RBAC antes da abertura para usuarios finais.

