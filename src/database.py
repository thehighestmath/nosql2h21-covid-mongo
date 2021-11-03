from datetime import datetime
from typing import List

from pymongo import MongoClient


class DataBase:
    def __init__(self):
        self.__client = MongoClient('localhost', 27017)
        self.__db = self.__client.covid
        self.__cases = self.__db.cases
        self.__vaccinations = self.__db.vaccinations
        self.__countries = self.__db.countries

    @staticmethod
    def __get_first_stage_of_aggregate(
            countries: List[str] = None,
            left_bound: datetime = None,
            right_bound: datetime = None
    ):
        date_bounds = {}
        if left_bound:
            date_bounds['$gte'] = left_bound
        if right_bound:
            date_bounds['$lte'] = right_bound
        dates = {}
        if date_bounds:
            dates['date'] = date_bounds

        countries_query = {}
        if countries:
            countries_query['iso_code'] = {
                '$in': countries
            }

        return {
            '$match': {
                **countries_query,
                **dates
            }
        }

    def get_number_of_new_cases(
            self,
            countries: List[str] = None,
            left_bound: datetime = None,
            right_bound: datetime = None
    ):
        """
        минимальное/среднее/максимальное количество новых заболевших
        в сутки за весь/заданный период пандемии
        :param countries:
        :param left_bound:
        :param right_bound:
        :return:
        """
        first_stage = self.__get_first_stage_of_aggregate(countries, left_bound, right_bound)
        return list(self.__cases.aggregate([
            first_stage, {
                '$group': {
                    '_id': '$iso_code',
                    'max_disease_new_cases': {
                        '$max': 'new_cases'
                    },
                    'min_disease_new_cases': {
                        '$min': 'new_cases'
                    },
                    'avg_disease_new_cases': {
                        '$avg': 'new_cases'
                    }
                }
            }, {
                '$project': {
                    'iso_code': '$_id',
                    'max_disease_new_cases': '$max_disease_new_cases',
                    'min_disease_new_cases': '$min_disease_new_cases',
                    'avg_disease_new_cases': '$avg_disease_new_cases',
                    '_id': 0
                }
            }
        ]))

    def get_max_number_of_new_vaccinated(
            self,
            countries: List[str] = None,
            left_bound: datetime = None,
            right_bound: datetime = None
    ):
        """
        максимальное количество новых вакцинированных
        в сутки за весь/заданный период вакцинации
        :param countries:
        :param left_bound:
        :param right_bound:
        :return:
        """
        first_stage = self.__get_first_stage_of_aggregate(countries, left_bound, right_bound)
        return list(
            self.__vaccinations.aggregate([
                first_stage, {
                    '$group': {
                        '_id': '$iso_code',
                        'max_new_vaccinations': {
                            '$max': 'new_vaccinations'
                        }
                    }
                }, {
                    '$project': {
                        'iso_code': '$_id',
                        'max_new_vaccinations': '$max_new_vaccinations',
                        '_id': 0
                    }
                }
            ])
        )

    def get_total_number_of_cases(
            self,
            countries: List[str] = None,
            left_bound: datetime = None,
            right_bound: datetime = None
    ):
        """
        общее количество заболевших по миру/стране
        за весь/заданный период пандемии
        :param countries:
        :param left_bound:
        :param right_bound:
        :return:
        """
        first_stage = self.__get_first_stage_of_aggregate(countries, left_bound, right_bound)
        return list(self.__cases.aggregate([
            first_stage, {
                '$group': {
                    '_id': '$iso_code',
                    'total_cases': {
                        '$sum': 'new_cases'
                    }
                }
            }, {
                '$project': {
                    'iso_code': '$_id',
                    'total_cases': '$total_cases',
                    '_id': 0
                }
            }
        ]))

    def get_diagrams_of_total_number_of_new_cases(
            self,
            countries: List[str] = None,
            left_bound: datetime = None,
            right_bound: datetime = None
    ):
        """
        диаграммы общего количества новых заболевших
        в сутки за определённый период пандемии
        :param countries:
        :param left_bound:
        :param right_bound:
        :return:
        """
        first_stage = self.__get_first_stage_of_aggregate(countries, left_bound, right_bound)
        return list(self.__cases.aggregate([
            first_stage, {
                '$group': {
                    '_id': '$date',
                    'sum_disease_new_cases': {
                        '$sum': '$new_cases'
                    }
                }
            }, {
                '$project': {
                    'date': '$_id',
                    'sum_disease_new_cases': '$sum_disease_new_cases',
                    '_id': 0
                }
            }
        ]))

    def get_graph_of_dependence_of_cases(
            self,
            left_bound: datetime = None,
            right_bound: datetime = None
    ):
        """
        график зависимости заболевших в стране от плотности населения
        :param left_bound:
        :param right_bound:
        :return:
        """
        first_stage = self.__get_first_stage_of_aggregate(left_bound=left_bound, right_bound=right_bound)
        return list(self.__cases.aggregate([
            first_stage, {
                '$group': {
                    '_id': '$iso_code',
                    'total_cases': {
                        '$sum': '$new_cases'
                    }
                }
            }, {
                '$project': {
                    'iso_code': '$_id',
                    'total_cases': '$total_cases',
                    '_id': 0
                }
            }, {
                '$lookup': {
                    'from': 'countries',
                    'localField': 'iso_code',
                    'foreignField': 'iso_code',
                    'as': 'countries'
                }
            }, {
                '$project': {
                    'iso_code': '$iso_code',
                    'total_cases': '$total_cases',
                    'country': {
                        '$arrayElemAt': [
                            '$countries', 0
                        ]
                    }
                }
            }, {
                '$project': {
                    'iso_code': '$iso_code',
                    'total_cases': '$total_cases',
                    'population_density': '$country.population_density'
                }
            }
        ]))

    def __clear_db(self):
        self.__cases.drop()
        self.__countries.drop()
        self.__vaccinations.drop()

    def __add_countries(self, countries):
        return self.__countries.insert_many(countries)

    def parse_data(self):
        if __name__ != '__main__':
            raise Exception("Do not call this function outside database.py")

        self.__clear_db()
        import json
        with open('../owid-covid-data.json') as fp:
            data = json.load(fp)
        countries = []
        for iso_code, value in data.items():
            countries.append(dict(
                iso_code=iso_code,
                continent=value.get('continent', None),
                location=value.get('location', None),
                population=value.get('population', None),
                population_density=value.get('population_density', None),
                median_age=value.get('median_age', None),
                aged_65_older=value.get('aged_65_older', None),
                aged_70_older=value.get('aged_70_older', None),
            ))
        self.__add_countries(countries)


def main():
    db = DataBase()
    db.parse_data()


if __name__ == '__main__':
    main()
