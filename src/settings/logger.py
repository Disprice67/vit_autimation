import logging


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Создает и настраивает общий логгер.
    :param name: Имя логгера (обычно __name__).
    :param level: Уровень логирования (по умолчанию INFO).
    :return: Настроенный логгер.
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger
