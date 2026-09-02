# REQUIREMENTS.md — InfraManager

## 1. Objetivo

O InfraManager será uma aplicação web segura para gerenciamento de infraestrutura de TI, com foco em:

- ativos de TI;
- máquinas virtuais;
- datacenters;
- salas;
- racks;
- usuários e perfis de acesso;
- autenticação com MFA;
- auditoria de ações.

O sistema será desenvolvido em Python utilizando Flask e deverá aplicar princípios de Secure by Design e Secure by Default.

O projeto também deverá atender aos requisitos acadêmicos de infraestrutura em nuvem, versionamento, desenvolvimento seguro e CI/CD.

---

# 2. Escopo do MVP

O MVP deverá possuir os seguintes módulos:

1. Autenticação
2. MFA
3. Dashboard
4. Gestão de Ativos
5. Gestão de Máquinas Virtuais
6. Gestão de Datacenters
7. Gestão de Salas
8. Gestão de Racks
9. Gestão de Usuários
10. Controle de Acesso — RBAC
11. Auditoria
12. Pesquisa e filtros

Funcionalidades fora desse escopo somente deverão ser implementadas após a conclusão integral do MVP.

---

# 3. Perfis de Usuário

O sistema deverá possuir inicialmente três perfis.

## 3.1 Administrador

O Administrador poderá:

- acessar todas as funcionalidades;
- cadastrar ativos;
- editar ativos;
- excluir ativos;
- cadastrar máquinas virtuais;
- editar máquinas virtuais;
- excluir máquinas virtuais;
- administrar datacenters;
- administrar salas;
- administrar racks;
- cadastrar usuários;
- editar usuários;
- alterar perfis;
- habilitar/desabilitar usuários;
- consultar logs de auditoria.

---

## 3.2 Operador

O Operador poderá:

- visualizar Dashboard;
- visualizar ativos;
- cadastrar ativos;
- editar ativos;
- visualizar máquinas virtuais;
- cadastrar máquinas virtuais;
- editar máquinas virtuais;
- visualizar datacenters;
- visualizar salas;
- visualizar racks.

O Operador não poderá:

- excluir registros críticos;
- administrar usuários;
- alterar permissões;
- consultar configurações administrativas sensíveis.

---

## 3.3 Consulta

O usuário de Consulta poderá:

- visualizar Dashboard;
- visualizar ativos;
- visualizar máquinas virtuais;
- visualizar datacenters;
- visualizar salas;
- visualizar racks;
- pesquisar;
- utilizar filtros.

O perfil Consulta não poderá criar, editar ou excluir registros.

---

# 4. Requisitos Funcionais

## RF-001 — Login

O sistema deverá possuir uma tela de Login.

Campos:

- usuário;
- senha.

O sistema deverá validar as credenciais no servidor.

Em caso de credencial inválida, deverá apresentar mensagem genérica.

Exemplo:

> Usuário ou senha inválidos.

O sistema não deverá informar se o usuário existe ou não.

---

## RF-002 — MFA

Após a validação correta de usuário e senha, todos os usuários deverão concluir a validação por código TOTP. O MFA é obrigatório, sem exceção por perfil.

Fluxo:

```text
Usuário + senha
      ↓
Credenciais válidas
      ↓
MFA configurado?
   ┌──────┴──────┐
   │             │
  Não           Sim
   │             │
   ▼             ▼
Configuração  Código TOTP
e confirmação    │
   └──────┬──────┘
          ▼
      Dashboard
```

O código deverá possuir validade temporal.

O usuário não deverá receber sessão autenticada definitiva nem acessar o Dashboard antes da confirmação de um TOTP válido.

---

## RF-003 — Ativação de MFA

No primeiro acesso, o usuário que ainda não possuir MFA configurado deverá ser direcionado obrigatoriamente para a configuração do MFA antes do Dashboard.

Durante a ativação:

1. o sistema deverá gerar um segredo TOTP;
2. deverá apresentar QR Code;
3. o usuário deverá cadastrar o QR Code em aplicativo compatível;
4. deverá informar um código válido;
5. somente após a confirmação o MFA será considerado ativo.

