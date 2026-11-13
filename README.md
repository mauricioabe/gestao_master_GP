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
- ciclo de vida dos subprojetos no cadastro e na grade: Iniciação, Concepção,
  Contratação, Concp/Contç, Em produção, Implantação, Entrega e Encerrado;
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
- **Coordenador de Projetos e Chefe Ass Pjt:** gerenciam projetos, subprojetos,
  cronogramas e documentos, com as mesmas permissões do Gerente de Projetos.
- **Supervisor do Projeto:** consulta projetos e gerencia subprojetos, cronogramas e documentos.
- **Analista de Projetos:** consulta projetos e gerencia subprojetos, cronogramas e documentos.
- **Analista de licitações e Analista de contratos:** mesmas permissões do Analista
  de Projetos, sem administração de usuários.
- **Auditor interno:** acesso somente de consulta, sem alterar cadastros, equipes,
  cronogramas, documentos ou Diário de Bordo.
- **Equipe de Projeto:** consulta projetos e atualiza cronogramas.

Defina um `JWT_SECRET` exclusivo e seguro no `.env` antes de disponibilizar o sistema em producao. O token expira conforme `JWT_EXPIRE_MINUTES`.

O cadastro de usuários possui as modalidades Civil e Militar. Civil mantém os
campos existentes. Militar também exige posto e nome de guerra; as siglas iniciais
são Ten, Cap, Maj, TC, Cel, Cel R1 e Gen Bda. O nome completo é preservado, e a
identificação exibida utiliza posto seguido de nome de guerra (ex.: `Cap Silva`).
Os usuários anteriores à migração `0015_user_military_identity` permanecem como
civis até que o cadastro seja atualizado. Alterações de identificação aparecem na
sessão do usuário no próximo login.

Na seção **Gerência e situação** do subprojeto, o gerente pode ser selecionado
entre os usuários civis ativos. O campo **Responsável Militar** lista os militares
ativos como `Posto Nome de guerra · Perfil`, por exemplo `Cap Silva · Coordenador
de Projetos`. Ambos os vínculos são persistidos por ID de usuário; os nomes de
gerentes cadastrados anteriormente permanecem preservados. Usuários desativados
continuam visíveis nos vínculos existentes, mas não aparecem para novas seleções.

## Validacao

```powershell
cd backend
pytest
cd ..\frontend
npm run build
```

Os testes do backend incluem a verificacao explicita de que comandos de escrita e DDL sao bloqueados na conexao da base de custos.

## Diário de Bordo

### Integrantes dos projetos e subprojetos

O botão **Integrantes** nos detalhes de um projeto ou subprojeto abre a equipe
vinculada àquele cadastro. A mesma função está disponível no Diário de Bordo,
mantendo o contexto do subprojeto aberto; na visão geral, escolha o projeto ou
subprojeto antes de adicionar integrantes.

Selecione usuários ativos já cadastrados e use **Adicionar integrante**. Uma
pessoa pode participar de vários projetos e subprojetos, com listas independentes.
**Remover vínculo** retira a pessoa somente da equipe selecionada e preserva seu
cadastro, os demais vínculos e os históricos. Usuários inativados continuam nas
equipes existentes com indicação de inatividade.

As permissões seguem o cadastro pai: gerenciar projetos para suas equipes e
gerenciar subprojetos para as equipes dos subprojetos. Os demais perfis consultam
as equipes. A migração `0018_project_subproject_members` cria as associações;
integrantes antigos sem contexto não são distribuídos automaticamente. Ao
adicionar um integrante à equipe, seu usuário também fica disponível como
responsável no Diário de Bordo.

O módulo está disponível no menu **Diário de Bordo** (`/diarios`) e nos detalhes de
cada subprojeto, pelo botão superior ou pela seção abaixo dos contratos.

