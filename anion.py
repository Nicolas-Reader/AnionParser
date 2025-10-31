import asyncio
from datetime import datetime
from math import ceil

from httpx import AsyncClient, Timeout, ReadTimeout

from bs4 import BeautifulSoup

from fake_headers import Headers
from fake_useragent import UserAgent

from anion_excel import AnionTable
from models import Product


lock = asyncio.Lock()

with open('proxies.txt') as proxies_file:
    PROXIES = proxies_file.read().split('\n')


def chunked(lst, size):
    return [lst[i:i + size] for i in range(0, len(lst), size)]


class AnionParser:
    def __init__(self):
        self.__base_url = 'https://www.anion.ru/'
        timeout = Timeout(10.0, connect=5.0)

        # self.__client = AsyncClient(headers=headers, timeout=timeout)

    @staticmethod
    def gen_headers():
        return Headers().generate() | {'User-agent': UserAgent().random}

    async def get_all_categories_url(self):
        async with AsyncClient(headers=self.gen_headers()) as client:
            resp = await client.get(self.__base_url)

            soup = BeautifulSoup(resp.content, 'html.parser')

        categories_url = []

        catalog_menu = soup\
            .find('div', class_='row block__content')\
            .find_next('ul')\
            .find_all('li', recursive=False)

        for submenu in catalog_menu:
            categories_url.append(submenu.find_next('a').get('href'))

        return categories_url


    async def get_category_product_urls(self, category_url):
        async with AsyncClient(headers=self.gen_headers()) as client:
            resp = await client.get(self.__base_url + category_url,
                                           params={
                                               'limit': 1,
                                           })
            soup = BeautifulSoup(resp.content, 'html.parser')

        products_count = int(
            soup\
                .find_all('a', class_='page-link')[-1].text
        )

        print(f"[I] В категории {category_url} обнаружено {products_count} товаров")
        product_urls = []
        page_count = ceil(products_count / 100)
        # print(f'Общее количество эл-ов: {products_count}\nКоличество страниц в группе: ', ceil(products_count / 100))
        for page_num in range(page_count):
            page_param = {'page': page_num + 1} if page_num + 1 > 1 else {}
            async with AsyncClient(headers=self.gen_headers()) as client:
                try:
                    resp = await client.get(self.__base_url + category_url,
                                                   params={
                                                       'limit': 100,
                                                       **page_param
                                                   })
                except ReadTimeout:
                    print(f'[E] Превышено время ожидания при парсинге страницы {page_num}')
                    continue

            soup = BeautifulSoup(resp.content, 'html.parser')

            product_names = soup.find_all('p', class_='name')
            if page_num + 1 < page_count and len(product_names) < 100:
                print(f'[E] Произошла ошибка при парсинге страницы {page_num}, найдено {len(product_names)} товаров')

            pr_bar = round(page_num * 100 / page_count / 10)
            print(f"[{'#' * pr_bar * 2}{' ' * (10 - pr_bar) * 2}] {page_num}/{page_count}", end='\r')
            for i, product_name in enumerate(product_names):
                product_urls.append(product_name.find_next('a').get('href'))
            #     print(f'Распаршенно {i+1}/100 элементов на странице {page_num}\nОбщее количество эл-ов: {len(product_urls)}')
        print()

        return product_urls



    async def get_product(self, product_url, proxy):
        async with AsyncClient(headers=self.gen_headers(), proxy=proxy, http2=False) as client:
            try:
                resp = await client.get(self.__base_url + product_url)
            except ReadTimeout:
                print(f'[E] Ошибка(ReadTimeout) при чтении страницы {self.__base_url + product_url}')
                return

        soup = BeautifulSoup(resp.content, 'html.parser')

        chapters = soup.find('p', class_='crumbs').get_text(strip=True).split('/')[2:-1]

        name = soup.find('h1', class_='name_').text
        product_id = soup.find('p', class_='code').text.split(': ')[-1].replace('\t', '')

        img_text = soup.find('p', class_='tip').text
        small_img_url = self.__base_url + soup.select_one(".mini-slider img")['src'] \
            if 'нет фото' not in img_text else None

        img_url = self.__base_url + soup.select_one(".image-slider-wrapper img")['src'] \
            if 'нет фото' not in img_text else None

        info_table = soup.find('table', class_='info-table').find_all('tr')

        release_year = None
        piece_per_pkg = None
        execution = None
        producer = None
        dimensions = None
        for row in (info_table or []):
            row_text = row.get_text(strip=True).lower()
            row_data = row_text.split(':')[-1]
            # print(row_text)
            for i in [' ', '.']:
                row_data = row_data.replace(i, '')

            if 'год' in row_text:
                release_year = row_data
            elif 'упаковка' in row_text:
                piece_per_pkg = row_data
            elif 'исполнение' in row_text:
                execution = row_data
            elif 'изготовитель' in row_text:
                producer = row_data
            elif 'габаритные' in row_text:
                dimensions = row_data

        price_els = soup.find_all('div', class_='price-item')
        prices_per_piece = []
        coefficient = None
        if price_els:
            prices = [price_el.text.replace(' ', '').replace('р.', '') for price_el in price_els]

            for i, price in enumerate(prices[:-1]):
                if not price.split(':')[0].isdigit():
                    continue

                price_lower_limit = price.split(':')[0]
                price_high_limit = (int(prices[i+1].split(':')[0]) - 1) \
                    if prices[i+1].split(':')[0].isdigit() else ''

                price = price.split(':')[-1]

                prices_per_piece.append(f"{price_lower_limit}:{price_high_limit}:{price}:RUB;")
            else:
                if not prices[-1].split(':')[0].isdigit():
                    coefficient = ('для кол-в кратных ' +
                                   prices[-1].split(':')[0].replace('длякол-вкратных', '').split('.')[0] +
                                   ' - ' + prices[-1].split(':')[-1])
                else:
                    prices_per_piece.append(f"{prices[-1].split(':')[0]}::{prices[-1].split(':')[-1]}:RUB;")

        desc = []
        desc_header = soup.find('h3', string='ОПИСАНИЕ')

        desc_params = {'tech_conditions': None, 'case': None, 'marking': None, 'weight': None}
        if desc_header:
            if desc_header.find_all_next()[0].name == 'p':
                desc.append(desc_header.find_all_next()[0].get_text(strip=True))
            desc_menu = [desc_params.find_all('li') for desc_params in desc_header.find_all_next('ul')[:2]]
            desc_menu = [item for sublist in desc_menu for item in sublist]

            desc_alias = {'технические условия': 'tech_conditions', 'масса': 'weight',
                          'маркировка': 'marking', 'корпус': 'case'}
            for desc_item in desc_menu:
                if '-' not in desc_item.text:
                    continue

                desc.append(desc_item.text)
                param_name, param_value = desc_item.get_text(strip=True).split(' - ', 1)
                if param_name in desc_alias:
                    desc_params[desc_alias[param_name]] = param_value

        features = []
        table = soup.find('table', class_='table')
        if table:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if cols[1].text.replace(' ', ''):
                    features.append(f"{cols[0].text} - {cols[1].text}")

        documents = []
        labels = []
        add_info_tables = soup.find('div', class_='downloads').find_all('div', class_='col-sm-5') or []

        for info_table in add_info_tables:
            header_text = info_table.find('h3').text.lower()
            all_links = [self.__base_url + link_el.get('href') for link_el in info_table.find_all('a') if link_el.get('href') != 'https://www.anion.ru/#collapseLABELS']

            if 'этикетка' in header_text:
                labels = all_links
            elif 'параметры' in header_text:
                documents = all_links

        return Product(
            chapters, name, small_img_url,
            img_url, release_year, piece_per_pkg,
            prices_per_piece, desc, **desc_params,
            producer=producer, features=features, pr_id=product_id,
            execution=execution, labels=labels, documents=documents,
            dimensions=dimensions, coefficient=coefficient
        )