O MFA é um requisito adicional de segurança definido pelo projeto InfraManager. Não é uma exigência direta do professor ou do enunciado acadêmico.

---

## RF-004 — Códigos de Recuperação

O sistema deverá permitir a geração de códigos de recuperação do MFA.

Requisitos:

- códigos devem ser de uso único;
- códigos não deverão ser armazenados em texto puro;
- após utilizados deverão ser invalidados.

---

## RF-005 — Logout

O sistema deverá possuir botão de Logout.

Ao realizar Logout:

- a sessão deverá ser invalidada;
- o usuário deverá ser redirecionado para a tela de Login;
- páginas protegidas não deverão permanecer acessíveis.

---

# 5. Dashboard

## RF-006 — Dashboard Geral

Após autenticação, o usuário deverá acessar o Dashboard.

O Dashboard deverá apresentar pelo menos:

- total de ativos;
- total de máquinas virtuais;
- total de datacenters;
- total de racks;
- quantidade de ativos ativos;
- quantidade de ativos em manutenção;
- quantidade de VMs ligadas;
- quantidade de VMs desligadas.

---

## RF-007 — Últimos Registros

O Dashboard deverá apresentar uma lista dos últimos registros cadastrados ou modificados.

Exemplo:

```text
Últimas alterações

VM-APP-01       Atualizada
HOST-ESXI-03    Cadastrado
SW-CORE-01      Alterado
RACK-04         Cadastrado
```

---

# 6. Gestão de Ativos

## RF-008 — Listar Ativos

O sistema deverá possuir página para listagem dos ativos cadastrados.

A listagem deverá apresentar pelo menos:

- hostname;
- patrimônio;
- tipo;
- fabricante;
- modelo;
- endereço IP;
- localização;
- status.

---

## RF-009 — Cadastrar Ativo

Usuários autorizados deverão poder cadastrar ativos.

Campos:

- patrimônio;
- hostname;
- tipo;
- fabricante;
- modelo;
- número de série;
- endereço IP;
- sistema operacional;
- setor;
- responsável;
- localização;
- status;
- observações.

---

## RF-010 — Tipos de Ativos

O sistema deverá permitir inicialmente os seguintes tipos:

- Servidor;
- Storage;
- Switch;
- Firewall;
- Access Point;
- Notebook;
- Desktop;
- Appliance;
- Outro.

---

## RF-011 — Status de Ativo

Um ativo poderá possuir os seguintes status:

- Ativo;
- Em manutenção;
- Reserva;
- Desativado.

---

## RF-012 — Visualizar Ativo

O usuário deverá poder acessar os detalhes completos de um ativo.

---

## RF-013 — Editar Ativo

Usuários autorizados poderão modificar os dados de um ativo.

A alteração deverá gerar evento de auditoria.

---

## RF-014 — Excluir Ativo

Somente usuários autorizados poderão excluir ativos.

A exclusão deverá:

- exigir confirmação;
- validar permissão;
- gerar registro de auditoria.

---

## RF-015 — Pesquisa de Ativos

O usuário deverá poder pesquisar ativos por:

- hostname;
- patrimônio;
- número de série;
- endereço IP;
- fabricante;
- modelo.

---

## RF-016 — Filtro de Ativos

O sistema deverá permitir filtro por:

- tipo;
- status;
- localização;
- fabricante.

---

# 7. Gestão de Máquinas Virtuais

## RF-017 — Listar Máquinas Virtuais

A página de VMs deverá apresentar:

- hostname;
- IP;
- sistema operacional;
- ambiente;
- vCPU;
- memória;
- host;
- status.

---

## RF-018 — Cadastrar Máquina Virtual

Campos:

- nome;
- hostname;
- endereço IP;
- sistema operacional;
- ambiente;
- vCPU;
- memória RAM;
- armazenamento;
- aplicação;
- responsável;
- cluster;
- host;
- status;
- observações.

---

## RF-019 — Ambiente da VM

A VM poderá pertencer a:

- Produção;
- Homologação;
- Desenvolvimento;
- Teste.

---

