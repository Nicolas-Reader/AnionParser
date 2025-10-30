from openpyxl.workbook import Workbook
from wheel.macosx_libfile import swap32

from models import Product

from openpyxl import load_workbook


class AnionTable:
    def __init__(self, filename = 'book'):
        headers = ["Раздел1", "Раздел2", "Раздел3", "Название с сайта", "Картинка анонса (ссылка)", "Картинка детальная", "Год выпуска", "Упаковка", "Цена 1", "Цены от колва", "Цена 3", "Цена 4", "Цена 5", "коэффициент", "ОПИСАНИЕ (Html)", "технические условия", "корпус", "маркировка", "масса", "Габариты", "Исполнение", "Изготовитель", "номер по каталогу производителя", "Этикетки", "параметры/описание", "Характеристика 1", "Характеристика 2", "Характеристика 3", "Характеристика 4", "Характеристика 5", "Характеристика 6", "Характеристика 7"]

        self.__filename = filename

        self.__wb = Workbook()
        self.__ws = self.__wb.active

        self.__ws.append(headers)

    def write_new_row(self, pr: Product):
        chapters = pr.chapters + [None] * (3 - len(pr.chapters))
        # коофицент после цен
        self.__ws.append(
            [*chapters[:3], pr.name,
             pr.small_img_url, pr.img_url,
             pr.release_year, pr.piece_per_pkg,
             None, '\n'.join(pr.prices_per_piece),
             None, None, None,
             pr.coefficient, '\n'.join(pr.description), pr.tech_conditions,
             pr.case, pr.marking,
             pr.weight, pr.dimensions, pr.execution,
             pr.producer, pr.pr_id, ';'.join(pr.labels),
             ';'.join(pr.documents), *pr.features])


    def close(self):
        self.__wb.save(self.__filename)
# def main():
#     a = AnionTable()
#     print('dfsdfsfds')
#     del a
#
# if __name__ == '__main__':
#     main()
#     print('ffsdgsfdgfs')
#     # del a