async def get_and_write(aparser, atable, pr_url, proxy):
    try:
        pr = await aparser.get_product(pr_url, proxy)
    except Exception as e:
        print(f"[E] Ошибка({e}) при прасинге товара {pr_url}")
        pr = 0
    async with lock:
        if pr:
            atable.write_new_row(pr)


async def main():
    anion_parser = AnionParser()
    categories_urls = await anion_parser.get_all_categories_url()

    CHUNK_SIZE = 5

    for category_url in categories_urls[2:5]:
        products_url = await anion_parser.get_category_product_urls(category_url)

        anion_table = AnionTable(f"book_{category_url.split('/')[-1]}.xlsx")
        print('[D] Парсинг товаров начался')
        chunks = chunked(products_url, CHUNK_SIZE)
        for i, chunk_products in enumerate(chunks):
            time_start = datetime.now()
            tasks = [get_and_write(anion_parser, anion_table, pr_url, proxy) for pr_url, proxy in zip(chunk_products, PROXIES)]
            await asyncio.gather(*tasks)

            elapsed = (datetime.now() - time_start).total_seconds()
            ch_per_s = 1 / elapsed
            remaining = len(chunks) - (i + 1)
            time_left = remaining / ch_per_s

            pr_bar = round((i+1) * 20 / len(chunks))

            print(f"[{'#' * pr_bar}{' ' * (10 - pr_bar)}] {ch_per_s:.2f} ch/s {i+1}/{len(chunks)} ch. time left {time_left / 60:.2f} m", end='\r')
        print()

        anion_table.close()


if __name__ == '__main__':
    asyncio.run(main())