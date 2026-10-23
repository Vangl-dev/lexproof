# Política de Segurança

## Divulgação de Vulnerabilidades

A segurança do LexProof é uma prioridade. Se você descobrir uma vulnerabilidade de segurança, por favor a reporte de forma responsável.

### Como Reportar

**NÃO** abra issues públicas para vulnerabilidades de segurança.

Em vez disso, envie um e-mail para: **security@lexproof.com.br**

Inclua as seguintes informações no seu relatório:

1. **Descrição da vulnerabilidade**: Descreva o problema encontrado
2. **Passos para reproduzir**: Forneça instruções detalhadas
3. **Impacto potencial**: Explique o que poderia ser explorado
4. **Versão afetada**: Indique a versão do LexProof
5. **Sugestão de correção** (opcional): Se tiver uma ideia de como resolver

### Processo de Resposta

1. **Confirmação** (até 48 horas): Confirmamos o recebimento do relatório
2. **Avaliação** (até 5 dias úteis): Avaliamos a gravidade e escopo
3. **Correção** (até 30 dias): Desenvolvemos e testamos a correção
4. **Divulgação** (após correção): Divulgamos a vulnerabilidade após os usuários atualizarem

### Reconhecimento

Contribuidores que reportarem vulnerabilidades serão reconhecidos em nosso CHANGELOG (com sua autorização).

---

## Medidas de Segurança Implementadas

### 1. Integridade Criptográfica

- **Hashing multi-algoritmo**: SHA-256, SHA3-512, BLAKE3
- **Árvore Merkle**: Para verificação de integridade de múltiplos arquivos
- **Manifestos versionados**: Com hash global para validação retroativa
- **Verificação automática**: Comparação de hashes na importação e verificação

### 2. Cadeia de Custódia

- **Registro imutável**: Cada evento de evidência é registrado com hash
- **Rastreamento completo**: Operador, timestamp, ação realizada
- **Hash antes/depois**: Para cada modificação
- **Integração com blockchain**: Ancoragem opcional para timestamping imutável

### 3. Ancoragem Blockchain

- **OpenTimestamps**: Timestamping descentralizado ancorado no Bitcoin
- **RFC3161**: Timestamping baseado em TSA (Certificate Authority)
- **Degradação graciosa**: Funciona mesmo sem dependências blockchain

### 4. Validação de Dados

- **Pydantic**: Validação automática de todos os modelos de dados
- **Type hints**: Verificação de tipos em tempo de desenvolvimento
- **Sanitização**: Tratamento de entradas do usuário

### 5. Segurança de Arquivos

- **Detecção de tipo MIME**: Validação de tipos de arquivo
- **Tratamento de erros**: Falha segura em caso de arquivos corrompidos
- **Validação de ZIP**: Detecção de arquivos ZIP inválidos
- **Encoding detection**: Detecção automática de encoding para evitar injeção

### 6. Logging Seguro

- **Rotação de logs**: Prevenção de crescimento infinito
- **Sem dados sensíveis**: Logs não contêm conteúdo de evidências
- **Níveis configuráveis**: Controle granular de informação logada

---

## Práticas de Manipulação de Dados

### Dados Armazenados Localmente

- **Configurações**: `~/.lexproof/settings.json`
- **Logs**: `~/.lexproof/logs/`
- **Relatórios**: `~/.lexproof/output/`
- **Temporários**: `~/.lexproof/temp/`

### Princípios de Privacidade

1. **Processamento local**: Todos os dados são processados localmente
2. **Sem telemetria**: O LexProof não coleta dados de uso
3. **Sem conexões externas**: Exceto para anchoring blockchain (opcional)
4. **Controle do usuário**: O usuário decide quais dados compartilhar
5. **Criptografia de saída**: Relatórios podem incluir QR codes para verificação

### Dados Sensíveis

O LexProof lida com evidências digitais que podem conter dados sensíveis:

- **Não armazena cópias**: Apenas hashes e metadados são armazenados
- **Referências, não conteúdo**: Evidências são referenciadas por caminho, não copiadas
- **Cache de hash**: Armazenado apenas em memória durante a sessão
- **Manifestos**: Contêm apenas hashes, não conteúdo de evidências

### Conformidade

- **LGPD**: O LexProof é uma ferramenta offline que processa dados localmente
- **Marco Legal dos Dados**: Projetado para uso em contexto jurídico brasileiro
- **ICP-Brasil**: Planejado para futura certificação (Fase 20)

---

## Segurança durante Desenvolvimento

### Dependências

- Verificação automática de vulnerabilidades via `pip-audit`
- Atualização regular de dependências
- Preferência por dependências bem mantidas e amplamente usadas

### Código

- Type checking com mypy em modo estrito
- Linting com ruff para detecção de padrões inseguros
- Pre-commit hooks para verificação pré-commit
- Revisão de código para todas as mudanças

### Testes

- Testes unitários para componentes de segurança
- Testes de integração para fluxos completos
- Cobertura mínima de 80%

---

## Contato

- **E-mail de segurança**: security@lexproof.com.br
- **Issues gerais**: https://github.com/lexproof/lexproof/issues
- **Documentação**: https://docs.lexproof.com.br

Obrigado por ajudar a manter o LexProof seguro!
