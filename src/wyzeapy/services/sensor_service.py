#  Copyright (c) 2021. Mulliken, LLC - All Rights Reserved
#  You may use, distribute and modify this code under the terms
#  of the attached license. You should have received a copy of
#  the license with this file. If not, please write to:
#  joshua@mulliken.net to receive a copy
import asyncio
import logging
from threading import Thread
from typing import List, Callable, Tuple, Optional

from wyzeapy.services.base_service import BaseService
from wyzeapy.types import Device, PropertyIDs, DeviceTypes

_LOGGER = logging.getLogger(__name__)


class Sensor(Device):
    detected: bool = False


class SensorService(BaseService):
    _updater_thread: Optional[Thread] = None
    _subscribers: List[Tuple[Sensor, Callable[[Sensor], None]]] = []

    async def update(self, sensor: Sensor) -> Sensor:
        properties = await self._get_device_info(sensor)

        for property in properties['data']['property_list']:
            pid = property['pid']
            value = property['value']

            try:
                if PropertyIDs(pid) == PropertyIDs.CONTACT_STATE:
                    sensor.detected = value == "1"
                if PropertyIDs(pid) == PropertyIDs.MOTION_STATE:
                    sensor.detected = value == "1"
            except ValueError:
                pass

        return sensor

    async def register_for_updates(self, sensor: Sensor, callback: Callable[[Sensor], None]):
        _LOGGER.debug(f"Registering sensor: {sensor.nickname} for updates")
        loop = asyncio.get_event_loop()
        if not self._updater_thread:
            self._updater_thread = Thread(target=self.update_worker, args=[loop, ], daemon=True)
            self._updater_thread.start()

        self._subscribers.append((sensor, callback))

    def update_worker(self, loop):
        while True:
            for sensor, callback in self._subscribers:
                _LOGGER.debug(f"Providing update for {sensor.nickname}")
                callback(asyncio.run_coroutine_threadsafe(self.update(sensor), loop).result())

    async def get_sensors(self) -> List[Sensor]:
        if self._devices is None:
            self._devices = await self._get_object_list()

        sensors = [Sensor(device.raw_dict) for device in self._devices if
                   device.type is DeviceTypes.MOTION_SENSOR or
                   device.type is DeviceTypes.CONTACT_SENSOR]
        return [Sensor(sensor.raw_dict) for sensor in sensors]