## RF-020 — Status da VM

Valores iniciais:

- Ligada;
- Desligada;
- Manutenção;
- Descomissionada.

---

## RF-021 — Editar Máquina Virtual

Usuários autorizados deverão poder modificar os dados da VM.

Toda alteração deverá gerar log de auditoria.

---

## RF-022 — Excluir Máquina Virtual

Somente perfis autorizados poderão excluir uma VM.

A operação deverá exigir confirmação.

---

## RF-023 — Pesquisa de Máquinas Virtuais

Pesquisa por:

- nome;
- hostname;
- IP;
- aplicação;
- responsável.

---

## RF-024 — Filtros de Máquinas Virtuais

Filtros:

- ambiente;
- status;
- sistema operacional;
- host.

---

# 8. Datacenter

O módulo de Datacenter deverá oferecer CRUD completo: cadastrar, listar, visualizar detalhes, editar e excluir, sempre com autorização server-side, validação, CSRF nas escritas, tratamento de dependências e auditoria.

## RF-025 — Cadastro de Datacenter

Campos:

- nome;
- código;
- localização;
- descrição;
- status.

---

## RF-026 — Listar Datacenters

O sistema deverá apresentar:

- nome;
- localização;
- quantidade de salas;
- quantidade de racks;
- status.

---

## RF-027 — Editar Datacenter

Usuários autorizados poderão modificar os dados.

---

## RF-028 — Excluir Datacenter

A exclusão deverá verificar se existem dependências.

Um datacenter com salas ou racks associados não deverá ser excluído sem tratamento adequado.

---

# 9. Salas

O módulo de Sala deverá oferecer CRUD completo: cadastrar, listar, visualizar detalhes, editar e excluir, sempre com autorização server-side, validação, CSRF nas escritas, tratamento de dependências e auditoria.

## RF-029 — Cadastro de Sala

Campos:

- nome;
- datacenter;
- descrição;
- status.

---

## RF-030 — Relacionamento Datacenter/Sala

Toda sala deverá obrigatoriamente pertencer a um datacenter.

A listagem deverá permitir consultar as salas e seus respectivos datacenters. A visualização deverá mostrar os detalhes da sala. A edição deverá preservar um relacionamento válido, e a exclusão deverá verificar racks dependentes antes de prosseguir.

---

# 10. Racks

O módulo de Rack deverá oferecer CRUD completo: cadastrar, listar, visualizar detalhes, editar e excluir, sempre com autorização server-side, validação, CSRF nas escritas, tratamento de dependências e auditoria.

## RF-031 — Cadastro de Rack

Campos:

- nome;
- código;
- datacenter;
- sala;
- quantidade de U;
- descrição;
- status.

---

## RF-032 — Relacionamento Rack/Sala

Todo rack deverá pertencer a uma sala.

---

## RF-033 — Visualização de Rack

A primeira versão deverá apresentar informações textuais e equipamentos relacionados.

Visualização gráfica de unidades U não faz parte do MVP.

A listagem deverá permitir consultar racks, sala e datacenter. A edição deverá validar capacidade e relacionamentos. A exclusão deverá verificar ativos dependentes antes de prosseguir.

---

# 11. Usuários

## RF-034 — Cadastro de Usuários

Somente administradores poderão criar usuários.

Campos:

- nome;
- username;
- e-mail;
- perfil;
- status.

O perfil será armazenado diretamente em `User.role`, restrito aos valores `ADMIN`, `OPERATOR` e `VIEWER`. Não haverá entidade ou tabela `Role` separada no MVP.

A senha inicial deverá seguir política de segurança definida pelo sistema.

---

## RF-035 — Editar Usuário

Administradores poderão:

- editar nome;
- editar e-mail;
- alterar perfil;
- habilitar usuário;
- desabilitar usuário.

---

## RF-036 — Desabilitar Usuário

Usuários deverão preferencialmente ser desabilitados em vez de excluídos.

Usuário desabilitado não poderá realizar login.

---

## RF-037 — Alteração de Senha

O usuário deverá poder alterar sua própria senha.

O Administrador poderá iniciar processo de redefinição sem visualizar a senha atual do usuário.

