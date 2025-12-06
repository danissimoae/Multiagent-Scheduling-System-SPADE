import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулю конфигурации
sys.path.insert(0, str(Path(__file__).parent))

from agent import ShopAgent, DeliveryVehicleAgent
from config.config_loader import ConfigLoader


async def main():
    """Главная функция запуска системы"""

    print("=" * 60)
    print("СИСТЕМА ДОСТАВКИ ТОВАРОВ ПО МАГАЗИНАМ")
    print("=" * 60)

    # Создание загрузчика конфигурации
    try:
        loader = ConfigLoader("config")
    except FileNotFoundError as e:
        print(f"\nОшибка: {e}")
        print("\nСоздаю конфигурационные файлы по умолчанию...")
        ConfigLoader.create_default_configs("config")
        loader = ConfigLoader("config")
        print("✓ Конфигурационные файлы созданы!")
        print("✓ Отредактируйте файлы config/vehicles.json и config/shops.json при необходимости\n")

    # Загрузка конфигураций
    try:
        vehicles_config = loader.load_vehicles_config()
        shops_config = loader.load_shops_config()
    except Exception as e:
        print(f"\nОшибка загрузки конфигурации: {e}")
        return

    print(f"\nЗагружена конфигурация:")
    print(f"   XMPP сервер: {vehicles_config['xmpp_server']}")
    print(f"   Автомобилей: {len(vehicles_config['vehicles'])}")
    print(f"   Магазинов: {len(shops_config['shops'])}")

    # Создание и запуск агентов-автомобилей
    vehicles = []
    vehicle_jids = [v["jid"] for v in vehicles_config["vehicles"]]

    print("\n--- ЗАПУСК АВТОМОБИЛЕЙ ---")
    for v_config in vehicles_config["vehicles"]:
        vehicle = DeliveryVehicleAgent(
            v_config["jid"],
            v_config["password"],
            v_config["capacity"],
            v_config["speed"]
        )
        await vehicle.start()
        vehicles.append(vehicle)
        vehicle_name = v_config.get("name", v_config["jid"])
        print(f"✓ {vehicle_name} (вместимость: {v_config['capacity']}, скорость: {v_config['speed']} км/ч)")

    # Небольшая задержка для инициализации
    await asyncio.sleep(2)

    # Создание и запуск агентов-магазинов
    shops = []

    print("\n--- ЗАПУСК МАГАЗИНОВ ---")
    for s_config in shops_config["shops"]:
        shop = ShopAgent(
            s_config["jid"],
            s_config["password"],
            s_config["shop_id"],
            tuple(s_config["location"]),
            tuple(s_config["time_window"]),
            s_config["needs"]
        )

        # Передаем список автомобилей магазину
        shop.set("vehicles", vehicle_jids)

        await shop.start()
        shops.append(shop)

        total_needs = sum(s_config["needs"].values())
        print(f"✓ {s_config['shop_id']} (позиция: {s_config['location']}, товаров: {total_needs})")

    print("\n" + "=" * 60)
    print("ВСЕ АГЕНТЫ ЗАПУЩЕНЫ - СИСТЕМА РАБОТАЕТ")
    print("=" * 60)
    print("\nНаблюдайте за взаимодействием агентов...")
    print("Для остановки нажмите Ctrl+C\n")

    try:
        # Работа системы
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n\n--- ОСТАНОВКА СИСТЕМЫ ---")

        # Остановка всех агентов
        for vehicle in vehicles:
            await vehicle.stop()
            print(f"✓ Автомобиль остановлен")

        for shop in shops:
            await shop.stop()
            print(f"✓ Магазин остановлен")

        print("\nСистема остановлена.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем")