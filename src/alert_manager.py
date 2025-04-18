from .alert_entity import AlertProblem, AlertResolved, Alert
import asyncio
from .redis_cache import RedisCache
from .email_handler import EmailHandler
from .settings import setup_logger
import copy

logger = setup_logger(__name__)


class AlertManager:
    """Класс для управления алертами."""

    _flap_timer = 5 * 60
    _mass_timer = 5 * 60

    def __init__(self, email_handler: EmailHandler, redis_cache: RedisCache):
        self.email_handler = email_handler
        self.redis_cache = redis_cache
        self.active_flap_tasks = set()
        self.active_mass_tasks = set()
        self.active_timer_delete_tasks = set()

    async def problem_handler(self, message_id, host, severity, alert_type, subject: str, group,):
        """Добавляет алерт в кэш."""
        try:
            problem_alert = AlertProblem(message_id, host, alert_type, subject, severity, group)

            if not await self.redis_cache.get(problem_alert):
                await self.redis_cache.save(problem_alert)
            else:
                logger.info(f"Алерт {problem_alert.message_id} уже существует в кэше!")
                await self.email_handler.delete_message(problem_alert.message_id)
            await self.redis_cache.add_to_mass_group(problem_alert)
            await self.redis_cache.increase_flap_count(problem_alert)

            if problem_alert._flap_key not in self.active_flap_tasks:
                self.active_flap_tasks.add(problem_alert._flap_key)
                asyncio.create_task(self._check_flap_after_timeout(problem_alert))

            if not problem_alert.is_exclude_group and problem_alert._group_mass_key not in self.active_mass_tasks:
                self.active_mass_tasks.add(problem_alert._group_mass_key)
                asyncio.create_task(self._check_mass_issue_after_timeout(problem_alert))

            if problem_alert._cache_key not in self.active_timer_delete_tasks:
                self.active_timer_delete_tasks.add(problem_alert._cache_key)
                asyncio.create_task(self._check_after_timer_delete(problem_alert))
        except Exception as e:
            logger.error(f"Ошибка в problem_handler: {e}", exc_info=True)

    async def _check_after_timer_delete(self, problem_alert: AlertProblem):
        """Проверка после таймаута."""
        try:
            copy_problem_alert = copy.copy(problem_alert)
            await asyncio.sleep(copy_problem_alert.delete_time)

            if await self.redis_cache.get(copy_problem_alert):
                logger.info(f'Прошло {copy_problem_alert.delete_time} сек, отправляю нотификацию!')
                copy_problem_alert.is_regular = True
                await self.redis_cache.save(copy_problem_alert, {
                    "create_case": True,
                    "resolved_subject": copy_problem_alert.resolved_subject_msg()
                })
                await self.email_handler.send_alert_notification(copy_problem_alert)

            self.active_timer_delete_tasks.discard(problem_alert._cache_key)
        except Exception as e:
            logger.error(f"Ошибка в _check_after_timer_delete: {e}", exc_info=True)

    async def _check_flap_after_timeout(self, problem_alert: AlertProblem):
        """Ждет 5 минут и проверяет флапы."""
        try:
            copy_problem_alert = copy.copy(problem_alert)
            await asyncio.sleep(self._flap_timer)

            data = await self.redis_cache.get_flap_count(copy_problem_alert)
            logger.info(f"Данные флапа: {data}")
            if data and data["count"] >= 5:
                logger.warning(f"⚠️ Хост {copy_problem_alert.host} флапается! ({data['count']} за 5 минут)")
                copy_problem_alert.is_flapping = True
                await self.email_handler.send_alert_notification(copy_problem_alert, extra_data=data)

            self.active_flap_tasks.discard(copy_problem_alert._flap_key)
            await self.redis_cache.delete_flap(copy_problem_alert)
        except Exception as e:
            logger.error(f"Ошибка в _check_flap_after_timeout: {e}", exc_info=True)

    async def _check_mass_issue_after_timeout(self, problem_alert: AlertProblem):
        """Ждет 5 минут и проверяет массовость инцидента."""
        try:
            copy_problem_alert = copy.copy(problem_alert)
            await asyncio.sleep(self._mass_timer)

            data = await self.redis_cache.get_mass_group(copy_problem_alert)
            if data:
                total_issues = sum(len(issues) for issues in data.values())
                if total_issues >= 5:
                    logger.warning(f"🚨 Массовая проблема в группе {copy_problem_alert.group}! ({len(data['hosts'])} хостов)")
                    copy_problem_alert.is_massgroup_problem = True
                    await self.email_handler.send_alert_notification(copy_problem_alert, extra_data=data)

            self.active_mass_tasks.discard(copy_problem_alert._group_mass_key)
            await self.redis_cache.delete_mass_group(copy_problem_alert)
        except Exception as e:
            logger.error(f"Ошибка в _check_mass_issue_after_timeout: {e}", exc_info=True)

    async def resolved_handler(self, message_id, host, subject: str, alert_type):
        """Обрабатывает resolved."""
        try:
            resolved_alert = AlertResolved(message_id, host, alert_type, subject)
            cached_alert: dict = await self.redis_cache.get(resolved_alert)
            if cached_alert:
                problem_message_id = cached_alert.get('message_id')
                problem_folder_path = cached_alert.get('folder_path', '')
                resolved_folder_path = problem_folder_path.replace('problem', 'resolved')
                resolved_alert.resolved_subject_msg = cached_alert.get('resolved_subject')
                if cached_alert.get('create_case'):
                    await self.email_handler.send_alert_notification(resolved_alert)

                await self.email_handler.move_to_folder(problem_message_id, problem_folder_path)
                await self.email_handler.move_to_folder(resolved_alert.message_id, resolved_folder_path)

            await self.email_handler.delete_message(resolved_alert.message_id)
            await self.redis_cache.delete(resolved_alert)
        except Exception as e:
            logger.error(f"Ошибка в resolved_handler: {e}", exc_info=True)