---

# 12. RBAC

## RF-038 — Verificação de Permissão

Toda ação administrativa deverá verificar a autorização no servidor.

Não será permitido depender apenas da ocultação de botões no Front-end.

Exemplo:

Mesmo que um usuário tente acessar diretamente:

```text
/assets/10/delete
```

o servidor deverá verificar sua permissão antes de realizar a operação.

---

# 13. Auditoria

## RF-039 — Registro de Eventos

Deverão ser registrados pelo menos:

- Login bem-sucedido;
- Login falho;
- Logout;
- falha de MFA;
- ativação de MFA;
- desativação de MFA;
- criação de usuário;
- alteração de usuário;
- criação de ativo;
- alteração de ativo;
- exclusão de ativo;
- criação de VM;
- alteração de VM;
- exclusão de VM;
- alterações em datacenters;
- alterações em salas;
- alterações em racks.

Eventos críticos ou repetidos deverão alimentar um mecanismo simples de alertas de segurança. No MVP, múltiplas falhas de Login/MFA, bloqueios por rate limiting e tentativas de acesso administrativo negadas deverão gerar alerta com severidade `WARNING` ou `CRITICAL`, visível para Administradores em uma lista de alertas recentes. Integrações externas não são obrigatórias.

---

## RF-040 — Dados do Evento de Auditoria

Um evento deverá possuir pelo menos:

- data/hora;
- usuário;
- ação;
- recurso;
- identificador do recurso;
- endereço IP;
- resultado.

---

## RF-041 — Visualização da Auditoria

Somente Administradores deverão poder visualizar os logs completos de auditoria.

---

# 14. Requisitos Não Funcionais

## RNF-001 — Linguagem

Backend desenvolvido em Python.

---

## RNF-002 — Framework

Utilização de Flask.

---

## RNF-003 — Banco de Dados

O MVP deverá utilizar SQLite.

A camada de persistência deverá utilizar SQLAlchemy ORM.

---

## RNF-004 — Migrations

Alterações no banco deverão utilizar Flask-Migrate/Alembic.

---

## RNF-005 — Interface

A aplicação deverá possuir interface Web responsiva.

Poderão ser utilizados:

- HTML;
- CSS;
- Bootstrap;
- Jinja2.

---

## RNF-006 — HTTPS

Em produção, todo acesso deverá utilizar HTTPS.

HTTP deverá ser redirecionado para HTTPS.

Esse requisito está diretamente alinhado ao eixo de infraestrutura da atividade. fileciteturn0file0L37-L46

---

## RNF-007 — Sessões

Sessões deverão utilizar configurações seguras.

Quando aplicável:

- Secure;
- HttpOnly;
- SameSite.

---

## RNF-008 — CSRF

Formulários que modifiquem dados deverão possuir proteção contra CSRF.

---

## RNF-009 — Password Hashing

Senhas nunca deverão ser armazenadas em texto puro.

---

## RNF-010 — Rate Limiting

Rotas sensíveis deverão possuir limitação de requisições.

Especialmente:

```text
/login
/mfa
/password-reset
```

---

## RNF-011 — Validação

Todo dado proveniente do usuário deverá passar por validação server-side.

---

## RNF-012 — Tratamento de Erros

A aplicação não deverá exibir ao usuário:

- stack traces;
- caminhos internos;
- variáveis de ambiente;
- consultas SQL;
- informações sensíveis.

---

## RNF-013 — Secrets

Credenciais e segredos não deverão estar presentes no código-fonte.

---

## RNF-014 — GitHub

O projeto deverá possuir repositório público no GitHub, conforme exigido pela atividade. fileciteturn0file0L50-L69

A conta GitHub utilizada no projeto deverá possuir 2FA habilitado. Push, pull e deploy deverão utilizar autenticação segura por chave SSH protegida ou Personal Access Token (PAT) de escopo mínimo; a senha da conta não deverá ser utilizada para operações Git.

---

## RNF-015 — `.gitignore`

O projeto deverá impedir commit de:

```text
.env
*.key
*.pem
*.db
.venv/
__pycache__/
```

