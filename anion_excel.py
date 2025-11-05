from openpyxl.workbook import Workbook
from openpyxl import load_workbook
from models import Product

class AnionTable:
    def __init__(self, filename='book', max_per_file=2000):
        self.__headers = [
            "Раздел1", "Раздел2", "Раздел3", "Название с сайта", "Картинка анонса (ссылка)",
            "Картинка детальная", "Год выпуска", "Упаковка", "Цена 1", "Цены от колва",
            "Цена 3", "Цена 4", "Цена 5", "коэффициент", "ОПИСАНИЕ (Html)",
            "технические условия", "корпус", "маркировка", "масса", "Габариты", "Исполнение",
            "Изготовитель", "номер по каталогу производителя", "Этикетки", "параметры/описание",
            "Характеристика 1", "Характеристика 2", "Характеристика 3",
            "Характеристика 4", "Характеристика 5", "Характеристика 6", "Характеристика 7"
        ]

        self.__filename = filename
        self.__max_per_file = max_per_file
        self.__file_index = 1
        self.__row_count = 0

        self.__create_new_workbook()

    def __create_new_workbook(self):
        self.__wb = Workbook()
        self.__ws = self.__wb.active
        self.__ws.append(self.__headers)
        self.__row_count = 0

    def __save_current_workbook(self):
        part_filename = f"{self.__filename}_part{self.__file_index}.xlsx"
        self.__wb.save(part_filename)
        print(f"Сохранён файл: {part_filename}")

    def write_new_row(self, pr: Product):
        # если лимит достигнут — сохраняем и начинаем новый файл
        if self.__row_count >= self.__max_per_file:
            self.__save_current_workbook()
            self.__file_index += 1
            self.__create_new_workbook()

        chapters = pr.chapters + [None] * (3 - len(pr.chapters))
        self.__ws.append([
            *chapters[:3], pr.name,
            pr.small_img_url, pr.img_url,
            pr.release_year, pr.piece_per_pkg,
            None, '\n'.join(pr.prices_per_piece),
            None, None, None,
            pr.coefficient, '\n'.join(pr.description),
            pr.tech_conditions, pr.case, pr.marking,
            pr.weight, pr.dimensions, pr.execution,
            pr.producer, pr.pr_id, ';'.join(pr.labels),
            ';'.join(pr.documents), *pr.features
        ])

        self.__row_count += 1

    def close(self):
        # сохраняем последний файл, если есть несохранённые данные
        if self.__row_count > 0:
            self.__save_current_workbook()