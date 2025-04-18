from .settings import RECIPIENTS_EMAILS, EMAIL_TAC
from exchangelib import Credentials, Account, Message, DELEGATE, ExtendedProperty
from datetime import datetime, time
import pytz
from .alert_entity import Alert, AlertProblem, AlertResolved
import asyncio
from typing import Optional
from .settings import setup_logger
from .telegram_bot import send_alert_to_telegram
from aiogram import Bot


logger = setup_logger(__name__)


class FollowUpFlag(ExtendedProperty):
    property_tag = 0x1090
    property_type = 'Integer'


Message.register('follow_up_flag', FollowUpFlag)


class EmailHandler:
    """Класс для мониторинга и управления почтой."""

    _recipients_emails = [RECIPIENTS_EMAILS]
    email_tac = EMAIL_TAC

    def __init__(self, bot, username, password):
        self.bot = bot
        self.username = username
        self.password = password

    async def _connect(self,):
        """Подключение к почте."""
        try:
            self.credentials = Credentials(self.username, self.password)
            self.account = Account(
                primary_smtp_address=self.username,
                credentials=self.credentials,
                autodiscover=True,
                access_type=DELEGATE
            )
            logger.info('Успешное подключение к почте.')
        except Exception as e:
            logger.error(f'Подключиться к почте не удалось. {e}')

    @classmethod
    async def create(cls, bot: Bot, username: str, password: str):
        """Фабричный метод для создания объекта с асинхронным подключением."""
        self = cls(bot, username, password)
        await self._connect()
        return self

    def _get_recipients(self, alert: AlertProblem):
        """Определяет список получателей в зависимости от типа алерта."""
        recipients = self._recipients_emails[:]
        if not alert.is_emergency:
            if alert.is_critical:
                recipients.append(self.email_tac)
            elif alert.severity in ['Disaster'] or alert.is_flapping or alert.is_massgroup_problem:
                recipients.append(self.email_tac)
        return recipients

    async def _get_subject_and_body_resolved(self, alert: AlertResolved):
        """Получаем тему и тело письма для resolved алертов."""
        return alert.resolved_subject_msg, f"Инцидент на {alert.host} решен."

    async def _get_subject_and_body_problem(self, alert: AlertProblem, extra_data=None,):
        """Формирует тему и тело письма в зависимости от типа алерта."""
        try:
            subject, body = "", ""
            if alert.is_regular:
                subject = alert.regular_subject_msg()
                body = self._build_body_message(alert)
            elif alert.is_flapping:
                subject = alert.flap_subject_msg()
                body = self._build_flap_body(alert, extra_data)
            elif alert.is_massgroup_problem:
                subject = alert.mass_subject_msg()
                body = self._build_mass_body(alert, extra_data)
            return subject, body
        except Exception as e:
            logger.error(f"Ошибка при формировании темы и тела письма: {e}", exc_info=True)
            return "ALERT", "Ошибка при формировании тела письма."

    async def send_alert_notification(self, alert: Alert, extra_data=None,):
        """Отправляет письмо в зависимости от типа алерта."""
        recipients = []
        subject, body = "", ""

        if isinstance(alert, AlertProblem):
            recipients = self._get_recipients(alert)
            subject, body = await self._get_subject_and_body_problem(alert, extra_data,)
        elif isinstance(alert, AlertResolved):
            recipients = self._recipients_emails[:]
            subject, body = await self._get_subject_and_body_resolved(alert,)

        message = await self.get_message(alert.message_id)
        if message:
            await send_alert_to_telegram(self.bot, message, subject, body, alert.alert_type)

        if self._is_within_sending_hours():
            await self.send_message(alert, recipients, subject, body)
            if isinstance(alert, AlertProblem):
                await self._mark_message(message)
                await self.copy_and_mark_message(message)
                logger.info(f"Письмо {message.subject} обработано и перемещено в 'create_case'.")

    def _is_within_sending_hours(self) -> bool:
        """Проверяет, находится ли текущее время в пределах 10:00–20:00 по Москве."""
        tz_moscow = pytz.timezone('Europe/Moscow')
        now = datetime.now(tz_moscow).time()
        start = time(10, 0)
        end = time(20, 0)
        return start <= now <= end

    def _build_mass_body(self, alert: AlertProblem, mass_data: Optional[dict]) -> str:
        """Формирует тело письма для массовой проблемы."""
        if not mass_data:
            return f"Массовая проблема в группе {alert.group}, но дополнительных данных нет."

        details = "\n".join(f"Хост: {host}, Тема: {subject}, Уровень: {severity}"
                            for host, alerts in mass_data.items()
                            for subject, severity in alerts)

        return f"Массовая проблема в группе {alert.group}!\n\nДетали:\n{details}"

    def _build_flap_body(self, alert: AlertProblem, flap_data: Optional[dict]) -> str:
        """Формирует тело письма для флап-алерта."""
        if not flap_data or "mass" not in flap_data:
            return f"Хост {alert.host} флапается слишком часто, но дополнительных данных нет."

        details = "\n".join(f"Тема: {subject}, Уровень: {severity}" for subject, severity in flap_data["mass"])
        count = flap_data.get("count", "N/A")

        return f"Хост {alert.host} флапается слишком часто ({count} раз за 5 минут)!\n\nСписок уведомлений:\n{details}"

    def _build_body_message(self, alert: AlertProblem,) -> str:
        """Формирует тело сообщения."""
        if alert.is_emergency:
            return" Прошло 8 минут без разрешения проблемы. Произошла авария!!!"
        elif alert.is_critical:
            return" Это критичный хост!!!"
        minutes = alert.delete_time // 60
        return f'\nПрошло {minutes} минут без разрешения проблемы. Требуется внимание!'

    async def get_message(self, message_id: str) -> Optional[Message]:
        """Получаем письмо по id."""
        try:
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: self.account.inbox.get(id=message_id)
            )
        except Exception as e:
            logger.error(f"Ошибка при получении письма {message_id}: {e}")
            return None

    async def _message_move(self, message: Message, folder_path: str):
        loop = asyncio.get_event_loop()
        try:
            folder_names = folder_path.split('\\')

            folder = self.account.inbox
            for name in folder_names:
                folder = folder / name
            await loop.run_in_executor(None, lambda: message.move(to_folder=folder))
            logger.info(f"Письмо {message.subject} перемещено в {folder_path}.")

        except Exception as e:
            logger.error(f"Ошибка при перемещении письма {message.subject} в {folder_path}: {e}")

    async def delete_message(self, message_id: str):
        """Удаляет письмо по message_id."""
        try:
            message = await self.get_message(message_id)
            if message:
                await asyncio.get_running_loop().run_in_executor(None, message.delete)
                logger.info(f"Письмо {message.subject} удалено.")
            else:
                logger.info(f"Письмо {message_id} не найдено.")
        except Exception as e:
            logger.error(f"Ошибка при удалении письма {message_id}: {e}")

    async def forward_message(self, message: Message, recipients, subject, body):
        """Пересылает сообщение получателям."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: message.create_forward(
            subject=subject,
            body=body,
            to_recipients=recipients
        ).send())
        logger.info(f"Письмо {message.subject} успешно переслано.")

    async def copy_and_mark_message(self, message: Message):
        """Копирует письмо в 'create_case', помечает его как непрочитанное."""
        loop = asyncio.get_running_loop()

        copied_message_id, _ = await loop.run_in_executor(
            None, lambda: message.copy(to_folder=self.account.inbox / 'create_case')
        )

        copied_message: Message = await self.get_message(copied_message_id)
        if copied_message:
            copied_message.is_read = False
            await self._mark_message(copied_message)
            await loop.run_in_executor(None, copied_message.save)
            logger.info(f"Скопированное письмо {copied_message.subject} помечено как непрочитанное.")
        else:
            logger.error(f"Ошибка: скопированное письмо {copied_message.subject} не найдено.")

    async def send_message(self, alert_entity: Alert, recipients, subject: str = None, body: str = None):
        """Отправляет сообщение и копирует его в 'create_case'."""
        try:
            message: Message = await self.get_message(alert_entity.message_id)
            if not message:
                logger.error(f"Ошибка: письмо {alert_entity.message_id} не найдено.")
                return

            await self.forward_message(message, recipients, subject, body)
            await asyncio.get_running_loop().run_in_executor(None, message.refresh)

            await asyncio.get_running_loop().run_in_executor(None, message.save)
        except Exception as e:
            logger.error(f'Ошибка при обработке письма {alert_entity.message_id}: {e}', exc_info=True)

    async def _mark_message(self, message: Message):
        """Отметить сообщение."""
        try:
            message.importance = 'High'
        except Exception as e:
            logger.error(f'Не удалось отметить/выделить сообщение: {e}', exc_info=True)

    async def unmark_message(self, message: Message):
        """Убирает все пометки с сообщения."""
        try:
            message.importance = 'Normal'
            await asyncio.get_running_loop().run_in_executor(None, message.save)
        except Exception as e:
            logger.error(f'Не удалось убрать метки с сообщения: {e}', exc_info=True)

    async def move_to_folder(self, message_id: int, folder_path: str = None):
        """Перемещает письмо в папку."""
        try:
            message: Message = await self.get_message(message_id)
            if not message:
                logger.error(f"Ошибка: письмо {message_id} не найдено.")
                return

            await asyncio.get_running_loop().run_in_executor(None, message.save)
            await self._message_move(
                message,
                folder_path
            )
        except Exception as e:
            logger.error(f'Ошибка при перемещении письма {message_id}: {e}', exc_info=True)
