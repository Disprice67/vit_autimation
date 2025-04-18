import json
from typing import Optional, Any, Dict
from redis.asyncio import Redis
from .alert_entity import Alert, AlertProblem
from .settings import setup_logger


logger = setup_logger(__name__)


class RedisCache:
    """Класс для работы с кэшем Redis."""

    def __init__(self, redis: Redis) -> None:
        """Инициализирует экземпляр RedisCache."""
        self.redis = redis

    @classmethod
    async def create(cls, host: str, port: int = 6379) -> Optional["RedisCache"]:
        """
        Фабричный метод для создания экземпляра RedisCache.
        Проводит проверку подключения, очищает кэш и возвращает объект.
        """
        try:
            redis = Redis(host=host, port=port)
            await redis.ping()
            logger.info("Успешное подключение к Redis!")
            instance = cls(redis)
            await instance.clear_cache()
            return instance
        except Exception as e:
            logger.error(f"Ошибка при подключении к Redis: {e}")
            return None

    async def clear_cache(self) -> None:
        """Очищает весь кэш при запуске программы."""
        try:
            keys = await self.redis.keys("*")
            if keys:
                await self.redis.delete(*keys)
                logger.info("Кэш был очищен при запуске программы!")
            else:
                logger.info("Кэш уже пуст.")
        except Exception as e:
            logger.error(f"Ошибка при очистке кэша: {e}")

    async def increase_flap_count(self, entity: AlertProblem, expiration: int = 370) -> None:
        """
        Увеличивает счетчик флапов для заданного хоста.
        Если запись существует, увеличивает счётчик и добавляет новые данные;
        иначе – создаёт новую запись.
        """
        key = entity._flap_key
        try:
            cached = await self.redis.get(key)
            if cached:
                data = json.loads(cached)
                data['count'] += 1
                data['mass'].append((entity.subject, entity.severity))
            else:
                data = {
                    'count': 1,
                    'mass': [(entity.subject, entity.severity)]
                }
            await self.redis.set(key, json.dumps(data), ex=expiration)
            logger.info(f"Счетчик флапов для {key} увеличен.")
        except Exception as e:
            logger.error(f"Ошибка при увеличении счетчика флапов: {e}")

    async def add_to_mass_group(self, entity: AlertProblem, expiration: int = 370) -> None:
        """
        Добавляет информацию об алерте в массовую группу.
        Для каждого хоста хранится список кортежей (тема, уровень серьезности).
        """
        key = entity._group_mass_key
        try:
            cached = await self.redis.get(key)
            if cached:
                data: Dict[str, Any] = json.loads(cached)
                if entity.host in data:
                    data[entity.host].append((entity.subject, entity.severity))
                else:
                    data[entity.host] = [(entity.subject, entity.severity)]
            else:
                data = {entity.host: [(entity.subject, entity.severity)]}
            await self.redis.set(key, json.dumps(data), ex=expiration)
            logger.info(f"Данные добавлены в массовую группу для ключа {key}.")
        except Exception as e:
            logger.error(f"Ошибка при добавлении в массовую группу: {e}")

    async def get_mass_group(self, entity: AlertProblem) -> Optional[Dict[str, Any]]:
        """
        Получает данные о массовой проблеме для заданного хоста.
        Возвращает словарь вида {host: [(subject, severity), ...]} или None.
        """
        try:
            cached = await self.redis.get(entity._group_mass_key)
            if cached:
                logger.info(f"Данные массовой группы для {entity._group_mass_key} получены.")
                return json.loads(cached)
            logger.info(f"Данные массовой группы для {entity._group_mass_key} отсутствуют.")
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении массовой группы: {e}", exc_info=True)
            return None

    async def delete_mass_group(self, entity: AlertProblem) -> None:
        """Удаляет данные массовой проблемы из кэша."""
        try:
            await self.redis.delete(entity._group_mass_key)
        except Exception as e:
            logger.error(f"Ошибка при удалении массовой группы: {e}", exc_info=True)

    async def get_flap_count(self, entity: AlertProblem) -> Optional[Dict[str, Any]]:
        """
        Получает данные о флапах для заданного хоста.
        Возвращает словарь с количеством и списком уведомлений или None.
        """
        try:
            cached = await self.redis.get(entity._flap_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении флапов: {e}", exc_info=True)
            return None

    async def delete_flap(self, entity: AlertProblem) -> None:
        """Удаляет данные о флапах для заданного хоста."""
        try:
            await self.redis.delete(entity._flap_key)
        except Exception as e:
            logger.error(f"Ошибка при удалении флапов: {e}", exc_info=True)

    async def get(self, entity: AlertProblem) -> Optional[Dict[str, Any]]:
        """Получает данные из кэша по заданному ключу."""
        try:
            cached = await self.redis.get(entity._cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Не удалось получить данные из кэша: {e}", exc_info=True)
        return None

    async def delete(self, entity: AlertProblem) -> bool:
        """Удаляет элемент из кэша по заданному ключу."""
        try:
            result = await self.redis.delete(entity._cache_key)
            if result:
                logger.info(f"Элемент {entity._cache_key} удален из кэша.")
            else:
                logger.info(f"Элемент {entity._cache_key} не найден в кэше.")
            return bool(result)
        except Exception as e:
            logger.error(f"Ошибка при удалении элемента из кэша: {e}", exc_info=True)
            return False

    async def save(self, entity: AlertProblem, update_data: Optional[Dict[str, Any]] = None,
                   expiration: Optional[int] = None) -> None:
        """
        Сохраняет данные в кэше с возможностью обновления отдельных полей.
        :param entity: Объект алерта.
        :param update_data: Словарь с обновляемыми данными.
        :param expiration: Время жизни записи в секундах.
        """
        key = entity._cache_key
        try:
            cached = await self.redis.get(key)
            if cached:
                data = json.loads(cached)
            else:
                data = entity.__dict__
            if update_data:
                data.update(update_data)
            if expiration:
                await self.redis.set(key, json.dumps(data), ex=expiration)
            else:
                await self.redis.set(key, json.dumps(data))
            logger.info(f"Данные для {key} сохранены в кэше.")
        except Exception as e:
            logger.error(f"Ошибка сохранения данных в кэше: {e}", exc_info=True)
