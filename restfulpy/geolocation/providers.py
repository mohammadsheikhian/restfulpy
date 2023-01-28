import traceback

import ipinfo
import redis
import requests
from nanohttp import settings

from restfulpy.constants import GEO_DEFAULT
from restfulpy.helpers import construct_class_by_name, Singleton
from restfulpy.logging_ import logger


class GeoLocation(metaclass=Singleton):
    """
    Data-Model:
        ip:{ip}:info: country:country_name,city:city_name or NA

    Redis-Command:
        get ip:{ip}:info
        set ip:{ip}:info country:country_name,city:city_name
        del ip:{ip}:info
    """

    def __init__(self):
        self.redis = redis.StrictRedis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.authentication.redis.db,
            password=settings.redis.password
        )

    @staticmethod
    def get_ip_info_key(ip):
        return f'ip:{ip}:info'

    def get_info_ip(self, ip):
        raise NotImplementedError

    def set_info_ip_redis(self, ip, info):
        """
        This method set details of ip to redis
        :param ip: str
        :param info: str(country:country_name,city:city_name) or NA
        """
        self.redis.set(self.get_ip_info_key(ip), info, ex=settings.geo_ip.ttl)

    def get_info_ip_redis(self, ip):
        """
        This method get details of ip from redis
        :param ip: str
        :returns: country:country_name,city:city_name or NA or None
        """
        info = self.redis.get(self.get_ip_info_key(ip))
        return info.decode("utf-8") if info is not None else info


class IpInfoProvider(GeoLocation):
    """
    For more details check https://ipinfo.io/
    """

    def __init__(self):
        super().__init__()
        access_token = settings.geo_ip.access_token
        ttl = settings.geo_ip.ttl
        maxsize = settings.geo_ip.maxsize
        self.handler = ipinfo.getHandler(
            access_token=access_token,
            cache_options={'ttl': ttl, 'maxsize': maxsize}
        )

    def get_info_ip(self, ip: str) -> str:
        """
        This method use ipinfo to get detail of ip
        :param ip:(string)
        :returns: string(country:country_name,city:city_name or NA)
        """
        _location = GEO_DEFAULT

        if settings.geo_ip.is_active is False or ip is None:
            return _location

        try:
            _location_redis = self.get_info_ip_redis(ip)
            if _location_redis is not None and _location_redis != GEO_DEFAULT:
                _location = _location_redis
                return _location

            details = \
                self.handler.getDetails(ip, timeout=settings.geo_ip.time_out)
            if hasattr(details, 'country_name') and hasattr(details, 'city'):
                _location = f'country:{details.country_name},' \
                    f'city:{details.city}'
                self.set_info_ip_redis(ip, _location)

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

    def get_info_ip(self, ip: str) -> str:
        """
        This method call API ipapi to get detail of ip
        :param ip:(string)
        :returns: string(country:country_name,city:city_name or NA)
        """
        _location = GEO_DEFAULT

        if settings.geo_ip.is_active is False or ip is None:
            return _location

        try:
            _location_redis = self.get_info_ip_redis(ip)
            if _location_redis is not None and _location_redis != GEO_DEFAULT:
                _location = _location_redis
                return _location

            response = requests.get(
                url=f'https://ipapi.co/{ip}/json/',
                timeout=settings.geo_ip.time_out,
            ).json()
            if hasattr(response, 'country_name') and hasattr(response, 'city'):
                _location = f'country:{response.get("country_name")},' \
                    f'city:{response.get("city")}'
                self.set_info_ip_redis(ip, _location)
            
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

