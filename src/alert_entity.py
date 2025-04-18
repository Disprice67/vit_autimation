import json
from .settings.config import CRITICAL_HOSTS, EXCLUDE_GROUPS
import os
from .settings import setup_logger

logger = setup_logger(__name__)


class Alert:
    """Общий класс для алертов."""

    def __init__(self, message_id: int, host: str, alert_type: str, subject: str,):
        try:
            self.message_id = message_id
            self.host = host
            self.alert_type = alert_type
            self.subject = subject
        except Exception as e:
            logger.error(f"Ошибка при инициализации Alert: {e}", exc_info=True)

    @property
    def _cache_key(self) -> str:
        """Создает ключ для кэша."""
        return f'{self.host}:{self.subject}'

    @property
    def _json_alert(self):
        """Преобразует alert в json."""
        return json.dumps(self.__dict__)

    def _defines_a_folder(self,):
        """Определяет папку."""
        try:
            base_folder = ''
            if isinstance(self, AlertProblem):
                if self.is_exclude_group:
                    base_folder = "pbo"
                elif self.is_critical:
                    base_folder = "critical_host"
                elif self.severity == "High":
                    base_folder = "high"
                elif self.severity == "Disaster":
                    base_folder = "disaster"
                else:
                    return
            folder_path = os.path.join(base_folder, "problem")
            return folder_path
        except Exception as e:
            logger.error(f"Ошибка при определении папки: {e}", exc_info=True)
            return ""

