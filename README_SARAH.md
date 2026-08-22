# Sarah - Sistema de Assistência Judicial

Sistema unificado de assistência judicial para magistrados trabalhistas, integrando extração estruturada de autos, análise de provas e geração de minutas de sentença com IA.

## Visão Geral

O sistema Sarah é composto por 4 módulos principais:

1. **Cartão do Caso**: Extração estruturada de autos trabalhistas (petição inicial, defesa, questões a decidir)
2. **Dossiê de Prova**: Análise automatizada de provas documentais, periciais e orais com regras de valoração
3. **Minuta de Sentença**: Geração de minuta dialética com busca de precedentes
4. **Indexador de Sentenças**: Indexação de sentenças publicadas na Collection xAI para busca de precedentes

## Requisitos

- Python 3.9+
- Chave de API xAI (Grok)
- Management Key xAI (para Collections)
- Sistema operacional: Linux, macOS ou Windows

## Instalação

### 1. Clone o repositório e mude para a branch unificada

```bash
git clone https://github.com/fgbkiwi/GrokCollectionUpload-Search.git
cd GrokCollectionUpload-Search
git checkout cursor/cartao-caso-entregavel-2-3b1b
```

### 2. Instale as dependências

```bash
pip install -r requirements_sarah.txt
```

Ou instale individualmente:

```bash
pip install flet pydantic requests pytest
```

### 3. Configure as variáveis de ambiente (opcional)

Você pode configurar as chaves de API via variáveis de ambiente:

```bash
export XAI_API_KEY="xai-..."
export XAI_MANAGEMENT_KEY="xai-..."
```

Ou configure diretamente na interface do aplicativo (aba Configurações).

## Uso

### Iniciar o Aplicativo

```bash
python AppSarah.py
```

O aplicativo abrirá uma interface gráfica com 5 abas:

1. **Cartão do Caso**
2. **Dossiê de Prova**
3. **Minuta**
4. **Indexador**
5. **Configurações**

## Fluxo de Trabalho

### 1. Configuração Inicial (Primeira Execução)

1. Abra a aba **Configurações**
2. Insira sua **API Key xAI**
3. Insira sua **Management Key xAI**
4. (Opcional) Personalize o **Kernel Sarah** (prompt de sistema)
5. (Opcional) Adicione ou edite **Modelos Temáticos**

### 2. Indexar Sentenças Publicadas (Precedentes)

**Esta etapa é opcional** - o juiz já possui uma Collection funcional de sentenças publicadas.

Se você precisar indexar novas sentenças:

1. Abra a aba **Indexador**
2. Clique em "Escolher Pasta de Sentenças (MD)"
3. Selecione a pasta contendo suas sentenças em formato Markdown
4. Clique em "Indexar na Collection"
5. Aguarde a conclusão (cada sentença é extraída e enviada à Collection)

### 3. Extrair Cartão do Caso

1. Abra a aba **Cartão do Caso**
2. Clique em "Escolher Arquivo MD"
3. Selecione o arquivo Markdown dos autos do processo
4. Clique em "Extrair Cartão"
5. Aguarde a extração (pode levar alguns minutos)
6. Revise o resultado (pedidos, questões, avisos)
7. Clique em "Confirmar e Salvar"

O cartão será salvo em: `~/.indexador_sentencas/cartoes/`

### 4. Montar Dossiê de Prova

1. Abra a aba **Dossiê de Prova**
2. Status mostrará "Cartão confirmado" (em verde)
3. Clique em "Escolher Autos (MD)"
4. Selecione **o mesmo arquivo MD dos autos**
5. Clique em "Montar Dossiê"
6. Aguarde a análise de provas (pode levar vários minutos)
7. Revise o dossiê por questão (provas documentais, periciais, orais)
8. Clique em "Confirmar Dossiê"

O dossiê será salvo em: `~/.indexador_sentencas/dossies/`

### 5. Gerar Minuta de Sentença

1. Abra a aba **Minuta**
2. Status mostrará "Cartão e dossiê confirmados"
3. Selecione a **Collection de Precedentes** (sua Collection existente)
4. Configure critérios de busca:
   - **Top K**: número de precedentes por questão (padrão: 5)
   - **Modo de Busca**: híbrido, palavra-chave ou semântico
