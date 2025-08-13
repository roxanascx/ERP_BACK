from typing import List, Optional
from datetime import datetime
from ..models.user import UserModel, UserCreate, UserUpdate, UserResponse
from bson import ObjectId
import motor.motor_asyncio
import os

class UserService:
    def __init__(self):
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url)
        self.db = self.client.erp_database
        self.collection = self.db.users

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Crear un nuevo usuario"""
        # Verificar si el usuario ya existe por clerk_id
        existing_user = await self.collection.find_one({"clerk_id": user_data.clerk_id})
        if existing_user:
            return self._format_user_response(existing_user)

        # Crear nuevo usuario
        user_dict = user_data.dict()
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()
        user_dict["is_active"] = True

        result = await self.collection.insert_one(user_dict)
        
        # Obtener el usuario creado
        created_user = await self.collection.find_one({"_id": result.inserted_id})
        return self._format_user_response(created_user)

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[UserResponse]:
        """Obtener usuario por Clerk ID"""
        user = await self.collection.find_one({"clerk_id": clerk_id})
        return self._format_user_response(user) if user else None

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Obtener usuario por email"""
        user = await self.collection.find_one({"email": email})
        return self._format_user_response(user) if user else None

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """Obtener todos los usuarios"""
        cursor = self.collection.find().skip(skip).limit(limit)
        users = await cursor.to_list(length=limit)
        return [self._format_user_response(user) for user in users]

    async def update_user(self, clerk_id: str, user_update: UserUpdate) -> Optional[UserResponse]:
        """Actualizar usuario"""
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        update_data["updated_at"] = datetime.utcnow()

        result = await self.collection.update_one(
            {"clerk_id": clerk_id},
            {"$set": update_data}
        )

        if result.matched_count:
            updated_user = await self.collection.find_one({"clerk_id": clerk_id})
            return self._format_user_response(updated_user)
        return None

    async def delete_user(self, clerk_id: str) -> bool:
        """Eliminar usuario (soft delete)"""
        result = await self.collection.update_one(
            {"clerk_id": clerk_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.matched_count > 0

    async def update_last_sign_in(self, clerk_id: str) -> bool:
        """Actualizar último inicio de sesión"""
        result = await self.collection.update_one(
            {"clerk_id": clerk_id},
            {"$set": {"last_sign_in_at": datetime.utcnow(), "updated_at": datetime.utcnow()}}
        )
        return result.matched_count > 0

    def _format_user_response(self, user_doc) -> UserResponse:
        """Formatear documento de MongoDB a UserResponse"""
        if not user_doc:
            return None
            
        return UserResponse(
            id=str(user_doc["_id"]),
            clerk_id=user_doc["clerk_id"],
            email=user_doc["email"],
            username=user_doc.get("username"),
            first_name=user_doc.get("first_name"),
            last_name=user_doc.get("last_name"),
            profile_image_url=user_doc.get("profile_image_url"),
            is_active=user_doc.get("is_active", True),
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
            last_sign_in_at=user_doc.get("last_sign_in_at")
        )
