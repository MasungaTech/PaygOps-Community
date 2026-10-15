import math
from pony import orm


class CSVPageProcessorService:

    @classmethod
    def process_by_page(cls, input_data, processing_function, writer, page_size=1000, data_limit=None):
        if data_limit:
            number_of_data = data_limit if data_limit < input_data.count() else input_data.count()
        else:
            number_of_data = input_data.count()

        number_of_pages = math.ceil(number_of_data / page_size)

        total_size = 0
        for page_n in range(0, number_of_pages):
            total_size += page_size
            if data_limit and total_size > data_limit:
                print('SKIPPED because above size limit - Page: ' + str(page_number) + ' out of ' + str(number_of_pages))
            else:
                page_number = page_n + 1
                print('Page: ' + str(page_number) + ' out of ' + str(number_of_pages))
                if data_limit:
                    page_data = input_data[page_size * (page_number - 1):page_size * page_number]
                else:
                    page_data = input_data.page(page_number, page_size)
                processing_function(page_data, writer)
            orm.rollback() # This is critical to free memory