5. Clique em "Gerar Estrutura"
6. Revise a estrutura de tópicos proposta
7. Clique em "Gerar Minuta"
8. Aguarde a geração (pode levar vários minutos)
9. Minuta será salva automaticamente em JSON e Markdown

Minutas salvas em: `~/.indexador_sentencas/minutas/`

## Arquitetura do Sistema

### Módulos

- **`cartao_caso/`**: Schema, extrator e persistência do cartão do caso
- **`dossie_prova/`**: Examinadores de prova (documental, pericial, oral) e orquestrador
- **`minuta/`**: Kernel Sarah, modelos temáticos, busca de precedentes e orquestrador de minuta
- **`indexador/`**: Catalogação e upload de sentenças para Collection xAI

### Persistência Local

Todos os artefatos são salvos localmente em `~/.indexador_sentencas/`:

```
~/.indexador_sentencas/
├── cartoes/          # Cartões confirmados (JSON)
├── dossies/          # Dossiês de prova (JSON)
├── minutas/          # Minutas geradas (JSON e MD)
├── modelos/          # Modelos temáticos (JSON)
└── config/           # Configurações (kernel Sarah)
```

**IMPORTANTE**: Os autos (arquivos MD) **NÃO** são enviados para a Collection. Apenas o cartão, dossiê e minuta são persistidos localmente.

## O que o Sistema Faz

### Cartão do Caso

- Extrai estrutura JSON dos autos:
  - Partes (reclamante, reclamada)
  - Petição inicial (pedidos, períodos, valores, reflexos)
  - Contestação (impugnação específica, teses)
  - Réplica
  - Questões a decidir (tipo, momento processual, natureza fática)
  - Mapa pedido-defesa-questão
- Aplica art. 341 CPC (falta de impugnação específica)
- Identifica IDs do PJe e folhas citadas

### Dossiê de Prova

- **Examinador Documental**:
  - Extrai provas documentais relevantes por questão
  - Aplica regras de valoração (doc prevalece sobre testemunha)
  - Detecta confissão ficta (falta de impugnação + alegação de irregularidade)
  - Particiona em lotes se conteúdo muito grande

- **Examinador Pericial**:
  - Extrai trechos de laudos (médico, ambiental, contábil, etc.)
  - Aplica presunção de veracidade do laudo

- **Examinador Oral**:
  - Aplica rigorosamente as **regras do juiz**:
    - Depoimento de parte só vale como confissão real
    - Preposto não fundamenta indeferimento
    - Reclamante não fundamenta deferimento
    - Descarta testemunha se mente, contradiz documento, excede limites da lide
    - Valoriza conhecimento pessoal e detalhe
    - Ouvir dizer = zero, dúvida = zero
    - Conflito: específico > genérico, pessoal > impessoal
  - Transcreve trechos com carimbo de tempo `[HH:MM:SS]`

### Minuta de Sentença

- **Kernel Sarah**: Prompt de sistema editável com diretrizes de redação
- **Modelos Temáticos**: Biblioteca de templates (juros, FGTS, honorários, etc.)
- **Busca de Precedentes**: Busca híbrida/semântica/palavra-chave na Collection
- **Orquestração em Etapas**:
  1. Estrutura de tópicos (pressupostos → mérito → juros/honorários)
  2. Minuta prévia por tópico (tese, antítese, abordagem)
  3. Minuta definitiva (fundamentação dialética, transcrição literal de prova, precedentes)
- **Validação de IDs**: Verifica se todos os IDs citados existem no dossiê/cartão
- **Formato**: Relatório (narrativo) + Fundamentação (dialética por questão) + Dispositivo

## O que o Sistema NÃO Faz

- **NÃO faz OCR**: autos devem estar em Markdown
- **NÃO envia autos para a Collection**: autos ficam locais
- **NÃO decide sozinho**: todas as etapas requerem confirmação do juiz
- **NÃO substitui o juiz**: é uma ferramenta de assistência, não de automação total
- **NÃO depende de Kubernetes/SSO**: roda localmente

## Collection de Precedentes

A Collection xAI **já existe e está funcional** com sentenças publicadas do juiz.

- **Não é necessário reindexar** para usar o sistema
- Autos **NÃO** são enviados para a Collection
- Somente sentenças **publicadas** devem ser indexadas

