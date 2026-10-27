"""
Расчёт состояния оплаты для пира.

Логика вынесена отдельно, потому что её используют три места: объект
Peer (для выдачи в API), сводка по всем конфигурациям и push-уведомления.
Раньше расчёт жил в DashboardClients и был привязан к учётной записи
клиента, но клиент и пир - разные сущности: пир может существовать без
клиента, и наоборот. Для администратора важнее пир, поэтому состояние
считается по пиру.

Статусы:
  unset    - срок не задан
  active   - оплачено, до истечения больше порога
  expiring - срок заканчивается (по умолчанию <= 5 дней)
  expired  - просрочено
"""
import datetime
from typing import Any

# Число дней до конца срока, начиная с которых оплата считается
# заканчивающейся. Этот порог управляет и подсветкой карточки пира, и
# счётчиками в сводке, поэтому он задаётся в одном месте.
EXPIRING_WITHIN_DAYS = 5

# Срок для бессрочной оплаты ("Безлимит"). Хранится в существующей колонке
# paid_until без миграции схемы: дата достаточно далека, чтобы никогда не
# наступить, а SQLite DATETIME спокойно её принимает (TIMESTAMP в MySQL
# ограничен 2038 годом, но проект работает на SQLite).
UNLIMITED_PAID_UNTIL_STR = "9999-12-31"
UNLIMITED_PAID_UNTIL = datetime.date(9999, 12, 31)


def IsUnlimitedPaidUntil(value: Any) -> bool:
    """
    Проверяет, является ли срок бессрочным ("Безлимит").
    """
    parsed = NormalizePaidUntil(value)
    return parsed is not None and parsed.date() == UNLIMITED_PAID_UNTIL


def NormalizePaidUntil(value: Any) -> datetime.datetime | None:
    """
    Приводит значение из БД к datetime или None.

    Нужно, потому что приходят как datetime (sqlite), так и строки
    разных форматов, в том числе из JSON-источников.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 0:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
    return None


def ComputePaymentStatus(paidUntil: Any) -> tuple[str, int | None, str | None]:
    """
    Возвращает (PaymentStatus, DaysRemaining, PaidUntilFormatted).
    """
    parsed = NormalizePaidUntil(paidUntil)
    if parsed is None:
        return "unset", None, None
    # "Безлимит": бессрочный пир. Статус остаётся active, чтобы вся
    # существующая логика (счётчики сводки, фильтры, уведомления) работала
    # без изменений; DaysRemaining не имеет смысла, поэтому None, а дата
    # отдаётся маркером - фронтенд по нему показывает бейдж "Безлимит".
    if parsed.date() == UNLIMITED_PAID_UNTIL:
        return "active", None, UNLIMITED_PAID_UNTIL_STR
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Срок считается истёкшим в конце указанного дня: полночь, к которой
    # прибавлен срок, ещё относится к оплаченному дню.
    days = (parsed.date() - today.date()).days
    if days < 0:
        status = "expired"
    elif days <= EXPIRING_WITHIN_DAYS:
        # Граница включительная: осталось ровно 5 дней - уже "истекает",
        # и карточка пира красится в жёлтый
        status = "expiring"
    else:
        status = "active"
    return status, days, parsed.strftime("%Y-%m-%d")


def ParsePaidUntilInput(value: Any) -> tuple[datetime.datetime | None, str | None]:
    """
    Разбирает дату, введённую администратором.

    Пустая строка означает "сбросить срок" и возвращает (None, None).
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None, None
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(value[:19], fmt), None
            except ValueError:
                continue
        return None, "Paid until must be in YYYY-MM-DD format"
    return None, "Paid until must be in YYYY-MM-DD format"
