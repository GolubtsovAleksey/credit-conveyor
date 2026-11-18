import logging  # в Python есть встроенный промышленный модуль logging


def setup_logger(name: str = "calculator") -> logging.Logger: # -> logging.Logger — подсказка типа возвращаемого значения (говорит IDE, что функция вернет объект логгера)
    logger = logging.getLogger(name) # запрашиваю у системы логгер с именем "calculator"
    if not logger.handlers:          # проверка, настроен ли этот логгер уже ранее (чтобы при повторном импорте файла сообщения не дублировались в консоли дважды).
        logger.setLevel(logging.INFO)  # Задал мин уровень важности. Логгер будет выводить инф сообщения (INFO), предупр (WARNING) и ошибки (ERROR), но игнор (DEBUG)
        handler = logging.StreamHandler()  # создал обработчик вывода. StreamHandler направляет логи прямо в стандартный поток вывода (терминал IDEA).
        formatter = logging.Formatter(     #шаблон каждой строчки лога:
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # asctime — дата и время события
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger() # • вызвал функцию один раз и сохранил в переменную logger, чтобы импортировать ее в сервисы и контроллеры.

