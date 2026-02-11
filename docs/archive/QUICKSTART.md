# 🚀 Guia de Início Rápido

Sistema de Busca Semântica de Precedentes Trabalhistas usando xAI Collections

## ⚡ Instalação e Configuração Rápida

### Passo 1: Preparar Ambiente

```bash
# Clone ou baixe os arquivos para um diretório
cd /caminho/para/diretorio

# Instale dependências da aplicação de busca
pip install flet requests pyperclip
```

### Passo 2: Processar Sentenças

```bash
# Execute o script de processamento
python CollectionUploader.py "Sentenças Indexadas Revisado.json" --output-dir ./sentencas_md

# Resultado: Arquivos MD criados em ./sentencas_md/
```

**⏱️ Tempo estimado**: 2-5 minutos para ~1000 sentenças

### Passo 3: Criar Collection no xAI

1. **Acesse**: https://console.x.ai/
2. **Faça login** com sua conta xAI
3. **Crie Collection**:
   - Nome: `Precedentes Trabalhistas`
   - Chunk Size: `2048`
   - Chunk Overlap: `256`
   - Clique em **Create**

4. **Configure Metadados**:
   - Adicione campos: `categoria`, `reclamada`, `numero_processo`, `data_publicacao`, `tipo_acao`, `keywords`
   - Configure `categoria`, `reclamada`, `tipo_acao`, `data_publicacao` como **filtros**
   - Configure `keywords` como **busca**

5. **Upload Arquivos MD**:
   - Clique em **Upload Files**
   - Selecione todos os arquivos do diretório `./sentencas_md/`
   - Aguarde processamento (barra de progresso)

6. **Gere Management Key**:
   - Vá para **Settings** → **API Keys**
   - Clique em **Generate Management Key**
   - **Copie e guarde** em local seguro

**⏱️ Tempo estimado**: 10-15 minutos + tempo de upload

### Passo 4: Executar Aplicação de Busca

```bash
python PrecedenteSearchApp.py
```

**Primeira Vez:**
1. Clique em ⚙️ **Configurações**
2. Cole suas chaves:
   - **Management Key**: Chave da Collection criada
   - **API Key**: Sua chave de API do Grok
3. Configure:
   - **Modelo**: `grok-2-1212`
   - **Temperature**: `0.7`
4. Clique em **Salvar**

**⏱️ Tempo estimado**: 2 minutos

### Passo 5: Realizar Primeira Busca

1. **Selecione Collection**: No menu suspenso
2. **Habilite busca**: Toggle "Buscar na Collection"
3. **Digite consulta**:
   ```
   Como fundamentar adicional de insalubridade para profissionais de saúde?
   ```
4. **Clique Enviar** (ou pressione Enter)

**⏱️ Tempo estimado**: 10-30 segundos por consulta

## 📋 Checklist de Configuração

- [ ] Python 3.8+ instalado
- [ ] Dependências instaladas (`pip install flet requests pyperclip`)
- [ ] Arquivo JSON de sentenças disponível
- [ ] Arquivos MD gerados com `CollectionUploader.py`
- [ ] Conta xAI criada (https://console.x.ai/)
- [ ] Collection criada no xAI Console
- [ ] Arquivos MD enviados para Collection
- [ ] Management Key gerada e salva
- [ ] API Key do Grok obtida
- [ ] Aplicação PrecedenteSearchApp.py configurada
- [ ] Primeira busca realizada com sucesso

## 🎯 Exemplos de Consultas

### Busca Básica
```
Precedentes sobre justa causa por insubordinação
```

### Busca com Filtro de Empresa
```
Busque precedentes sobre horas extras da empresa Petrobras
```

### Busca com Contexto Temporal
```
Decisões sobre adicional noturno dos últimos 2 anos
```

### Busca Complexa
```
Como fundamentar reintegração de empregado dispensado durante 
pandemia de COVID-19, considerando precedentes sobre estabilidade 
provisória e compromisso #NãoDemita?
```

## 🔧 Configurações Recomendadas

### Para Busca Geral de Precedentes:
- **Modelo**: grok-2-1212
- **Temperature**: 0.7
- **Top K**: 5 (padrão)
- **Search Type**: hybrid

### Para Análise Detalhada:
- **Modelo**: grok-2-1212
- **Temperature**: 0.3 (mais conservador)
- **Top K**: 10 (mais resultados)
- **Anexar**: Petição ou documento relevante

### Para Geração de Minutas:
- **Modelo**: grok-2-1212
- **Temperature**: 0.8 (mais criativo)
- **System Prompt**: 
```
Você é um assistente jurídico especializado em elaboração de minutas 
de sentenças trabalhistas. Use os precedentes fornecidos para fundamentar 
decisões de forma consistente com jurisprudência anterior. Sempre cite 
o número do processo ao mencionar precedentes.
```

## ⚠️ Solução Rápida de Problemas

### "Management Key inválida"
**Solução**: Copie novamente do xAI Console, sem espaços extras

### "Collection não encontrada"
**Solução**: Aguarde finalização do processamento dos arquivos MD

### "Erro ao enviar mensagem"
**Solução**: Verifique sua conexão com internet e validade da API Key

### Busca não retorna resultados
**Solução**: 
1. Verifique se "Buscar na Collection" está habilitado
2. Tente termos mais específicos
3. Verifique se a Collection foi selecionada no dropdown

### Aplicação Flet não abre
**Solução**:
```bash
# Reinstale Flet
pip install --upgrade flet

# Execute novamente
python PrecedenteSearchApp.py
```

## 📞 Suporte

Para problemas ou dúvidas:
1. Consulte o README.md completo
2. Verifique documentação xAI: https://docs.x.ai/
3. Revise logs do console para mensagens de erro

## 🎓 Próximos Passos

Após dominar o básico:

1. **Customize System Prompt**: Adapte para seu estilo de fundamentação
2. **Organize Collections**: Crie Collections temáticas (CLT, Processo, etc.)
3. **Experimente Temperature**: Ajuste para diferentes tipos de consulta
4. **Use Anexos**: Adicione petições ao contexto para análise mais precisa
5. **Explore Filtros**: Use metadados para buscas mais específicas

## ⏱️ Tempo Total Estimado (Setup Completo)

- Instalação e preparação: **5 minutos**
- Processamento de sentenças: **2-5 minutos**
- Configuração xAI Collection: **15 minutos**
- Primeira busca: **5 minutos**

**Total**: ~30 minutos para sistema completo funcionando

---

**Desenvolvido para modernizar a busca de precedentes judiciais com IA.**
