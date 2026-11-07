import os
import json
import logging
import datetime
import pytz
from google import genai
from src.config import get_settings

logger = logging.getLogger(__name__)

# Emojis intercalados das classes: natureza/animais e emoções positivas
GREETING_EMOJIS = [
    "🦊", "😄", "🌻", "🦁", "🤩", "🦋", "🐼", "🥰", "🌲", "🐬",
    "😎", "🌺", "🦉", "🤗", "🌈", "🐢", "🥳", "🌸", "🐝", "😁",
    "🍀", "🦜", "😊", "🌊", "🐨", "😸", "🐳", "🌟", "🦩", "😋",
    "🦔", "✨", "🦦"
]

REST_QUOTES = [
    "“Quase tudo volta a funcionar se você desligar por alguns minutos, inclusive você.” — Anne Lamott",
    "“O descanso não é ociosidade; deitar-se às vezes na grama sob as árvores em um dia de verão não é de modo algum perda de tempo.” — John Lubbock",
    "“A pausa também faz parte da música.” — Stefan Zweig",
    "“Aprenda a descansar, não a desistir.” — Banksy",
    "“Na correria da vida, parar para respirar e recarregar as energias é a maior forma de produtividade.”",
    "“Você não precisa produzir o tempo todo para merecer descansar. O descanso sustenta a jornada.”",
    "“Descansar o corpo e a mente hoje é o que garante a clareza de amanhã.” — Provérbio"
]

class AIService:
    def __init__(self):
        self.settings = get_settings()
        self.tz = pytz.timezone(self.settings.TIMEZONE)
        self.client = None
        if self.settings.GEMINI_API_KEY and self.settings.GEMINI_API_KEY.startswith("AIza"):
            try:
                self.client = genai.Client(
                    api_key=self.settings.GEMINI_API_KEY,
                    http_options={"timeout": 8000}
                )
            except Exception as e:
                logger.warning(f"Erro ao inicializar cliente Gemini: {e}")

    def get_daily_emoji(self, target_date: datetime.date = None) -> str:
        if target_date is None:
            target_date = datetime.datetime.now(self.tz).date()
        index = target_date.toordinal() % len(GREETING_EMOJIS)
        return GREETING_EMOJIS[index]

    def get_daily_rest_quote(self, target_date: datetime.date = None) -> str:
        if target_date is None:
            target_date = datetime.datetime.now(self.tz).date()
        index = target_date.toordinal() % len(REST_QUOTES)
        return REST_QUOTES[index]

    def _fallback_briefing(self, events: list, next_month_events: list = None) -> str:
        emoji = self.get_daily_emoji()
        if not events:
            quote = self.get_daily_rest_quote()
            return (
                f"{emoji} *Bom dia!*\n\n"
                "Hoje sua agenda está livre de compromissos. Lembre-se de que o descanso é tão importante "
                "quanto os dias trabalhados — aproveite para desacelerar e recarregar as energias!\n\n"
                f"💬 _{quote}_"
            )

        msg = f"{emoji} *Bom dia! Aqui está o resumo da sua agenda de hoje:*\n\n"
        for e in events:
            link = f" ({e['meet_link']})" if e.get('meet_link') else ""
            msg += f"• *{e['start']} - {e['end']}*: {e['summary']}{link}\n"

        if next_month_events:
            msg += "\n📅 *Eventos únicos dos próximos 30 dias (sem recorrência):*\n"
            for e in next_month_events:
                link = f" ({e['meet_link']})" if e.get('meet_link') else ""
                msg += f"• *{e['start']}*: {e['summary']}{link}\n"

        return msg.strip()

    def generate_briefing(self, events: list, next_month_events: list = None) -> str:
        if not self.client or not events:
            return self._fallback_briefing(events, next_month_events)

        emoji = self.get_daily_emoji()
        next_month_events = next_month_events or []

        prompt = f"""
        Você é uma secretária executiva de alta performance e assistente pessoal no WhatsApp.
        Analise a lista de compromissos abaixo e gere um resumo matinal diário impecável e amigável:
        
        Eventos de hoje:
        {json.dumps(events, ensure_ascii=False)}

        Eventos únicos (sem recorrência) dos próximos 30 dias:
        {json.dumps(next_month_events, ensure_ascii=False)}

        Regras:
        1. Comece OBRIGATORIAMENTE a saudação de "Bom dia" usando o emoji do dia: {emoji} (ex.: "{emoji} *Bom dia!* ...").
        2. Liste os eventos de hoje em ordem cronológica com horários (início e término).
        3. Use formatação do WhatsApp (*negrito*, _itálico_).
        4. Use emojis pontuais e funcionais (ex.: ☕ para manhã, 💼 reuniões, 🍱 almoço, 🚀 tarde).
        5. Se houver reuniões coladas hoje (intervalo menor que 15 min), adicione um aviso em destaque.
        6. Se houver links de reunião, coloque-os de forma clicável.
        7. Se a lista de "Eventos únicos (sem recorrência) dos próximos 30 dias" não estiver vazia, adicione ao final uma seção clara destacando esses compromissos com suas respectivas datas e horários.
        """

        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Fallback ativado na geração de briefing via Gemini: {e}")
            return self._fallback_briefing(events, next_month_events)
