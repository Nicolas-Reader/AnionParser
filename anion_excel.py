from wheel.macosx_libfile import swap32

from models import Product

from openpyxl import load_workbook


class AnionTable:
    def __init__(self, filename = 'Book 3.xlsx'):
        self.__filename = filename

        self.__wb = load_workbook(self.__filename)
        self.__ws = self.__wb.active

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