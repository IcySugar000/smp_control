from loguru import logger
from mcrcon import MCRcon
from time import sleep
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
from random import randint
import toml


class StageType(Enum):
    SHRINK = "SHRINK"
    PEACE = "PEACE"


class RoutineItem(BaseModel):
    time_start: datetime
    time_end: datetime
    stage_type: StageType
    range_start: int
    range_end: int


def load_routine_from_config(config_path: str) -> list[RoutineItem]:
    try:
        with open(config_path, "r") as file:
            config = toml.load(file)
            routine_items = []
            for item in config["routine"]["items"]:
                routine_items.append(
                    RoutineItem(
                        time_start=datetime.fromisoformat(item["time_start"]),
                        time_end=datetime.fromisoformat(item["time_end"]),
                        stage_type=StageType[item["stage_type"]],
                        range_start=item["range_start"],
                        range_end=item["range_end"],
                    )
                )
            return routine_items
    except Exception as e:
        logger.error(f"Failed to load routine from config: {e}")
        return []


# Replace the hardcoded ROUTINE with the loaded configuration
ROUTINE = load_routine_from_config("routine_config.toml")


class Border(BaseModel):
    x: int
    y: int
    r: int

    def __init__(self, x, y, r):
        super().__init__(x=x, y=y, r=r)


def move_border(border: Border):
    logger.info(
        f"Moving border to position: ({border.x}, {border.y}) with radius: {border.r}"
    )
    try:
        with MCRcon("localhost", "your_rcon_password") as mcr:
            mcr.command(f"worldborder center {border.x} {border.y}")
            mcr.command(f"worldborder set {border.r}")
    except Exception as e:
        logger.error(f"Failed to move border: {e}")


def calculate_border(
    border_start: Border, border_end: Border, total_diff: int, now_diff: int
) -> Border:
    x = int(border_start.x + (border_end.x - border_start.x) * (now_diff / total_diff))
    y = int(border_start.y + (border_end.y - border_start.y) * (now_diff / total_diff))
    r = int(border_start.r + (border_end.r - border_start.r) * (now_diff / total_diff))
    return Border(x=x, y=y, r=r)


class Stage:
    def __init__(
        self,
        time_start: datetime,
        time_end: datetime,
        stage_type: StageType,
        border_start: Border,
        border_end: Border,
    ):
        self.time_start = time_start
        self.time_end = time_end
        self.stage_type = stage_type
        self.border_start = border_start
        self.border_end = border_end

    def work(self):
        match self.stage_type:
            case StageType.SHRINK:
                self.shrink()
            case StageType.PEACE:
                self.peace()

    def shrink(self):
        logger.info("Executing SHRINK stage...")
        total_diff = int((self.time_end - self.time_start).total_seconds())
        now_diff = int((datetime.now() - self.time_start).total_seconds())
        new_border = calculate_border(
            self.border_start, self.border_end, total_diff, now_diff
        )
        move_border(new_border)

    def peace(self):
        logger.info("Executing PEACE stage...")


def main():
    border_start = Border(0, 0, 10000)
    border_end = Border(0, 0, 10000)
    for item in ROUTINE:
        # wait until the start time of the item, might happen at the first item
        while True:
            if datetime.now() < item.time_start:
                sleep(1)
            else:
                break

        logger.info(f"Starting routine item: {item}")

        # adjusting new border infomation
        border_start = border_end
        if item.stage_type == StageType.SHRINK:
            border_start.r = item.range_start
            border_end = Border(
                x=randint(
                    border_start.x - item.range_start + item.range_end,
                    border_start.x + item.range_start - item.range_end,
                ),
                y=randint(
                    border_start.y - item.range_start + item.range_end,
                    border_start.y + item.range_start - item.range_end,
                ),
                r=item.range_end,
            )
            logger.info(
                f"New border set to: ({border_end.x}, {border_end.y}) with radius: {border_end.r}"
            )
        else:
            border_end = border_start

        stage = Stage(
            time_start=item.time_start,
            time_end=item.time_end,
            stage_type=item.stage_type,
            border_start=border_start,
            border_end=border_end,
        )

        # loop and work
        while datetime.now() < item.time_end:
            stage.work()
            sleep(1)


if __name__ == "__main__":
    main()