Para busca de precedentes:
- Modo **híbrido** (padrão): combina busca semântica + palavra-chave
- Modo **keyword**: busca por palavras-chave exatas
- Modo **semantic**: busca por similaridade semântica

## Testes

O sistema inclui testes unitários com mocks:

```bash
pytest tests/test_dossie_minuta.py -v
pytest tests/test_integracao.py -v
```

Testes cobrem:
- Examinador oral descarta depoimento autointeressado
- Dossiê funde lotes documentais
- Minuta recusa ID inexistente
- Modelo temático é injetado quando tema bate
- Questão de ofício sem `mencionar_na_minuta=false` não vira tópico
- Fluxo sintético ponta a ponta

## Troubleshooting

### Erro "API Key inválida"

- Verifique se configurou as chaves na aba **Configurações**
- Teste a chave em: https://console.x.ai

### Erro "Collection não encontrada"

- Verifique se a Management Key está correta
- Liste suas Collections na aba **Minuta**

### Extração do cartão falha

- Verifique se o arquivo MD está bem formatado
- Tente com um arquivo menor primeiro
- Veja os logs de erro na interface

### Dossiê vazio ou com poucas provas

- Verifique se os autos contêm as seções esperadas (depoimentos, documentos, laudos)
- Heurística de segmentação pode precisar ajustes para formatos específicos

### Minuta com IDs inválidos

- Sistema valida automaticamente e avisa
- Revise manualmente os IDs citados
- Corrija o dossiê se necessário

## API xAI

O sistema usa a API oficial xAI:

- **Chat/Completions**: `https://api.x.ai/v1/chat/completions`
- **Documents Search**: `https://api.x.ai/v1/documents/search`
- **Collections Management**: `https://management-api.x.ai/v1/collections`

Modelos suportados:
- `grok-beta` (padrão)
- `grok-2-1212`
- `grok-4.6`

**IMPORTANTE**: Credenciais só em `env` ou campo senha em memória. **Nunca grave chaves em JSON**.

## Desenvolvimento

### Estrutura de Arquivos

```
.
├── AppSarah.py              # App principal unificado
├── aba_cartao.py            # UI do Cartão do Caso
├── aba_dossie.py            # UI do Dossiê
├── aba_minuta.py            # UI da Minuta
├── aba_indexador.py         # UI do Indexador
├── aba_configuracoes.py     # UI de Configurações
├── cartao_caso/             # Módulo Cartão do Caso
├── dossie_prova/            # Módulo Dossiê de Prova
├── minuta/                  # Módulo Minuta
├── indexador/               # Módulo Indexador
├── tests/                   # Testes unitários
└── README_SARAH.md          # Este arquivo
```

### Adicionar Novo Modelo Temático

1. Abra a aba **Configurações** → **Modelos Temáticos**
2. Clique em "Novo Modelo Temático"
3. Preencha:
   - Nome
   - Tema (ex: `juros`, `fgts`, `honorarios`)
   - Texto com variáveis `{{nome_variavel}}`
4. Salvar

Modelos são injetados automaticamente na minuta quando o tema bate com o título do tópico.

### Personalizar Kernel Sarah

1. Abra a aba **Configurações** → **Kernel Sarah**
2. Edite o prompt de sistema
3. Clique em "Salvar Prompt"
4. (Opcional) Ao final de uma sessão de minuta, clique em "Sugerir alterações no prompt" para melhorias automáticas

## Limitações Conhecidas

- Sistema assume autos em Markdown bem formatado
- Heurística de segmentação (documental/pericial/oral) é básica
- Validação de IDs é por regex simples
- Sem suporte nativo para DOCX (use conversores MD)
- Interface em desenvolvimento (algumas funcionalidades podem estar incompletas)

## Contribuindo

Este é um sistema interno. Para melhorias:

1. Crie uma branch `feature/nome-da-feature`
2. Implemente a melhoria
3. Adicione testes
4. Submeta PR

## Licença

Uso interno.

## Suporte

Para dúvidas ou problemas:

- Verifique este README
- Veja os exemplos em `tests/`
- Consulte a documentação da API xAI: https://docs.x.ai

---

**Sarah v1.0** - Sistema de Assistência Judicial para Magistrados Trabalhistas
