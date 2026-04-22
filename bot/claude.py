import json
import base64
from typing import Optional
import anthropic

MODELO = "claude-sonnet-4-5"

CATEGORIAS = [
    "Alimentação", "Transporte", "Moradia", "Saúde", "Lazer",
    "Vestuário", "Educação", "Pet", "Tecnologia", "Serviços", "Outros",
]

PROMPT_TEXTO = f"""Você é um extrator de informações de gastos financeiros.

Analise o texto enviado e extraia:
- valor: número decimal do valor gasto (ex: 25.00)
- estabelecimento: nome do estabelecimento (ex: "McDonald's")
- categoria: classifique em uma das opções abaixo

Categorias disponíveis: {', '.join(CATEGORIAS)}

Responda SOMENTE com um JSON válido neste formato exato, sem texto adicional:
{{"valor": 25.00, "estabelecimento": "McDonald's", "categoria": "Alimentação"}}

Se não conseguir identificar o valor, retorne:
{{"valor": null, "estabelecimento": null, "categoria": null}}"""

PROMPT_IMAGEM = f"""Você é um extrator de informações de notas fiscais.

Analise a imagem da nota fiscal e extraia:
- valor: número decimal do valor total pago (ex: 25.00)
- estabelecimento: nome do estabelecimento (ex: "McDonald's")
- categoria: classifique em uma das opções abaixo
- data: data da nota no formato YYYY-MM-DD (ex: "2026-04-22"). Se não encontrar, retorne null.

Categorias disponíveis: {', '.join(CATEGORIAS)}

Responda SOMENTE com um JSON válido neste formato exato, sem texto adicional:
{{"valor": 25.00, "estabelecimento": "McDonald's", "categoria": "Alimentação", "data": "2026-04-22"}}

Se não conseguir identificar o valor, retorne:
{{"valor": null, "estabelecimento": null, "categoria": null, "data": null}}"""


def _parse_resposta(texto: str) -> Optional[dict]:
    try:
        # Remove blocos de código markdown se o modelo os incluir
        texto = texto.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(texto)
    except (json.JSONDecodeError, AttributeError):
        return None


def extrair_gasto_texto(texto: str) -> Optional[dict]:
    client = anthropic.Anthropic()
    resposta = client.messages.create(
        model=MODELO,
        max_tokens=256,
        messages=[{"role": "user", "content": f"{PROMPT_TEXTO}\n\nTexto: {texto}"}],
    )
    return _parse_resposta(resposta.content[0].text)


def extrair_gasto_imagem(imagem_bytes: bytes) -> Optional[dict]:
    client = anthropic.Anthropic()
    imagem_b64 = base64.standard_b64encode(imagem_bytes).decode("utf-8")
    resposta = client.messages.create(
        model=MODELO,
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": imagem_b64,
                        },
                    },
                    {"type": "text", "text": PROMPT_IMAGEM},
                ],
            }
        ],
    )
    return _parse_resposta(resposta.content[0].text)