---

# 15. Requisitos OWASP

A atividade exige a mitigação de pelo menos três categorias OWASP Top 10:2025. fileciteturn0file0L91-L97

O InfraManager deverá priorizar:

## A01:2025 — Broken Access Control

Controles:

- autenticação obrigatória;
- RBAC;
- deny-by-default;
- proteção server-side;
- validação de acesso a recursos.

---

## A05:2025 — Injection

Controles:

- SQLAlchemy ORM;
- queries parametrizadas;
- validação de entrada;
- escaping de saída;
- proibição de concatenação insegura de SQL.

---

## A07:2025 — Authentication Failures

Controles:

- password hashing;
- MFA;
- rate limiting;
- sessão segura;
- Logout;
- mensagens genéricas;
- controle de tentativas.

---

## A09:2025 — Security Logging & Alerting Failures

Controles:

- logs de autenticação;
- logs de alterações;
- logs de exclusões;
- logs de MFA;
- auditoria administrativa.
- alertas administrativos para eventos críticos ou repetidos;
- registro de severidade, contagem, data/hora e estado de revisão do alerta.

---

# 16. Infraestrutura

## RNF-016 — Cloud

Produção hospedada na Oracle Cloud Infrastructure utilizando recursos gratuitos.

Deverão ser coletadas evidências da criação e da operação de: compartment, VCN, subnet pública, internet gateway, security list e/ou NSG, criação da instância, IP público atribuído e instância no estado `Running`/em execução.

---

## RNF-017 — Sistema Operacional

A VM deverá utilizar Ubuntu Server em versão estável compatível com o requisito acadêmico.

O enunciado permite obrigatoriamente Ubuntu Server ou Debian. fileciteturn0file0L31-L34

---

## RNF-018 — Servidor Web

Utilização de Nginx.

---

## RNF-019 — Application Server

Utilização de Gunicorn para executar a aplicação Flask.

O ponto de entrada WSGI padronizado para referências e comandos de produção será `wsgi.py`.

---

## RNF-020 — SSH

A administração do servidor deverá utilizar autenticação por chave SSH.

Autenticação por senha deverá permanecer desabilitada.

---

## RNF-021 — Fail2Ban

Fail2Ban deverá proteger o SSH.

Configuração mínima exigida:

```text
maxretry = 4
bantime = 24h
```

Essa configuração decorre diretamente do requisito da atividade. fileciteturn0file0L41-L42

---

## RNF-022 — Firewall

Somente portas necessárias deverão ser expostas.

Inicialmente:

```text
22/tcp
80/tcp
443/tcp
```

---

## RNF-023 — Certificado

Utilização de Let's Encrypt com Certbot `>= 5.4` para emissão de certificado destinado ao IP público.

O certificado de IP deverá usar o perfil `shortlived` e um método suportado, preferencialmente `webroot`, com instalação explícita no Nginx. A renovação frequente deverá ser automatizada e incluir recarga segura do Nginx por `deploy-hook`.

---

## RNF-024 — SSL Labs

A implantação deverá obter:

```text
Qualys SSL Labs: A
PQC: habilitado
```

fileciteturn0file0L43-L46

---

# 17. CI/CD

## RNF-025 — GitHub Actions

O projeto deverá possuir pipeline no GitHub Actions.

---

## RNF-026 — Trigger

Push para:

```text
main
```

deverá iniciar a pipeline automaticamente, conforme exigência acadêmica. fileciteturn0file0L101-L129

---

## RNF-027 — Pipeline

Pipeline inicial:

```text
Checkout
   ↓
Python Setup
   ↓
Dependências
   ↓
Lint
   ↓
Testes
   ↓
Security Checks
   ↓
Deploy OCI
   ↓
Health Check
```

---

## RNF-028 — Bloqueio de Deploy

Falha em testes críticos deverá impedir o deploy.

---

## RNF-029 — GitHub Secrets

Credenciais utilizadas pela pipeline deverão permanecer em GitHub Secrets.

---

# 18. Testes

## RNF-030 — Pytest

Testes automatizados deverão utilizar pytest.

