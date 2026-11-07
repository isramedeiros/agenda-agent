from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from src.scheduler import setup_scheduler, execute_daily_briefing
from src.config import get_settings

scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    scheduler = setup_scheduler()
    yield
    if scheduler:
        scheduler.shutdown()

app = FastAPI(title="Agenda Daily Briefing Agent", lifespan=lifespan)

@app.get("/health")
def health():
    settings = get_settings()
    job = scheduler.get_job("daily_agenda_briefing") if scheduler else None
    return {
        "status": "online",
        "scheduler_running": scheduler.running if scheduler else False,
        "cron_schedule": f"{settings.CRON_HOUR:02d}:{settings.CRON_MINUTE:02d} ({settings.TIMEZONE})",
        "next_run_time": str(job.next_run_time) if job else None
    }

@app.post("/api/v1/trigger-briefing")
def trigger_briefing(background_tasks: BackgroundTasks):
    background_tasks.add_task(execute_daily_briefing)
    return {"status": "disparo iniciado em background"}
