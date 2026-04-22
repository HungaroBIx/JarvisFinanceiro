# 💰 Jarvis Financeiro

Bot no Telegram para controle de gastos pessoais. Envie uma foto de nota fiscal ou descreva um gasto em texto — o bot usa IA para extrair e categorizar as informações, salva no Supabase e disponibiliza um dashboard interativo com gráficos e relatórios.

---

## Produção

| Serviço | Plataforma | URL / Acesso |
|---|---|---|
| Bot Telegram | Railway | Rodando 24h em background |
| Dashboard | Streamlit Community Cloud | [jarvisfinanceiro.streamlit.app](https://jarvisfinanceiro.streamlit.app) |
| Banco de dados | Supabase | PostgreSQL na nuvem |

---

## Stack

| Camada | Tecnologia |
|---|---|
| Bot | Python + python-telegram-bot |
| IA | Claude API (Anthropic) |
| Banco de dados | Supabase (PostgreSQL) |
| Dashboard | Streamlit + Plotly |

---

## Funcionalidades

### Bot (Telegram)
- Registra gastos via **mensagem de texto** (`gastei 25 reais no McDonald's`)
- Registra gastos via **foto de nota fiscal** (extrai data, valor e estabelecimento da imagem)
- Exibe resumo para **confirmação** antes de salvar
- Gera **relatório mensal** via `/relatorio` ou linguagem natural (`me envia o relatório`)

### Dashboard (Streamlit)
- Cards de resumo: total no período, categoria e local mais frequente
- Gráfico de linha com tendência de gastos por mês
- Gráfico de pizza e barras por categoria
- Tabela de estabelecimentos com total, nº de compras e ticket médio
- Filtros por período (mês/ano ou intervalo de datas) e categoria

---

## Estrutura

```
gastosbot/
  bot/
    __init__.py
    bot.py          # lógica do Telegram (handlers, estados)
    claude.py       # integração com a Claude API
    db.py           # integração com o Supabase
  dashboard/
    app.py          # aplicação Streamlit
  .env              # variáveis de ambiente (não versionar)
  .env.example      # template das variáveis
  .gitignore
  requirements.txt
  supabase_schema.sql
```

---

## Configuração

### 1. Pré-requisitos

- Python 3.10+
- Conta no [Telegram](https://telegram.org) — crie um bot via [@BotFather](https://t.me/BotFather)
- Conta na [Anthropic](https://console.anthropic.com) — gere uma API Key
- Conta no [Supabase](https://supabase.com) — crie um projeto

### 2. Banco de dados

No painel do Supabase, acesse **SQL Editor** e execute o conteúdo de `supabase_schema.sql`:

```sql
create table gastos (
  id          uuid primary key default gen_random_uuid(),
  valor       decimal(10, 2) not null,
  data        date not null,
  estabelecimento text not null,
  categoria   text not null,
  criado_em   timestamptz default now()
);
```

### 3. Variáveis de ambiente

Copie `.env.example` para `.env` e preencha:

```env
TELEGRAM_TOKEN=seu_token_aqui
ANTHROPIC_API_KEY=sua_chave_aqui
SUPABASE_URL=https://xxxxxxxxxxx.supabase.co
SUPABASE_KEY=sua_chave_anon_aqui
```

### 4. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## Como rodar

**Bot** (na raiz do projeto):
```bash
python -m bot.bot
```

**Dashboard** (em outro terminal):
```bash
streamlit run dashboard/app.py
```

---

## Categorias disponíveis

O Claude classifica automaticamente cada gasto em uma das categorias:

`Alimentação` `Transporte` `Moradia` `Saúde` `Lazer` `Vestuário` `Educação` `Pet` `Tecnologia` `Serviços` `Outros`

---

## Exemplos de uso

**Registrar por texto:**
```
gastei 35 reais no iFood
Uber 18,50
mercado 210 reais
```

**Pedir relatório:**
```
/relatorio
me envia o relatório de gastos
quanto gastei esse mês
```
