import traceback

import ipinfo
import requests
from nanohttp import settings

from restfulpy.constants import GEO_DEFAULT
from restfulpy.mule import logger
from restfulpy.helpers import construct_class_by_name, Singleton


class GeoLocation(metaclass=Singleton):

    @staticmethod
    def get_info_ip(ip):
        raise NotImplementedError


class IpInfoProvider(GeoLocation):
    """
    For more details check https://ipinfo.io/
    """

    @staticmethod
    def get_info_ip(ip: str) -> str:
        """
        This method use ipinfo to get detail of ip
        :param ip:(string)
        :returns: string(country:country_name,city:city_name or NA)
        """
        _location = GEO_DEFAULT
        if settings.geo_ip.is_active is False or ip is None:
            return _location

        try:
            access_token = settings.geo_ip.access_token
            handler = ipinfo.getHandler(access_token=access_token)
            details = handler.getDetails(ip)
            if hasattr(details, 'country_name') and hasattr(details, 'city'):
                _location = f'country:{details.country_name},' \
                    f'city:{details.city}'

        except Exception as ex:
            exception = {
                'Traceback': traceback.format_exc(),
                'Message Exception': ex,
                'Message Exception document': ex.__doc__,
            }
            logger.error(exception)

        finally:
            return _location


class IpApiProvider(GeoLocation):
    """
    For more details check https://ipapi.co/api/
    """

    @staticmethod
    def get_info_ip(ip: str) -> str:
        """
        This method call API ipapi to get detail of ip
        :param ip:(string)
        :returns: string(country:country_name,city:city_name or NA)
        """
        _location = GEO_DEFAULT
        if settings.geo_ip.is_active is False or ip is None:
            return _location

        try:
            response = requests.get(f'https://ipapi.co/{ip}/json/').json()
            if hasattr(response, 'country_name') and hasattr(response, 'city'):
                _location = f'country:{response.get("country_name")},' \
                    f'city:{response.get("city")}'

        except Exception as ex:
            exception = {
                'Traceback': traceback.format_exc(),
                'Message Exception': ex,
                'Message Exception document': ex.__doc__,
            }
            logger.error(exception)

        finally:
            return _location


def getter_geolocation() -> GeoLocation:
    return construct_class_by_name(settings.geo_ip.default_getter)

