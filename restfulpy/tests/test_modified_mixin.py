from sqlalchemy import Unicode, Integer

from restfulpy.orm import DeclarativeBase, Field, ModifiedMixin


class ModificationCheckingModel(ModifiedMixin, DeclarativeBase):
    __tablename__ = 'modification_checking_model'
    __exclude__ = {'age'}

    title = Field(Unicode(50), primary_key=True)
    age = Field(Integer)


def test_modified_mixin(db):
    session = db()

    instance = ModificationCheckingModel(
        title='test title',
        age=1,
    )

    session.add(instance)
    session.commit()

    assert instance.modified_at is None
    assert instance.created_at is not None
    assert instance.last_modification_time == instance.created_at

    instance = session.query(ModificationCheckingModel).one()
    assert instance.modified_at is None
    assert instance.created_at is not None
    assert instance.last_modification_time == instance.created_at

    instance.age = 2
    session.commit()
    assert instance.modified_at is None
    assert instance.created_at is not None
    assert instance.last_modification_time == instance.created_at

    instance.title = 'Edited title'
    session.commit()
    assert instance.modified_at is not None
    assert instance.created_at is not None
    assert instance.last_modification_time == instance.modified_at

    instance = session.query(ModificationCheckingModel).one()
    assert instance.modified_at is not None
    assert instance.created_at is not None
    assert instance.last_modification_time == instance.modified_at