class AlertProblem(Alert):
    """Класс для problem алертов."""

    _critical_hosts = {
        "Database Is Down": [
            "ORACLE HR_Database",
            "ORACLE RO_Database",
            "ORACLE Finance_Database"
        ],
        "Zabbix agent is not available": [
            "RUMOSDB8001", "RUMOSAP8001", "RUMOSDB28", "RUMOSAP28", "RUMOSDB29", "RUMOSAP29",
            "RUMOSDB2101", "RUMOSAP2102", "RUMOSAP2105", "RUMOSAP2106", "RUMOSAP2107", "RUMOSAP2108"
        ],
        "Synthetic test has failed": [
            "Oracle HR Synthetic test",
            "Oracle Finance Synthetic test",
            "EDF Synthetic test",
            "PCW Synthetic test",
            "RIT Synthetic test"
        ],
        "Service is unavailable": [
            "RUMOSDB2101_Database"
        ],
        "“Service” is not running": [
            "RUMOSAP"
        ],
        "Container Restarts in McDonalds Namespace (>2 every second)": [],
        "loyalty_service_add < 5 за 1 час": [],
        "loyalty_apply_award <10 (daytime)": [],
        "loyalty_apply_award =0 (nighttime)": [],
        "loyalty_service_create_account < 10 (daytime)": [],
        "payment_atol_rps < 300 (daytime)": [],
        "payment_sber_rps < 700 (daytime)": [],
        "payment_atol_ok = 0": [],
        "Disaster ошибки с оплатой Sber": [],
        "Disaster ошибки с оплатой АТОЛ": [],
        "OffersRedeem <10 (daytime)": [],
        "IdentifiedSales<100 (daytime)": [],
        "IdentifiedSales =0 (nighttime)": [],
        "promocode_entered > 5000": [],
        "promocode_entered = 0 (nighttime)": [],
        "promocode_entered = 0 (daytime)": [],
        "invalid_promocode > 150": [],
        "Резкое падение payment_sber_rps (20%) (daytime)": [],
        "Nginx Controller Connections delta > 50% (daytime)": [],
        "Nginx Controller Connections > 25000": [],
        "Резкое изменение payment_sber_rps > 50% (daytime)": [],
        "Резкое изменение order_processdo > 50% (daytime)": [],
        "payment_sber_hold > order_processdo by 500": [],
        "payment_sber_hold > payment_sber_complete by 500": [],
        "Unavailable by ICMP ping for 3m/10m/ Zabbix agent not available": [
            "RUMOSRDS101"
        ],
        "Unavailable by ICMP ping for 3m/10m/Zabbix agent not available": [
            "RUMOSJH101", "RUMOSRD050", "RUMOSRD051", "RUMOSRD052", "RUMSKAP95", "RUMSKRDS01",
            "RUMOSIS111", "RUMOSAS101", "RUMOSAS102", "RUMOSAS103", "RUMOSAP101", "RUMOSAP109",
            "RUMOSAP1410", "RUMOSPS101", "RUMOSDB1102", "RUMSKDB02", "RUMOSDC211", "RUMOSDC221",
            "RUMOSFS221", "RUMOSFS223", "RUMOSAP2201", "RUMOSDB2201", "RUMOSAP2202", "RUMOSAP2203",
            "RUMOSAP2205", "RUMOSAP2206", "RUMOSAP2212", "RUMOSAP2213", "RUMOSAP2214", "RUMOSAP2301",
            "RUMOSDB2301", "RUMOSAP2701", "RUMOSDB2702", "RUMOSAP3602", "YC-WA-211", "YC-WA-221",
            "RUMOSWA211", "RUMOSWA221", "RUMOSFE211", "RUMOSFE221", "YC-FE-211", "YC-FE-221",
            "RUMOSJH221", "DFS-DB01", "DFS-DC01", "DFS-DC02", "DFS-Micro01", "DFS-Micro02",
            "DFS-Web01", "DFS-Web02", "App-101", "App-102", "App-103", "App-104", "App-105",
            "App-106", "App-107", "App-108", "App-109", "App-110", "App-111", "App-112", "DB-01",
            "DB-02", "DB-03", "DB-04", "DB-05", "Master-01", "Master-02", "Master-03", "Monitor-01",
            "Nat-instance-01", "nat-instance-mobileapplication-production", "Nexus-01", "Nginx-101",
            "Nginx-102", "rabbitmq-node-01-instance-mobileapplication-production",
            "rabbitmq-node-02-instance-mobileapplication-production",
            "rabbitmq-node-03-instance-mobileapplication-production",
            "rabbitmq-node-04-instance-mobileapplication-production",
            "rabbitmq-node-05-instance-mobileapplication-production", "admin01", "app-01", "app-02",
            "app-03", "bln-01", "bln-02", "cache-01", "DB-01", "DB-02", "Infra-01", "nat-inst",
            "rabbit-01", "search-01", "search-02", "search-03", "RUMOSAP2705", "RUMOSAP2706",
            "router-interconnect-prod", "sentry-production", "itlab-runner-android-001",
            "gitlab-access", "pcw-rit-router", "pcw-prod-nat", "cl1qtfdrdeidivas7olv-inov",
            "cl1qtfdrdeidivas7olv-ilol", "cl1qtfdrdeidivas7olv-adip", "cl1qtfdrdeidivas7olv-ajil",
            "cl1uvn1b4hhombg10ilh-emog", "cl1ohn8s7crtr6993l3i-orug", "cl1k1vknt3bpm9us6671-yqup",
            "svz-backup-12022024", "ruyandmz02", 'RUMOSAP2211'
        ]
    }
    _exclude_groups = EXCLUDE_GROUPS

    _EMERGENCY_ALERTS = {
        "Unavailable by ICMP ping": ["GSC01", "GSC02", "RHS01", "RHS02", "POS02", "POS19", "POS06", "POS07", "POS21", "POS09", "POS18", "POS22", "KVS01", "KVS07", "KVS09", "BOS01"],
        "WerFault": ["GSC01", "GSC02", "RHS01", "RHS02", "POS02", "POS19", "POS06", "POS07", "POS21", "POS09", "POS18", "POS22", "KVS01", "KVS07", "KVS09", "BOS01"],
        "License grace period < 7 days": ["GSC01", "GSC02"],
        "CSO Config File not exist": ["GSC01", "GSC02"],
        "KDS Balancer config not exist": ["GSC01", "GSC02"],
        "Disk space is low (free < 10% for 30m)": ["GSC01", "GSC02", "RHS01", "RHS02", "POS02", "POS19", "POS06", "POS07", "POS21", "POS09", "POS18", "POS22", "KVS01", "KVS07", "KVS09", "BOS01"]
    }

    def __init__(self, message_id, host, alert_type, subject, severity: str = None, group: str = None):
        try:
            super().__init__(message_id, host, alert_type, subject,)
            self.severity = severity
            self.group = group
            self.is_critical = self._is_critical_host(subject, host)
            self.is_emergency = self._check_emergency(subject, host) if not self.is_critical else False
            self.is_exclude_group = True if self._exclude_groups in group else False
            self.create_case = False
            self.is_flapping = False
            self.is_massgroup_problem = False
            self.is_regular = False
            self.resolved_subject = self.resolved_subject_msg()
            self.folder_path = self._defines_a_folder()
            self.delete_time = self._set_delete_timer()
        except Exception as e:
            logger.error(f"Ошибка при инициализации AlertProblem: {e}", exc_info=True)

    def _check_emergency(self, subject: str, host: str) -> bool:
        for alert_subject, critical_hosts in self._EMERGENCY_ALERTS.items():
            if alert_subject in subject:
                if any(critical_host in host for critical_host in critical_hosts):
                    return True
        return False

    def _is_critical_host(self, subject: str, host: str) -> bool:
        """
        Проверяет, является ли хост критичным на основе темы и словаря _critical_hosts.
        Если тема входит в словарь и у нее есть значения, проверяет наличие хоста в этих значениях.
        Если тема входит в словарь, но значений нет, считает хост критичным без проверки.
        """
        for alert_subject, critical_hosts in self._critical_hosts.items():
            if alert_subject in subject:
                if critical_hosts:
                    if any(critical_host in host for critical_host in critical_hosts):
                        return True
                else:
                    return True
        return False

    @property
    def _flap_key(self) -> str:
        """Создает ключ для флапа."""
        return f'flap:{self.host}'

    @property
    def _group_mass_key(self) -> str:
        """Создаем ключ для массовой проблемы."""
        return f'mass_group:{self.group}'

    @property
    def subject(self,):
        """Возвращает тему сообщения."""
        return self._subject

    @subject.setter
    def subject(self, value: str):
        """Удаляет нежелательные символы из темы, если это problem alert."""
        try:
            self._subject = value.replace('❌', '')
        except Exception as e:
            logger.error(f"Ошибка при установке subject: {e}", exc_info=True)

    def resolved_subject_msg(self):
        """Создает тему для resolved письма."""
        if self.is_critical:
            return f"✅ Resolved CRITICAL_HOST!!! {self.subject}"
        elif self.is_emergency:
            return f"✅ Resolved EMERGENCY!!! {self.subject}"
        return f"✅ Resolved {self.subject}"

    def regular_subject_msg(self):
        """Создает тему для problem письма."""
        if self.is_critical:
            return f"❌ CRITICAL_HOST!!! {self.subject}"
        elif self.is_emergency:
            return f"❌ EMERGENCY!!! {self.subject}"
        return f"❌ {self.subject}"

    def flap_subject_msg(self):
        """Создает тему для флапов или массовых проблем."""
        if self.is_flapping:
            return f"❌ FLAPPING!!! {self.subject}"

    def mass_subject_msg(self):
        """Создает тему для массовых проблем."""
        if self.is_massgroup_problem:
            return f"❌ MASS_GROUP_PROBLEM!!! {self.subject}"

    def _set_delete_timer(self,):
        """Устанавливает таймер на удаление."""
        try:
            if self.is_critical:
                return 0
            elif self.is_emergency:
                return 8 * 60
            elif self.severity == 'High':
                return 17 * 60
            elif self.severity == 'Disaster':
                return 8 * 60
        except Exception as e:
            logger.error(f"Ошибка при установке таймера удаления: {e}", exc_info=True)
            return -1

class AlertResolved(Alert):
    """Класс для resolved алертов."""

    def __init__(self, message_id, host, alert_type, subject,):
        try:
            super().__init__(message_id, host, alert_type, subject,)
            self.resolved_subject_msg = ""
        except Exception as e:
            logger.error(f"Ошибка при инициализации AlertResolved: {e}", exc_info=True)

    @property
    def subject(self,):
        """Возвращает тему сообщения."""
        return self._subject

    @subject.setter
    def subject(self, value: str):
        """Удаляет нежелательные символы из темы, если это problem alert."""
        try:
            self.resolved_subject_msg = value
            self._subject = value.replace(' Resolved', '').replace('✅', '')
        except Exception as e:
            logger.error(f"Ошибка при установке subject: {e}", exc_info=True)\
