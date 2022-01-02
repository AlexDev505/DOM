"""

Интерфейс запуска приложения.

"""

from __future__ import annotations

import os
import time
import typing as ty

import pygame as pg
import socketio.exceptions  # noqa
from loguru import logger

from base import Thread, Label, Group, Text, Anchor
from utils import FinishStatus

if ty.TYPE_CHECKING:
    from network import NetworkClient


class StartAppScreen(Group):
    SIZE = (300, 350)

    def __init__(self, network_client: NetworkClient):
        logger.trace("Инициализация окна загрузки клиента")

        super(StartAppScreen, self).__init__()

        self.network_client = network_client

        # Создаем окно без стандартной рамки
        self.screen = pg.display.set_mode(self.SIZE, pg.NOFRAME)
        pg.display.set_caption("DOM")

        self.label = Label(
            self,
            x=lambda lb: self.SIZE[0] / 2 - lb.rect.w / 2,
            y=lambda lb: self.SIZE[1] / 2 - lb.rect.h,
            text="DOM",
            padding=6,
            color=pg.Color("red"),
            font=pg.font.Font(None, 60),
            border_color=pg.Color("red"),
            border_width=2,
        )

        self.status = Text(
            self,
            x=lambda lb: self.SIZE[0] / 2 - lb.rect.w / 2,
            y=self.label.rect.bottom + 20,
            width=self.SIZE[0] - 40,
            text="Запуск клиента",
            color=pg.Color("red"),
            font=pg.font.Font(None, 30),
            anchor=Anchor.center,
            soft_split=True,
        )

        self.running = True
        self.finish_status: str = FinishStatus.close

    def exec(self) -> str:
        """
        Запускает основной цикл окна.
        :return: FinishStatus.
        """
        # Запуск отдельного потока, для запуска приложения.
        logger.debug("Запуск окна загрузки клиента")
        Thread(self.worker).run()

        while self.running:  # Цикл окна
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.terminate()
            self.render()
        return self.finish_status

    def worker(self) -> None:
        """
        Процесс запуска приложения.
        TODO:
            Проверяет целостность файлов.
            Проверяет наличие обновления клиента.
        """
        logger.debug("Загрузка клиента")
        while not self.network_client.sio.connected:
            try:
                self.status.text = "Подключение к серверу"
                self.network_client.init()
                logger.info("Соединение с сервером установлено")
            except socketio.exceptions.ConnectionError as err:
                logger.error(f"{type(err).__name__}: {str(err)}")
                if "[Errno 11001]" in str(err):
                    self.status.text = "Проверьте подключение к интернету"
                else:
                    self.status.text = "Сервер недоступен\nПопробуйте позже"
                time.sleep(5)

        self.finish_status = FinishStatus.auth_failed
        if os.path.isfile(os.environ["AUTH_PATH"]):
            with open(os.environ["AUTH_PATH"], encoding="utf-8") as file:
                data = file.readlines()
            if len(data) == 2:
                self.status.text = "Авторизация"
                login, password = map(str.strip, data)
                self.network_client.login(
                    login,
                    password,
                    lambda: (
                        self.__setattr__("finish_status", FinishStatus.ok),
                        self.terminate(),
                    ),
                    lambda msg: (
                        FinishStatus.set_msg(msg),
                        self.terminate(),
                    ),
                )
            else:
                self.terminate()
                logger.warning("Файл .auth поврежден")
        else:
            logger.info("Файл .auth не найден")
            self.terminate()

    def render(self) -> None:
        """
        Отображает интерфейс.
        """
        self.screen.fill("black")
        self.draw(self.screen)
        pg.display.flip()

    def terminate(self) -> None:
        """
        Останавливает приложения.
        """
        logger.debug("Остановка окна загрузки клиента")
        self.running = False