---

## RNF-031 — Testes de Autenticação

Testar:

- Login válido;
- Login inválido;
- usuário desabilitado;
- Logout;
- rota protegida;
- MFA válido;
- MFA inválido.

---

## RNF-032 — Testes de RBAC

Testar que:

- Administrador possui acesso administrativo;
- Operador não consegue executar operações proibidas;
- Consulta não consegue modificar dados;
- acesso direto por URL não contorna as permissões.

---

## RNF-033 — Testes CRUD

Testar:

- criação;
- leitura;
- atualização;
- exclusão;
- validação.

---

# 19. Desenvolvimento Assistido por IA

## RNF-034 — Ambiente

O desenvolvimento deverá utilizar ambiente com IA integrada.

Planejado:

```text
Visual Studio Code
+
OpenAI Codex
```

O requisito acadêmico prevê Antigravity ou ambiente similar baseado em IA. fileciteturn0file0L83-L85

---

## RNF-035 — Uso da IA

IA deverá ser utilizada para:

- planejamento;
- implementação;
- testes;
- revisão;
- refatoração;
- auditoria de segurança.

---

## RNF-036 — Evidências

O projeto deverá manter evidências das principais interações de desenvolvimento assistido por IA.

---

# 20. Critérios de Aceite do MVP

O MVP será considerado funcional quando:

- [ ] usuário conseguir realizar Login;
- [ ] MFA estiver operacional;
- [ ] primeiro acesso exigir configuração e confirmação do MFA antes do Dashboard;
- [ ] Logout funcionar;
- [ ] Dashboard estiver protegido;
- [ ] RBAC estiver funcionando;
- [ ] CRUD de Ativos estiver completo;
- [ ] CRUD de Máquinas Virtuais estiver completo;
- [ ] CRUD completo de Datacenter estiver funcionando;
- [ ] CRUD completo de Sala estiver funcionando;
- [ ] CRUD completo de Rack estiver funcionando;
- [ ] pesquisa estiver funcionando;
- [ ] filtros estiverem funcionando;
- [ ] logs de auditoria estiverem funcionando;
- [ ] alertas simples de segurança estiverem funcionando;
- [ ] testes automatizados estiverem aprovados;
- [ ] aplicação estiver publicada na OCI;
- [ ] evidências de compartment, VCN, subnet, internet gateway, security list/NSG, criação da instância, IP público e estado em execução estiverem organizadas;
- [ ] Nginx estiver configurado;
- [ ] HTTPS estiver funcionando;
- [ ] Certbot `>= 5.4` estiver emitindo e renovando o certificado do IP público;
- [ ] HTTP estiver redirecionando para HTTPS;
- [ ] SSH utilizar somente chave;
- [ ] Fail2Ban estiver ativo;
- [ ] SSL Labs apresentar Nota A;
- [ ] PQC estiver confirmado;
- [ ] GitHub Actions estiver realizando deploy automático;
- [ ] nenhum segredo estiver presente no repositório;
- [ ] GitHub 2FA estiver habilitado e Git utilizar SSH ou PAT de escopo mínimo;
- [ ] OWASP estiver documentado;
- [ ] README da entrega estiver completo.

---

# 21. Restrições

Durante o MVP, não deverão ser adicionados sem necessidade:

- Docker;
- Kubernetes;
- Redis;
- PostgreSQL;
- API REST pública;
- React;
- microserviços;
- Terraform;
- Ansible.

Essas tecnologias poderão ser avaliadas posteriormente, mas não deverão aumentar a complexidade da entrega inicial.

---

# 22. Princípio de Desenvolvimento

Toda implementação deverá seguir a seguinte prioridade:

```text
Segurança
   +
Simplicidade
   +
Testabilidade
   +
Manutenibilidade
   +
Aderência aos requisitos
```

Nenhuma funcionalidade deverá ser considerada concluída apenas porque funciona visualmente.

Ela deverá:

1. funcionar;
2. validar dados;
3. verificar autorização;
4. possuir tratamento de erros;
5. possuir testes;
6. respeitar os controles de segurança definidos para o projeto.
