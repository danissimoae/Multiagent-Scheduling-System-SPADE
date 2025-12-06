import json
import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from datetime import datetime
import random


class DeliveryVehicleAgent(Agent):
    """Агент-автомобиль доставки"""

    def __init__(self, jid, password, capacity, speed=50):
        super().__init__(jid, password)
        self.capacity = capacity
        self.speed = speed
        self.current_load = 0
        self.current_position = (0, 0)
        self.schedule = []
        self.available = True

    class ReceiveRequestBehaviour(CyclicBehaviour):
        """Поведение для приема запросов от магазинов"""

        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                try:
                    request_data = json.loads(msg.body)
                    msg_type = request_data.get("type")

                    if msg_type == "delivery_request":
                        print(f"\n[Vehicle {self.agent.name}] >> Получен ЗАПРОС от {request_data.get('shop_id')}")
                        await self.handle_delivery_request(msg, request_data)
                    elif msg_type == "query_availability":
                        await self.handle_availability_query(msg)

                except json.JSONDecodeError:
                    print(f"[Vehicle {self.agent.name}] Ошибка: Неверный формат JSON в сообщении")

        async def handle_delivery_request(self, msg, request_data):
            """Обработка запроса на доставку с подробным расчетом"""
            shop_id = request_data.get("shop_id")
            products = request_data.get("products", {})
            location = tuple(request_data.get("location", [0, 0]))

            # 1. Анализ груза
            request_quantity = sum(products.values())
            current_free_space = self.agent.capacity - self.agent.current_load

            # Проверка условий
            is_capacity_ok = request_quantity <= current_free_space
            can_deliver = self.agent.available and is_capacity_ok

            # 2. Расчет логистики
            distance = self.calculate_distance(self.agent.current_position, location)
            delivery_time = distance / self.agent.speed if self.agent.speed > 0 else float('inf')

            # 3. Расчет стоимости (Тариф: 10 у.е. за км)
            tariff_per_km = 10
            cost = distance * tariff_per_km

            response = Message(to=str(msg.sender))
            response.set_metadata("performative", "propose")

            print(f"[Vehicle {self.agent.name}] -- Логика расчета для {shop_id} --")
            print(
                f"   1. Вместимость: Требуется {request_quantity} | Свободно {current_free_space} | Статус: {'OK' if is_capacity_ok else 'ПЕРЕГРУЗ'}")
            print(f"   2. Дистанция: {distance:.2f} км (от {self.agent.current_position} до {location})")
            print(f"   3. Стоимость: {distance:.2f} км * {tariff_per_km} у.е. = {cost:.2f} у.е.")

            if can_deliver:
                proposal = {
                    "type": "delivery_proposal",
                    "vehicle_id": self.agent.name,
                    "can_deliver": True,
                    "cost": cost,
                    "estimated_time": delivery_time,
                    "distance": distance,
                    "capacity_available": current_free_space
                }
                print(f"[Vehicle {self.agent.name}] << Отправлено ПРЕДЛОЖЕНИЕ: Стоимость {cost:.2f}")
            else:
                proposal = {
                    "type": "delivery_proposal",
                    "vehicle_id": self.agent.name,
                    "can_deliver": False,
                    "reason": "Недостаточная вместимость или занят"
                }
                print(f"[Vehicle {self.agent.name}] << Отправлен ОТКАЗ (нет места или занят)")

            response.body = json.dumps(proposal)
            await self.send(response)

        async def handle_availability_query(self, msg):
            response = Message(to=str(msg.sender))
            response.set_metadata("performative", "inform")
            response.body = json.dumps({
                "type": "availability_response",
                "available": self.agent.available
            })
            await self.send(response)

        def calculate_distance(self, pos1, pos2):
            return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    class ExecuteDeliveryBehaviour(OneShotBehaviour):
        async def run(self):
            if self.agent.schedule:
                delivery = self.agent.schedule.pop(0)
                print(f"[Vehicle {self.agent.name}] Начинаю доставку в {delivery['shop_id']}...")
                await asyncio.sleep(delivery['estimated_time'])

                confirm_msg = Message(to=delivery['shop_jid'])
                confirm_msg.set_metadata("performative", "inform")
                confirm_msg.body = json.dumps({
                    "type": "delivery_completed",
                    "vehicle_id": self.agent.name,
                    "shop_id": delivery['shop_id']
                })
                await self.send(confirm_msg)
                self.agent.available = True
                print(f"[Vehicle {self.agent.name}] Доставка в {delivery['shop_id']} завершена.")

    async def setup(self):
        print(f"[INFO] Автомобиль {self.name} запущен (JID: {self.jid})")
        self.add_behaviour(self.ReceiveRequestBehaviour())


