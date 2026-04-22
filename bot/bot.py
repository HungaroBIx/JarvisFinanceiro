import asyncio
import io
import os
import logging
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from . import claude, db

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

AGUARDANDO, CONFIRMANDO = range(2)

TECLADO_CONFIRMACAO = ReplyKeyboardMarkup(
    [["✅ Sim", "❌ Não"]],
    one_time_keyboard=True,
    resize_keyboard=True,
)

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

PALAVRAS_RELATORIO = [
    "relatório", "relatorio", "relatório", "resumo", "gastos do mês",
    "quanto gastei", "meus gastos", "report",
]


def _e_pedido_de_relatorio(texto: str) -> bool:
    t = texto.lower()
    return any(p in t for p in PALAVRAS_RELATORIO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 Olá! Sou seu bot de controle de gastos.\n\n"
        "Me envie uma *foto de nota fiscal* ou descreva seu gasto em texto.\n\n"
        "Exemplos:\n"
        "• _gastei 25 reais no McDonald's_\n"
        "• _Uber 18,50_\n"
        "• _mercado 150 reais_\n\n"
        "Para ver o resumo do mês envie /relatorio",
        parse_mode="Markdown",
    )
    return AGUARDANDO


async def relatorio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    hoje = datetime.now()
    mes_nome = MESES_PT[hoje.month - 1]

    await update.message.reply_text("⏳ Gerando relatório...")

    gastos = await asyncio.to_thread(db.buscar_gastos, hoje.year, hoje.month)

    if not gastos:
        await update.message.reply_text(
            f"Nenhum gasto registrado em {mes_nome}/{hoje.year}."
        )
        return AGUARDANDO

    total = sum(float(g["valor"]) for g in gastos)

    por_cat: dict[str, float] = defaultdict(float)
    for g in gastos:
        por_cat[g["categoria"]] += float(g["valor"])
    por_cat_ord = sorted(por_cat.items(), key=lambda x: x[1], reverse=True)

    por_estab: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "compras": 0})
    for g in gastos:
        por_estab[g["estabelecimento"]]["total"] += float(g["valor"])
        por_estab[g["estabelecimento"]]["compras"] += 1
    top_estab = sorted(por_estab.items(), key=lambda x: x[1]["total"], reverse=True)[:5]

    total_fmt = f"R$ {total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    linhas = [
        f"📊 *Relatório — {mes_nome}/{hoje.year}*\n",
        f"💸 *Total gasto:* {total_fmt}\n",
        "🏷️ *Por categoria:*",
    ]
    for cat, val in por_cat_ord:
        pct = val / total * 100
        val_fmt = f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas.append(f"  • {cat}: {val_fmt} ({pct:.0f}%)")

    linhas.append("\n📍 *Top estabelecimentos:*")
    for i, (estab, dados) in enumerate(top_estab, 1):
        n = dados["compras"]
        val_fmt = f"R$ {dados['total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        linhas.append(f"  {i}. {estab} — {val_fmt} ({'1 compra' if n == 1 else f'{n} compras'})")

    await update.message.reply_text("\n".join(linhas), parse_mode="Markdown")
    return AGUARDANDO


async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text

    if _e_pedido_de_relatorio(texto):
        return await relatorio(update, context)

    data_msg = update.message.date.strftime("%Y-%m-%d")

    await update.message.reply_text("⏳ Processando...")

    gasto = await asyncio.to_thread(claude.extrair_gasto_texto, texto)

    if not gasto or gasto.get("valor") is None:
        await update.message.reply_text(
            "❌ Não consegui identificar o gasto.\n\n"
            "Tente algo como:\n_gastei 50 reais no supermercado_\n\n"
            "Para ver o resumo do mês envie /relatorio",
            parse_mode="Markdown",
        )
        return AGUARDANDO

    context.user_data["gasto_pendente"] = {**gasto, "data": data_msg}
    return await _exibir_confirmacao(update, context)


async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    foto = await update.message.photo[-1].get_file()
    buf = io.BytesIO()
    await foto.download_to_memory(buf)
    imagem_bytes = buf.getvalue()
    data_msg = update.message.date.strftime("%Y-%m-%d")

    await update.message.reply_text("⏳ Lendo nota fiscal...")

    gasto = await asyncio.to_thread(claude.extrair_gasto_imagem, imagem_bytes)

    if not gasto or gasto.get("valor") is None:
        await update.message.reply_text(
            "❌ Não consegui ler a nota fiscal.\n\n"
            "Tente uma foto mais nítida ou descreva o gasto em texto."
        )
        return AGUARDANDO

    data = gasto.get("data") or data_msg
    context.user_data["gasto_pendente"] = {**gasto, "data": data}
    return await _exibir_confirmacao(update, context)


async def _exibir_confirmacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    gasto = context.user_data["gasto_pendente"]
    data_fmt = datetime.strptime(gasto["data"], "%Y-%m-%d").strftime("%d/%m/%Y")

    await update.message.reply_text(
        "✅ Aqui está o que entendi:\n\n"
        f"📍 {gasto.get('estabelecimento') or 'Não identificado'}\n"
        f"💰 R$ {float(gasto['valor']):.2f}\n"
        f"📅 {data_fmt}\n"
        f"🏷️ {gasto.get('categoria') or 'Outros'}\n\n"
        "Confirma?",
        reply_markup=TECLADO_CONFIRMACAO,
    )
    return CONFIRMANDO


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    resposta = update.message.text

    try:
        if "✅" in resposta or "sim" in resposta.lower():
            gasto = context.user_data.pop("gasto_pendente", None)
            if gasto:
                await asyncio.to_thread(
                    db.salvar_gasto,
                    valor=float(gasto["valor"]),
                    data=gasto["data"],
                    estabelecimento=gasto.get("estabelecimento") or "Não identificado",
                    categoria=gasto.get("categoria") or "Outros",
                )
            await update.message.reply_text(
                "💾 Gasto salvo com sucesso!\n\nMe envie outro gasto quando quiser.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return AGUARDANDO

        if "❌" in resposta or "não" in resposta.lower() or "nao" in resposta.lower():
            context.user_data.pop("gasto_pendente", None)
            await update.message.reply_text(
                "❌ Registro descartado.\n\nMe envie outro gasto quando quiser.",
                reply_markup=ReplyKeyboardRemove(),
            )
            return AGUARDANDO

        await update.message.reply_text(
            "Use os botões abaixo para confirmar ou cancelar o registro:",
            reply_markup=TECLADO_CONFIRMACAO,
        )
        return CONFIRMANDO

    except Exception:
        logger.exception("Erro em confirmar")
        context.user_data.pop("gasto_pendente", None)
        await update.message.reply_text(
            "⚠️ Ocorreu um erro ao salvar. Tente registrar o gasto novamente.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return AGUARDANDO


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Operação cancelada.", reply_markup=ReplyKeyboardRemove()
    )
    return AGUARDANDO


def main() -> None:
    token = os.environ["TELEGRAM_TOKEN"]
    app = Application.builder().token(token).build()

    conversa = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("relatorio", relatorio),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto),
            MessageHandler(filters.PHOTO, receber_foto),
        ],
        states={
            AGUARDANDO: [
                CommandHandler("relatorio", relatorio),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto),
                MessageHandler(filters.PHOTO, receber_foto),
            ],
            CONFIRMANDO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(conversa)

    logger.info("Bot iniciado! Pressione Ctrl+C para parar.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
