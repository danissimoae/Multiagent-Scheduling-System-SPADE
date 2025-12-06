import json
import os
from pathlib import Path


class ConfigLoader:
    """Класс для загрузки конфигураций из JSON файлов"""

    def __init__(self, config_dir="config"):
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Директория конфигурации '{config_dir}' не найдена")

    def load_vehicles_config(self, filename="vehicles.json"):
        """Загрузка конфигурации автомобилей"""
        config_path = self.config_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(f"Файл конфигурации '{config_path}' не найден")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Валидация конфигурации
        self._validate_vehicles_config(config)

        return config

    def load_shops_config(self, filename="shops.json"):
        """Загрузка конфигурации магазинов"""
        config_path = self.config_dir / filename

        if not config_path.exists():
            raise FileNotFoundError(f"Файл конфигурации '{config_path}' не найден")

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Валидация конфигурации
        self._validate_shops_config(config)

        return config

    def get_xmpp_server(self, config_type="vehicles"):
        """Получение адреса XMPP сервера из конфигурации"""
        if config_type == "vehicles":
            config = self.load_vehicles_config()
        else:
            config = self.load_shops_config()

        return config.get("xmpp_server", "localhost")

    def get_all_vehicle_jids(self):
        """Получение списка всех JID автомобилей"""
        config = self.load_vehicles_config()
        return [v["jid"] for v in config["vehicles"]]

    def get_vehicle_by_id(self, vehicle_id):
        """Получение конфигурации конкретного автомобиля по ID"""
        config = self.load_vehicles_config()
        for vehicle in config["vehicles"]:
            if vehicle["id"] == vehicle_id:
                return vehicle
        return None

    def get_shop_by_id(self, shop_id):
        """Получение конфигурации конкретного магазина по ID"""
        config = self.load_shops_config()
        for shop in config["shops"]:
            if shop["id"] == shop_id:
                return shop
        return None

    def _validate_vehicles_config(self, config):
        """Валидация конфигурации автомобилей"""
        if "xmpp_server" not in config:
            raise ValueError("Отсутствует поле 'xmpp_server' в конфигурации")

        if "vehicles" not in config:
            raise ValueError("Отсутствует поле 'vehicles' в конфигурации")

        required_fields = ["id", "jid", "password", "capacity", "speed"]
        for i, vehicle in enumerate(config["vehicles"]):
            for field in required_fields:
                if field not in vehicle:
                    raise ValueError(f"Отсутствует поле '{field}' у автомобиля #{i + 1}")

    def _validate_shops_config(self, config):
        """Валидация конфигурации магазинов"""
        if "xmpp_server" not in config:
            raise ValueError("Отсутствует поле 'xmpp_server' в конфигурации")

        if "shops" not in config:
            raise ValueError("Отсутствует поле 'shops' в конфигурации")

        required_fields = ["id", "jid", "password", "shop_id", "location", "time_window", "needs"]
        for i, shop in enumerate(config["shops"]):
            for field in required_fields:
                if field not in shop:
                    raise ValueError(f"Отсутствует поле '{field}' у магазина #{i + 1}")

            # Проверка формата location
            if not isinstance(shop["location"], list) or len(shop["location"]) != 2:
                raise ValueError(f"Поле 'location' должно быть списком из 2 элементов у магазина #{i + 1}")

            # Проверка формата time_window
            if not isinstance(shop["time_window"], list) or len(shop["time_window"]) != 2:
                raise ValueError(f"Поле 'time_window' должно быть списком из 2 элементов у магазина #{i + 1}")

    @staticmethod
    def create_default_configs(config_dir="config"):
        """Создание конфигурационных файлов по умолчанию"""
        config_path = Path(config_dir)
        config_path.mkdir(exist_ok=True)

        # Конфигурация автомобилей по умолчанию
        default_vehicles = {
            "xmpp_server": "localhost",
            "vehicles": [
                {
                    "id": 1,
                    "jid": "vehicle1@localhost",
                    "password": "vehicle1pass",
                    "capacity": 100,
                    "speed": 60,
                    "name": "Грузовик-1"
                },
                {
                    "id": 2,
                    "jid": "vehicle2@localhost",
                    "password": "vehicle2pass",
                    "capacity": 150,
                    "speed": 50,
                    "name": "Грузовик-2"
                },
                {
                    "id": 3,
                    "jid": "vehicle3@localhost",
                    "password": "vehicle3pass",
                    "capacity": 80,
                    "speed": 70,
                    "name": "Грузовик-3"
                }
            ]
        }

        # Конфигурация магазинов по умолчанию
        default_shops = {
            "xmpp_server": "localhost",
            "shops": [
                {
                    "id": 1,
                    "jid": "shop1@localhost",
                    "password": "shop1pass",
                    "shop_id": "Shop_A",
                    "location": [10, 20],
                    "time_window": [8, 18],
                    "needs": {
                        "product1": 50,
                        "product2": 30
                    }
                },
                {
                    "id": 2,
                    "jid": "shop2@localhost",
                    "password": "shop2pass",
                    "shop_id": "Shop_B",
                    "location": [25, 15],
                    "time_window": [9, 17],
                    "needs": {
                        "product1": 70,
                        "product3": 40
                    }
                },
                {
                    "id": 3,
                    "jid": "shop3@localhost",
                    "password": "shop3pass",
                    "shop_id": "Shop_C",
                    "location": [5, 30],
                    "time_window": [10, 16],
                    "needs": {
                        "product2": 60,
                        "product3": 20
                    }
                }
            ]
        }

        # Сохранение конфигураций
        vehicles_path = config_path / "vehicles.json"
        shops_path = config_path / "shops.json"

        with open(vehicles_path, 'w', encoding='utf-8') as f:
            json.dump(default_vehicles, f, indent=2, ensure_ascii=False)

        with open(shops_path, 'w', encoding='utf-8') as f:
            json.dump(default_shops, f, indent=2, ensure_ascii=False)

        print(f"✓ Созданы конфигурационные файлы в директории '{config_dir}/'")
        print(f"  - {vehicles_path}")
        print(f"  - {shops_path}")


# Пример использования
if __name__ == "__main__":
    # Создание конфигурационных файлов по умолчанию
    ConfigLoader.create_default_configs()

    # Загрузка и проверка
    loader = ConfigLoader()

    vehicles_config = loader.load_vehicles_config()
    print(f"\nЗагружено автомобилей: {len(vehicles_config['vehicles'])}")

    shops_config = loader.load_shops_config()
    print(f"Загружено магазинов: {len(shops_config['shops'])}")

    print(f"\nXMPP сервер: {loader.get_xmpp_server()}")
    print(f"JID автомобилей: {loader.get_all_vehicle_jids()}")