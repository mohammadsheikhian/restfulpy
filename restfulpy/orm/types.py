import ujson
from sqlalchemy import Unicode, TypeDecorator


class FakeJSON(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, engine):
        return ujson.dumps(value, reject_bytes=False)

    def process_result_value(self, value, engine):
        if value is None:
            return None

        return ujson.loads(value)
