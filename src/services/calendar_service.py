import datetime
import pytz
import os
import re
import requests
import logging
try:
    import icalendar
    import recurring_ical_events
except ImportError:
    icalendar = None
    recurring_ical_events = None
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.config import get_settings

logger = logging.getLogger(__name__)
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

class CalendarService:
    def __init__(self):
        self.settings = get_settings()
        self.tz = pytz.timezone(self.settings.TIMEZONE)
        self.service = self._init_service()
        self._ics_cache = {}

    def _init_service(self):
        cred_path = self.settings.GOOGLE_SERVICE_ACCOUNT_FILE
        local_cred_path = os.path.join(os.path.dirname(__file__), "..", "..", "credentials", "service_account.json")
        for path in [cred_path, local_cred_path]:
            if path and os.path.exists(path):
                creds = service_account.Credentials.from_service_account_file(
                    path, scopes=SCOPES
                )
                return build('calendar', 'v3', credentials=creds)
        return None

    def _format_component(self, component, include_date: bool = False) -> Dict[str, Any]:
        summary = str(component.get("SUMMARY", "Sem título"))
        description = str(component.get("DESCRIPTION", ""))
        location = str(component.get("LOCATION", ""))

        dtstart = component.get("DTSTART").dt
        dtend_prop = component.get("DTEND")
        dtend = dtend_prop.dt if dtend_prop else dtstart

        if isinstance(dtstart, datetime.datetime):
            if dtstart.tzinfo is None:
                dtstart = self.tz.localize(dtstart)
            else:
                dtstart = dtstart.astimezone(self.tz)
            start_fmt = dtstart.strftime("%d/%m %H:%M") if include_date else dtstart.strftime("%H:%M")
            sort_key = dtstart.strftime("%Y%m%d%H%M")
        else:
            start_fmt = f"{dtstart.strftime('%d/%m')} (Dia inteiro)" if include_date else "Dia inteiro"
            sort_key = dtstart.strftime("%Y%m%d0000")

        if isinstance(dtend, datetime.datetime):
            if dtend.tzinfo is None:
                dtend = self.tz.localize(dtend)
            else:
                dtend = dtend.astimezone(self.tz)
            end_fmt = dtend.strftime("%H:%M")
        else:
            end_fmt = "Dia inteiro"

        combined_text = f"{description} {location}"
        meet_match = re.search(r"https://meet\.google\.com/[a-zA-Z0-9-]+", combined_text)
        meet_link = meet_match.group(0) if meet_match else ""

        return {
            "summary": summary,
            "start": start_fmt,
            "end": end_fmt,
            "meet_link": meet_link,
            "description": description or location,
            "upcoming": include_date,
            "_sort": sort_key
        }

    def _is_recurring_component(self, comp, recurring_uids: set = None) -> bool:
        if comp.get("RRULE") or comp.get("RDATE") or comp.get("RECURRENCE-ID"):
            return True
        uid = str(comp.get("UID", ""))
        if recurring_uids and uid and uid in recurring_uids:
            return True
        return False

    def _fetch_ics_calendar(self, ics_url: str):
        if ics_url in self._ics_cache:
            return self._ics_cache[ics_url]
        resp = requests.get(ics_url, timeout=15)
        resp.raise_for_status()
        cal = icalendar.Calendar.from_ical(resp.content)
        self._ics_cache[ics_url] = cal
        return cal

    def _get_events_from_ics(self, ics_url: str) -> List[Dict[str, Any]]:
        cal = self._fetch_ics_calendar(ics_url)
        now = datetime.datetime.now(self.tz)
        today_date = now.date()

        raw_today = recurring_ical_events.of(cal).at(today_date)
        events = []
        for comp in raw_today:
            if str(comp.get("STATUS", "")).upper() == "CANCELLED":
                continue
            events.append(self._format_component(comp, include_date=False))

        events.sort(key=lambda x: x.get("_sort", x["start"]))
        return events

    def _get_single_events_from_ics(self, ics_url: str, days: int = 30) -> List[Dict[str, Any]]:
        cal = self._fetch_ics_calendar(ics_url)
        now = datetime.datetime.now(self.tz)
        today_date = now.date()
        start_date = today_date + datetime.timedelta(days=1)
        end_date = today_date + datetime.timedelta(days=days)

        # Coleta UIDs de séries recorrentes para garantir exclusão de instâncias/exceções
        recurring_uids = set()
        for comp in cal.walk("VEVENT"):
            if comp.get("RRULE") or comp.get("RDATE") or comp.get("RECURRENCE-ID"):
                uid = str(comp.get("UID", ""))
                if uid:
                    recurring_uids.add(uid)

        raw_upcoming = recurring_ical_events.of(cal).between(
            start_date, end_date + datetime.timedelta(days=1)
        )
        events = []
        for comp in raw_upcoming:
            if str(comp.get("STATUS", "")).upper() == "CANCELLED":
                continue
            if self._is_recurring_component(comp, recurring_uids):
                continue

            dtstart = comp.get("DTSTART").dt
            if isinstance(dtstart, datetime.datetime):
                comp_date = (
                    dtstart.astimezone(self.tz).date()
                    if dtstart.tzinfo
                    else dtstart.date()
                )
            else:
                comp_date = dtstart

            if start_date <= comp_date <= end_date:
                events.append(self._format_component(comp, include_date=True))

        events.sort(key=lambda x: x.get("_sort", x["start"]))
        return events

    def get_today_events(self) -> List[Dict[str, Any]]:
        if self.settings.GOOGLE_CALENDAR_ICS_URL:
            try:
                return self._get_events_from_ics(self.settings.GOOGLE_CALENDAR_ICS_URL)
            except Exception as e:
                logger.error(f"Erro ao ler ICS do Google Calendar: {e}")

        if not self.service:
            # Fallback mock mode se credenciais não existirem
            now = datetime.datetime.now(self.tz)
            return [
                {
                    "summary": "[MOCK] Reunião de Alinhamento",
                    "start": (now + datetime.timedelta(hours=2)).strftime("%H:%M"),
                    "end": (now + datetime.timedelta(hours=3)).strftime("%H:%M"),
                    "meet_link": "https://meet.google.com/abc-defg-hij",
                    "description": "Alinhamento semanal de tarefas"
                },
                {
                    "summary": "[MOCK] Almoço com Cliente",
                    "start": (now + datetime.timedelta(hours=4, minutes=15)).strftime("%H:%M"),
                    "end": (now + datetime.timedelta(hours=5, minutes=15)).strftime("%H:%M"),
                    "meet_link": "",
                    "description": "Restaurante Central"
                }
            ]

        now = datetime.datetime.now(self.tz)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

        events_result = self.service.events().list(
            calendarId=self.settings.GOOGLE_CALENDAR_ID,
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        raw_events = events_result.get('items', [])
        formatted = []
        for event in raw_events:
            start_raw = event['start'].get('dateTime', event['start'].get('date'))
            end_raw = event['end'].get('dateTime', event['end'].get('date'))
            
            # Formatação de horário
            start_fmt = start_raw[11:16] if 'T' in start_raw else "Dia inteiro"
            end_fmt = end_raw[11:16] if 'T' in end_raw else "Dia inteiro"

            meet_link = event.get('hangoutLink', '')
            if not meet_link and 'conferenceData' in event:
                entries = event['conferenceData'].get('entryPoints', [])
                for ep in entries:
                    if ep.get('entryPointType') == 'video':
                        meet_link = ep.get('uri', '')
                        break

            formatted.append({
                "summary": event.get('summary', 'Sem título'),
                "start": start_fmt,
                "end": end_fmt,
                "meet_link": meet_link,
                "description": event.get('description', '')
            })
        return formatted

    def get_next_month_single_events(self, days: int = 30) -> List[Dict[str, Any]]:
        if self.settings.GOOGLE_CALENDAR_ICS_URL:
            try:
                return self._get_single_events_from_ics(self.settings.GOOGLE_CALENDAR_ICS_URL, days=days)
            except Exception as e:
                logger.error(f"Erro ao ler eventos únicos do ICS: {e}")

        if not self.service:
            now = datetime.datetime.now(self.tz)
            ev_date = now + datetime.timedelta(days=5)
            return [
                {
                    "summary": "[MOCK] Consulta Médica (Evento Único)",
                    "start": ev_date.replace(hour=14, minute=0).strftime("%d/%m %H:%M"),
                    "end": "15:00",
                    "meet_link": "",
                    "description": "Check-up anual",
                    "upcoming": True
                }
            ]

        now = datetime.datetime.now(self.tz)
        start_window = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        end_window = (now + datetime.timedelta(days=days)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        ).isoformat()

        events_result = self.service.events().list(
            calendarId=self.settings.GOOGLE_CALENDAR_ID,
            timeMin=start_window,
            timeMax=end_window,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        raw_events = events_result.get('items', [])
        formatted = []
        for event in raw_events:
            # Filtra apenas eventos sem recorrência (que acontecem uma só vez)
            if event.get('recurringEventId') or event.get('recurrence'):
                continue

            start_raw = event['start'].get('dateTime', event['start'].get('date'))
            end_raw = event['end'].get('dateTime', event['end'].get('date'))

            date_part = f"{start_raw[8:10]}/{start_raw[5:7]}"
            start_fmt = f"{date_part} {start_raw[11:16]}" if 'T' in start_raw else f"{date_part} (Dia inteiro)"
            end_fmt = end_raw[11:16] if 'T' in end_raw else "Dia inteiro"

            meet_link = event.get('hangoutLink', '')
            if not meet_link and 'conferenceData' in event:
                entries = event['conferenceData'].get('entryPoints', [])
                for ep in entries:
                    if ep.get('entryPointType') == 'video':
                        meet_link = ep.get('uri', '')
                        break

            formatted.append({
                "summary": event.get('summary', 'Sem título'),
                "start": start_fmt,
                "end": end_fmt,
                "meet_link": meet_link,
                "description": event.get('description', ''),
                "upcoming": True
            })
        return formatted
