import requests
import logging
from src.config import get_settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.settings = get_settings()

    def send_message(self, text: str, phone: str = None) -> bool:
        target_phone = phone or self.settings.DESTINATION_PHONE
        if not target_phone:
            logger.warning("Nenhum telefone de destino configurado.")
            return False

        # Sanitiza número para o padrão internacional (E.164 sem o +)
        sanitized_phone = "".join(filter(str.isdigit, target_phone))

        url = f"{self.settings.EVOLUTION_BASE_URL.rstrip('/')}/message/sendText/{self.settings.INSTANCE_NAME}"
        headers = {
            "apikey": self.settings.EVOLUTION_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "number": sanitized_phone,
            "text": text
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code in [200, 201]:
                logger.info(f"Mensagem enviada com sucesso para {sanitized_phone}")
                return True
            logger.error(f"Erro Evolution API ({response.status_code}): {response.text}")
            return False
        except Exception as e:
            logger.error(f"Falha de conexão com a Evolution API: {e}")
            return False