O campo **Relatores** permite selecionar várias pessoas das equipes dos projetos
ou subprojetos vinculados ao assunto. A API também valida esse vínculo: usuários
ativos sem participação nessas equipes não podem ser indicados como novos relatores.
Nos assuntos globais, as opções são os integrantes ativos de equipes de projetos
ou subprojetos. A migração `0019_logbook_relators` preserva cada responsável anterior
como relator. Relatores históricos podem ser mantidos quando a abrangência não muda,
mesmo após inativação ou saída da equipe. Cards, detalhes e busca exibem todos os
relatores selecionados.
Um assunto pode envolver vários projetos e subprojetos. A abrangência é calculada
pelos projetos distintos envolvidos: nenhum = Global, um = Projeto, dois ou mais =
Multi-projeto. Assuntos globais aparecem na visão geral; a visão de um subprojeto
mostra os assuntos explicitamente vinculados a ele.

Defina os responsáveis em **Integrantes**, no painel do diário ou no formulário
do assunto, selecionando usuários já cadastrados no sistema. Nome, posto, nome de
guerra e perfil são carregados do cadastro do usuário; não precisam ser redigitados.
Cada usuário possui um único vínculo de integrante. Os registros anteriores à
migração `0017_team_member_users` permanecem nos históricos e podem ser associados
explicitamente a um usuário. Integrantes e usuários inativos permanecem nos
históricos, mas não podem ser escolhidos como novos responsáveis. O autor dos
fatos continua sendo o usuário autenticado que realizou o registro.

Os perfis que gerenciam subprojetos também mantêm o diário e os integrantes; a Equipe
de Projeto tem acesso de consulta e download. A API valida as mesmas permissões da
interface. Fechar exige data de fim. Assuntos fechados ou cancelados não admitem
reabertura, edição, exclusão ou alterações em ocorrências, anexos e relacionamentos.
Um vínculo com assunto encerrado também impede excluir o assunto relacionado.

As ocorrências possuem data do fato independente do cadastro, tipo, referências e
anexos. A linha do tempo integrada do subprojeto reúne seus assuntos e permite
filtrar por assunto, tipo e período. Datas e horas de fatos são apresentadas no
fuso `America/Sao_Paulo` e armazenadas em UTC; datas de abertura e encerramento são
datas civis. Textos são exibidos como texto pelo React, sem interpretar HTML.

### Instalação e arquivos

Após atualizar as dependências Python, execute `alembic upgrade head` em `backend`.
A migração `0013_logbooks` cria apenas as tabelas do módulo na base de projetos.
Execute `npm run build` em `frontend`. No Docker, a migração roda na inicialização
do backend e o volume `logbook_storage` preserva os anexos.

Os arquivos ficam em `private_storage/logbook_items`, fora da pasta pública
`storage`. Inclua essa pasta (ou o volume Docker) no backup junto com o MySQL.
Downloads passam por `/api/logbook-attachments/{id}/download` e exigem autenticação.

Extensões aceitas: PDF, JPG/JPEG, PNG, TIF/TIFF, DOCX, XLSX, PPTX e MPP;
áudios MP3, WAV, OGG, M4A, AAC e FLAC; vídeos MP4, WEBM, MOV e AVI.
Áudios e vídeos utilizam os mesmos limites de tamanho e downloads autenticados
dos demais anexos. Não há conversão ou transcrição dos arquivos.
O conteúdo é verificado por assinatura e, no caso dos formatos Office Open XML,
pela estrutura ZIP esperada. Todos os arquivos são validados antes da persistência
da ocorrência; falhas de gravação desfazem a transação e limpam os novos arquivos.
Exclusões autorizadas removem também os arquivos físicos; falhas do sistema de
arquivos ficam registradas no log para manutenção.

`LOGBOOK_MAX_UPLOAD_SIZE` define o limite por arquivo (padrão 20 MB) e
`LOGBOOK_MAX_BATCH_SIZE` o limite por envio (padrão 100 MB), em bytes. Cada envio
aceita até 20 anexos. O Nginx aceita requisições de até 110 MB para comportar o lote
e o envelope multipart; ajuste esse limite se aumentar os valores do backend.

Esta entrega não inclui consolidação com IA ou integração com Ollama.

### Verificação

Execute `pytest` em `backend` e `npm run build` em `frontend`. Os testes do diário
usam SQLite isolado e cobrem escopo, permissões, bloqueios de encerramento,
uploads, downloads autenticados, relacionamentos e cronologia retroativa.

## Proximas etapas

- integracao da autenticacao ao provedor de identidade institucional;
- indicadores historicos e alertas;
- relatorios e exportacoes.
