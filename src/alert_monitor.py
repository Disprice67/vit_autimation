import asyncio
from exchangelib import Message
import re
from .alert_manager import AlertManager
from .email_handler import EmailHandler
from .settings import setup_logger

logger = setup_logger(__name__)


class AlertMonitor:
    """Класс для мониторинга почты и обработки алертов."""

    def __init__(self, alert_manager: AlertManager, email_handler: EmailHandler):
        self.alert_manager = alert_manager
        self.email_handler = email_handler

    async def start(self,) -> None:
        """Запускает процесс мониторинга почты."""
        while True:
            try:
                await self.check_inbox()
            except Exception as e:
                logger.error(f'Ошибка в процессе мониторинга: {e}', exc_info=True)

    async def check_inbox(self) -> None:
        """Проверяет входящие сообщения"""
        loop = asyncio.get_running_loop()
        try:
            messages = await loop.run_in_executor(None, lambda: self.email_handler.account.inbox.filter(is_read=False))
            for msg in messages:
                msg.is_read = True
                try:
                    await self.proccess_email(msg)
                    await loop.run_in_executor(None, msg.save)
                except Exception as e:
                    logger.error(f'Ошибка при обработке сообщения: {e}', exc_info=True)
        except Exception as e:
            logger.error(f'Ошибка при проверке входящих сообщений: {e}', exc_info=True)

    async def parse_to_dict(self, email_message: Message) -> dict:
        """Парсим письмо и вытаскиваем нужную информацию в словарик."""
        try:
            body = email_message.text_body or ""
            body_re = re.sub(r"\s+", "", body)
            parsed_data = {
                'subject': email_message.subject,
                'sender': email_message.sender.email_address,
                'alert_type': 'Resolved' if 'Resolved' in email_message.subject else 'Problem',
                'host': await self._extract_value(body_re, r"Host:(.*?)(?:Groups|IP-adress|Severity|Time|$)"),
                'severity': await self._extract_value(body_re, r"Severity:(.*?)(?:Time|$)"),
                'groups': await self._extract_value(body_re, r"Groups:(.*?)(?:IP-adress|Severity|Time|$)")
            }
            logger.debug(f'Парсинг письма завершен: {parsed_data}')
            return parsed_data
        except Exception as e:
            logger.error(f'Ошибка при парсинге письма: {e}', exc_info=True)
            return {}

    @staticmethod
    async def _extract_value(text: str, pattern: str):
        """Извлекает значения по регулярному выражению."""
        try:
            match = re.search(pattern, text, re.DOTALL)
            return match.group(1) if match else ''
        except Exception as e:
            logger.error(f'Ошибка при извлечении значения: {e}', exc_info=True)
            return ''

    async def proccess_email(self, message: Message):
        """Проверяем почту."""
        try:
            parse_msg = await self.parse_to_dict(message)
            host = parse_msg.get('host')
            severity = parse_msg.get('severity')
            alert_type = parse_msg.get('alert_type')
            subject = parse_msg.get('subject')
            group = parse_msg.get('groups')

            logger.info(f'Обработка письма: host={host}, severity={severity}, alert_type={alert_type}, subject={subject}, group={group}')

            if not host:
                logger.warning('Не удалось извлечь хост из сообщения.')
                return

            if alert_type == 'Problem':
                await self.alert_manager.problem_handler(message.id, host, severity, alert_type, subject, group)
            elif alert_type == 'Resolved':
                await self.alert_manager.resolved_handler(message.id, host, subject, alert_type)
        except Exception as e:
            logger.error(f'Ошибка при обработке письма: {e}', exc_info=True)