class ShopAgent(Agent):
    """Агент-магазин"""

    def __init__(self, jid, password, shop_id, location, time_window, needs):
        super().__init__(jid, password)
        self.shop_id = shop_id
        self.location = location
        self.time_window = time_window
        self.needs = needs
        self.proposals = []
        self.request_sent = False
        self.best_proposal_selected = False

    class SendRequestBehaviour(OneShotBehaviour):
        async def run(self):
            await asyncio.sleep(random.uniform(0.5, 2.0))

            print(f"\n[Shop {self.agent.shop_id}] >> Формирование заказа")
            print(f"[Shop {self.agent.shop_id}] Потребности: {self.agent.needs}")

            try:
                vehicles = self.agent.get("vehicles")
            except KeyError:
                vehicles = []

            if not vehicles:
                print(f"[Shop {self.agent.shop_id}] ОШИБКА: Нет известных автомобилей.")
                return

            request = {
                "type": "delivery_request",
                "shop_id": self.agent.shop_id,
                "location": self.agent.location,
                "products": self.agent.needs,
                "time_window": self.agent.time_window,
                "timestamp": datetime.now().isoformat()
            }

            print(f"[Shop {self.agent.shop_id}] Рассылка запроса {len(vehicles)} автомобилям...")
            for vehicle_jid in vehicles:
                msg = Message(to=vehicle_jid)
                msg.set_metadata("performative", "request")
                msg.body = json.dumps(request)
                await self.send(msg)

            self.agent.request_sent = True

    class ReceiveProposalBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=1)
            if msg:
                try:
                    data = json.loads(msg.body)
                    msg_type = data.get("type")

                    if msg_type == "delivery_proposal":
                        vid = data.get('vehicle_id')
                        cost = data.get('cost')

                        if data.get("can_deliver"):
                            print(f"[Shop {self.agent.shop_id}] Принято предложение от {vid}: Стоимость {cost:.2f}")
                            self.agent.proposals.append(data)
                            # Сохраняем JID отправителя для ответа
                            self.agent.proposals[-1]["vehicle_jid"] = str(msg.sender)
                        else:
                            print(f"[Shop {self.agent.shop_id}] Получен отказ от {vid}: {data.get('reason')}")

                    elif msg_type == "delivery_completed":
                        print(f"[Shop {self.agent.shop_id}] ТОВАР ПОЛУЧЕН от {data.get('vehicle_id')}. Заказ закрыт.")
                        self.agent.best_proposal_selected = False

                except json.JSONDecodeError:
                    pass

            # Логика выбора лучшего предложения
            if self.agent.request_sent and not self.agent.best_proposal_selected:
                # Ждем сбора всех предложений (эмуляция ожидания 4 сек)
                await asyncio.sleep(4)
                await self.select_best_proposal()

        async def select_best_proposal(self):
            if not self.agent.proposals:
                print(f"[Shop {self.agent.shop_id}] ВНИМАНИЕ: Нет активных предложений. Повтор запроса...")
                self.agent.request_sent = False
                self.agent.add_behaviour(self.agent.SendRequestBehaviour())
                return

            # Вывод таблицы сравнения
            print(f"\n[Shop {self.agent.shop_id}] --- АНАЛИЗ ПРЕДЛОЖЕНИЙ ---")
            print(f"{'Автомобиль':<20} | {'Стоимость':<10} | {'Время (ч)':<10} | {'Дистанция':<10}")
            print("-" * 60)

            for p in self.agent.proposals:
                print(
                    f"{p['vehicle_id']:<20} | {p['cost']:<10.2f} | {p['estimated_time']:<10.2f} | {p['distance']:<10.2f}")
            print("-" * 60)

            # Выбор победителя (минимум по стоимости)
            best_proposal = min(self.agent.proposals, key=lambda p: p["cost"])

            print(f"[Shop {self.agent.shop_id}] РЕШЕНИЕ: Выбран {best_proposal['vehicle_id']}")
            print(f"[Shop {self.agent.shop_id}] ПРИЧИНА: Минимальная стоимость ({best_proposal['cost']:.2f})\n")

            # Отправка согласия
            accept_msg = Message(to=best_proposal["vehicle_jid"])
            accept_msg.set_metadata("performative", "accept-proposal")
            accept_msg.body = json.dumps({
                "type": "accept_delivery",
                "shop_id": self.agent.shop_id,
                "shop_jid": str(self.agent.jid)
            })
            await self.send(accept_msg)

            self.agent.proposals = []
            self.agent.request_sent = False
            self.agent.best_proposal_selected = True

    async def setup(self):
        print(f"[INFO] Магазин {self.shop_id} запущен в точке {self.location}")
        self.add_behaviour(self.SendRequestBehaviour())
        self.add_behaviour(self.ReceiveProposalBehaviour())