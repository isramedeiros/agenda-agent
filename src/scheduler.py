import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from src.config import get_settings
from src.services.calendar_service import CalendarService
from src.services.ai_service import AIService
from src.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

def execute_daily_briefing() -> bool:
    logger.info("Executando rotina diária de briefing...")
    calendar = CalendarService()
    ai = AIService()
    whatsapp = WhatsAppService()

    events = calendar.get_today_events()
    next_month_events = calendar.get_next_month_single_events() if events else []
    message = ai.generate_briefing(events, next_month_events)
    sent = whatsapp.send_message(message)
    if sent:
        logger.info("Briefing enviado com sucesso.")
    return sent

def setup_scheduler():
    settings = get_settings()
    tz = pytz.timezone(settings.TIMEZONE)
    scheduler = BackgroundScheduler(timezone=tz)
    
    scheduler.add_job(
        execute_daily_briefing,
        trigger=CronTrigger(
            hour=settings.CRON_HOUR,
            minute=settings.CRON_MINUTE,
            timezone=tz
        ),
        id="daily_agenda_briefing",
        replace_existing=True,
        misfire_grace_time=3600
    )
    scheduler.start()
    return scheduler
