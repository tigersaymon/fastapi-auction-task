from typing import Annotated

from fastapi import Depends

from src.core.interfaces import AbstractUnitOfWork, SQLAlchemyUnitOfWork


def get_uow() -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork()


UnitOfWorkDep = Annotated[AbstractUnitOfWork, Depends(get_uow)]
