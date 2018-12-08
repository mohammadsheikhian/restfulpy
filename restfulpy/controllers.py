from nanohttp import Controller, context, json, RestController, \
    JsonPatchControllerMixin

from restfulpy.orm import DBSession


class RootController(Controller):

    def __call__(self, *remaining_paths):

        if context.method == 'options':
            context.response_encoding = 'utf-8'
            context.response_headers.add_header(
                'Cache-Control',
                'no-cache,no-store'
            )
            return b''

        return super().__call__(*remaining_paths)


class ModelRestController(RestController):
    __model__ = None

    @json
    def metadata(self):
        return self.__model__.json_metadata()


class JsonPatchDBAwareControllerMixin(JsonPatchControllerMixin):

    @json
    def patch(self: Controller):
        try:
            results = super().patch()
            DBSession.commit()
            results = [r.to_dict() if hasattr(r, 'to_dict') else r \
                      for r in results]
            return results

        except:
            if DBSession.is_active:
                DBSession.rollback()
            raise

        finally:
            del context.jsonpatch

