# backend/app/repositories/base.py
"""
Base Repository pattern for database operations.
Provides common CRUD operations and can be extended for specific models.
"""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.base import Base
from app.core.exceptions import DatabaseError
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Type Variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common database operations."""

    def __init__(self, model: Type[ModelType], db_session: Session):
        self.model = model
        self.db_session = db_session

    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """Get a single record by its ID. Returns None if not found."""
        try:
            return self.db_session.query(self.model).filter(self.model.id == id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting {self.model.__name__} by ID {id}: {e}")
            raise DatabaseError(operation=f"get_{self.model.__name__.lower()}_by_id", message=f"Failed to retrieve {self.model.__name__}")

    def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """Get a single record by a specific field. Returns None if not found."""
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Field {field_name} does not exist on {self.model.__name__}")
            field = getattr(self.model, field_name)
            return self.db_session.query(self.model).filter(field == value).first()
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting {self.model.__name__} by {field_name}={value}: {e}")
            raise DatabaseError(operation=f"get_{self.model.__name__.lower()}_by_{field_name}", message=f"Failed to retrieve {self.model.__name__}")

    def get_by_fields(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records by a set of field filters. Returns an empty list if none found."""
        try:
            query = self.db_session.query(self.model)
            for field_name, value in filters.items():
                if not hasattr(self.model, field_name):
                    raise ValueError(f"Field {field_name} does not exist on {self.model.__name__}")
                field = getattr(self.model, field_name)
                query = query.filter(field == value)
            return query.offset(skip).limit(limit).all()
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting {self.model.__name__} by filters {filters}: {e}")
            raise DatabaseError(operation=f"get_{self.model.__name__.lower()}_by_fields", message=f"Failed to retrieve {self.model.__name__}")

    def get_all(self, skip: int = 0, limit: int = 100, order_by: str = "id", desc: bool = False) -> List[ModelType]:
        """Get all records with optional pagination. Returns an empty list if none found."""
        try:
            query = self.db_session.query(self.model)
            if not hasattr(self.model, order_by):
                raise ValueError(f"Field {order_by} does not exist on {self.model.__name__}")
            field = getattr(self.model, order_by)
            if desc:
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field.asc())
            return query.offset(skip).limit(limit).all()
        except ValueError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting all {self.model.__name__} records: {e}")
            raise DatabaseError(operation=f"get_all_{self.model.__name__.lower()}", message=f"Failed to retrieve all {self.model.__name__} records")

    def create(self, obj: ModelType) -> ModelType:
        """Create a new record in the database."""
        try:
            self.db_session.add(obj)
            self.db_session.commit()
            self.db_session.refresh(obj)
            logger.info(f"Created new {self.model.__name__} record with ID {obj.id}")
            return obj
        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise DatabaseError(operation=f"create_{self.model.__name__.lower()}", message=f"Integrity error creating {self.model.__name__}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database error creating {self.model.__name__}: {e}")
            raise DatabaseError(operation=f"create_{self.model.__name__.lower()}", message=f"Failed to create {self.model.__name__}")

    def create_bulk(self, objs: List[ModelType]) -> List[ModelType]:
        """Create multiple records in the database."""
        try:
            self.db_session.bulk_save_objects(objs)
            self.db_session.commit()
            logger.info(f"Created {len(objs)} new {self.model.__name__} records")
            return objs
        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Integrity error creating bulk {self.model.__name__}: {e}")
            raise DatabaseError(operation=f"create_bulk_{self.model.__name__.lower()}", message=f"Integrity error creating bulk {self.model.__name__}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database error creating bulk {self.model.__name__}: {e}")
            raise DatabaseError(operation=f"create_bulk_{self.model.__name__.lower()}", message=f"Failed to create bulk {self.model.__name__}")

    def update(self, obj: ModelType, data: Dict[str, Any]) -> ModelType:
        """Update an existing record in the database."""
        try:
            for field, value in data.items():
                if hasattr(obj, field):
                    setattr(obj, field, value)
            logger.info(f"Updating {self.model.__name__} record with ID {obj.id} with data: {data}")
            self.db_session.commit()
            self.db_session.refresh(obj)
            return obj
        except IntegrityError as e:
            self.db_session.rollback()
            logger.error(f"Integrity error updating {self.model.__name__} with ID {obj.id}: {e}")
            raise DatabaseError(operation=f"update_{self.model.__name__.lower()}", message=f"Integrity error updating {self.model.__name__}")
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database error updating {self.model.__name__} with ID {obj.id}: {e}")
            raise DatabaseError(operation=f"update_{self.model.__name__.lower()}", message=f"Failed to update {self.model.__name__}")

    def update_by_id(self, id: Any, update_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update a record by its ID with the provided data. Returns the updated record or None if not found."""
        obj = self.get_by_id(id)
        if not obj:
            return None
        return self.update(obj, update_data)

    def delete(self, obj: ModelType) -> bool:
        """Delete a record from the database."""
        try:
            self.db_session.delete(obj)
            self.db_session.commit()
            logger.info(f"Deleted {self.model.__name__} record with ID {obj.id}")
            return True
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"Database error deleting {self.model.__name__} with ID {obj.id}: {e}")
            raise DatabaseError(operation=f"delete_{self.model.__name__.lower()}", message=f"Failed to delete {self.model.__name__}")

    def delete_by_id(self, id: Any) -> bool:
        """Delete a record by its ID. Returns True if deleted, False if not found."""
        obj = self.get_by_id(id)
        if not obj:
            return False
        return self.delete(obj)
