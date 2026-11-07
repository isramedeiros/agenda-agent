import sys
import os
import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.calendar_service import CalendarService
from src.services.ai_service import AIService, GREETING_EMOJIS

def test_flow():
    print("-> Testando CalendarService (Modo Mock / Integrado)...")
    cal = CalendarService()
    events = cal.get_today_events()
    next_month_single = cal.get_next_month_single_events()
    print(f"   Eventos de hoje: {len(events)}")
    print(f"   Eventos únicos nos próximos 30 dias: {len(next_month_single)}")

    print("-> Testando rotação diária de emojis...")
    ai = AIService()
    today = datetime.date.today()
    emoji_today = ai.get_daily_emoji(today)
    emoji_tomorrow = ai.get_daily_emoji(today + datetime.timedelta(days=1))
    assert emoji_today in GREETING_EMOJIS, "Emoji de hoje deve pertencer à lista permitida"
    assert emoji_tomorrow in GREETING_EMOJIS, "Emoji de amanhã deve pertencer à lista permitida"
    assert emoji_today != emoji_tomorrow, "O emoji deve mudar diariamente"
    print(f"   Emoji de hoje: {emoji_today} | Emoji de amanhã: {emoji_tomorrow}")

    print("-> Testando AIService (Dia com eventos + eventos únicos próximos 30 dias)...")
    briefing = ai.generate_briefing(events, next_month_single)
    print("\n--- MENSAGEM GERADA (COM EVENTOS) ---")
    print(briefing)
    print("-------------------------------------\n")
    assert briefing.startswith(emoji_today), "Mensagem deve começar com o emoji do dia"

    print("-> Testando AIService (Dia sem eventos - mensagem de descanso)...")
    empty_briefing = ai.generate_briefing([], next_month_single)
    print("\n--- MENSAGEM GERADA (SEM EVENTOS) ---")
    print(empty_briefing)
    print("-------------------------------------\n")
    assert empty_briefing.startswith(emoji_today), "Mensagem sem eventos deve começar com o emoji do dia"
    assert "descanso" in empty_briefing.lower(), "Mensagem sem eventos deve mencionar a importância do descanso"
    assert "próximos 30 dias" not in empty_briefing.lower(), "Não deve exibir eventos próximos quando não houver eventos hoje"

    print("-> Testando filtro de recorrência...")
    assert cal._is_recurring_component({"UID": "1", "RRULE": "FREQ=WEEKLY"}) is True
    assert cal._is_recurring_component({"UID": "2", "RECURRENCE-ID": "20261110T100000Z"}) is True
    assert cal._is_recurring_component({"UID": "3"}, recurring_uids={"3"}) is True
    assert cal._is_recurring_component({"UID": "4", "SUMMARY": "Evento Único"}, recurring_uids={"3"}) is False
    print("   Filtro de eventos únicos validado com sucesso!")

    print("✓ Pipeline e novas features validados com sucesso!")

if __name__ == "__main__":
    test_flow()
