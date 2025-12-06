import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулю конфигурации
sys.path.insert(0, str(Path(__file__).parent))

# Импорт модулей с обработкой ошибок
try:
    from agent import ShopAgent, DeliveryVehicleAgent
    from config.config_loader import ConfigLoader
except ImportError as e:
    print(f"[CRITICAL ERROR] Ошибка импорта модулей: {e}")
    print("Убедитесь, что файлы agent.py и config_loader.py находятся в правильных директориях.")
    sys.exit(1)


async def main():
    """Главная функция запуска системы"""

    print("############################################################")
    print("      ЗАПУСК МУЛЬТИАГЕНТНОЙ СИСТЕМЫ ДОСТАВКИ (MAS)          ")
    print("############################################################")

    # 1. Инициализация конфигурации
    try:
        loader = ConfigLoader("config")
    except FileNotFoundError:
        print("\n[INFO] Конфигурация не найдена. Создание файлов по умолчанию...")
        ConfigLoader.create_default_configs("config")
        loader = ConfigLoader("config")
        print("[INFO] Файлы созданы. Пожалуйста, проверьте папку config/.")
    except ValueError as e:
        print(f"\n[ERROR] Ошибка структуры конфигурации: {e}")
        return

    # 2. Загрузка данных
    try:
        vehicles_config = loader.load_vehicles_config()
        shops_config = loader.load_shops_config()
    except Exception as e:
        print(f"\n[ERROR] Не удалось загрузить конфигурацию: {e}")
        return

    print(f"\n[STATUS] Конфигурация загружена успешно.")
    print(f"   - XMPP Сервер: {vehicles_config['xmpp_server']}")
    print(f"   - Количество автомобилей: {len(vehicles_config['vehicles'])}")
    print(f"   - Количество магазинов: {len(shops_config['shops'])}")

    # 3. Запуск агентов-автомобилей
    vehicles = []
    vehicle_jids = [v["jid"] for v in vehicles_config["vehicles"]]

    print("\n---------------- ЗАПУСК АГЕНТОВ-АВТОМОБИЛЕЙ ----------------")
    for v_config in vehicles_config["vehicles"]:
        try:
            vehicle = DeliveryVehicleAgent(
                v_config["jid"],
                v_config["password"],
                v_config["capacity"],
                v_config["speed"]
            )
            # В версии SPADE 3+ start() является асинхронным
            await vehicle.start()

            vehicles.append(vehicle)
            v_name = v_config.get("name", v_config["jid"])
            print(f"[OK] {v_name} запущен. (Вместимость: {v_config['capacity']}, Скорость: {v_config['speed']})")

        except Exception as e:
            print(f"[ERROR] Не удалось запустить автомобиль {v_config['jid']}.")
            print(f"        Детали ошибки: {e}")
            print("        Возможная причина: XMPP сервер не доступен или неверный пароль.")
            # Прерываем, так как без транспорта система не имеет смысла
            break

    # Пауза для стабильной инициализации XMPP соединений
    print("[INFO] Ожидание инициализации сети (2 сек)...")
    await asyncio.sleep(2)

    # 4. Запуск агентов-магазинов
    shops = []

    print("\n---------------- ЗАПУСК АГЕНТОВ-МАГАЗИНОВ ------------------")
    for s_config in shops_config["shops"]:
        try:
            shop = ShopAgent(
                s_config["jid"],
                s_config["password"],
                s_config["shop_id"],
                tuple(s_config["location"]),
                tuple(s_config["time_window"]),
                s_config["needs"]
            )

            # Передаем список известных автомобилей агенту магазина
            shop.set("vehicles", vehicle_jids)

            await shop.start()

            shops.append(shop)
            needs_count = sum(s_config["needs"].values())
            print(
                f"[OK] Магазин {s_config['shop_id']} запущен. (Позиция: {s_config['location']}, Потребность: {needs_count} ед.)")

        except Exception as e:
            print(f"[ERROR] Не удалось запустить магазин {s_config['jid']}: {e}")

    print("\n" + "=" * 60)
    print("ВСЕ АГЕНТЫ АКТИВНЫ. НАЧАЛО ВЫПОЛНЕНИЯ СЦЕНАРИЯ.")
    print("Для завершения работы нажмите Ctrl+C")
    print("=" * 60 + "\n")

    # 5. Бесконечный цикл поддержания работы
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[USER STOP] Завершение работы системы...")

        # Корректная остановка агентов
        for vehicle in vehicles:
            if vehicle.is_alive():
                await vehicle.stop()

        for shop in shops:
            if shop.is_alive():
                await shop.stop()

        print("[STATUS] Система остановлена.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass