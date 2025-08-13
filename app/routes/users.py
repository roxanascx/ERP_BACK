from fastapi import APIRouter, HTTPException, Header, Request
from typing import List, Optional
import json
import hmac
import hashlib
from ..services.user_service import UserService
from ..models.user import UserCreate, UserUpdate, UserResponse

router = APIRouter()
user_service = UserService()

# Webhook de Clerk para sincronizar usuarios
@router.post("/webhook/clerk")
async def clerk_webhook(request: Request):
    """Webhook para recibir eventos de Clerk"""
    try:
        # Obtener el payload
        body = await request.body()
        payload = json.loads(body)
        
        event_type = payload.get("type")
        data = payload.get("data", {})
        
        print(f"🔔 Webhook recibido: {event_type}")
        print(f"📄 Datos: {data.get('id', 'No ID')}")
        
        if event_type == "user.created":
            # Usuario creado en Clerk - crear automáticamente en BD
            email_addresses = data.get("email_addresses", [])
            primary_email = ""
            
            # Buscar el email primario
            for email_obj in email_addresses:
                if email_obj.get("id") == data.get("primary_email_address_id"):
                    primary_email = email_obj.get("email_address", "")
                    break
            
            # Si no encontramos el primario, usar el primero disponible
            if not primary_email and email_addresses:
                primary_email = email_addresses[0].get("email_address", "")
            
            user_data = UserCreate(
                clerk_id=data.get("id"),
                email=primary_email,
                username=data.get("username"),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                profile_image_url=data.get("profile_image_url")
            )
            
            created_user = await user_service.create_user(user_data)
            print(f"✅ Usuario creado automáticamente: {created_user.email}")
            
        elif event_type == "user.updated":
            # Usuario actualizado en Clerk
            email_addresses = data.get("email_addresses", [])
            primary_email = ""
            
            for email_obj in email_addresses:
                if email_obj.get("id") == data.get("primary_email_address_id"):
                    primary_email = email_obj.get("email_address", "")
                    break
                    
            if not primary_email and email_addresses:
                primary_email = email_addresses[0].get("email_address", "")
            
            user_update = UserUpdate(
                email=primary_email,
                username=data.get("username"),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                profile_image_url=data.get("profile_image_url")
            )
            
            updated_user = await user_service.update_user(data.get("id"), user_update)
            print(f"✅ Usuario actualizado automáticamente: {data.get('id')}")
            
        elif event_type == "session.created":
            # Usuario inició sesión - actualizar último login
            await user_service.update_last_sign_in(data.get("user_id"))
            print(f"✅ Inicio de sesión registrado: {data.get('user_id')}")
            
        elif event_type == "user.deleted":
            # Usuario eliminado en Clerk
            success = await user_service.delete_user(data.get("id"))
            print(f"✅ Usuario eliminado: {data.get('id')}")
        
        return {"status": "success", "message": "Webhook procesado", "event": event_type}
        
    except Exception as e:
        print(f"❌ Error en webhook: {str(e)}")
        print(f"📄 Payload recibido: {payload if 'payload' in locals() else 'No payload'}")
        raise HTTPException(status_code=400, detail=f"Error procesando webhook: {str(e)}")

# Endpoint para sincronizar usuario manualmente
@router.post("/sync-user", response_model=UserResponse)
async def sync_user_manually(user_data: UserCreate):
    """Sincronizar usuario manualmente desde el frontend"""
    try:
        user = await user_service.create_user(user_data)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Obtener usuario por Clerk ID
@router.get("/clerk/{clerk_id}", response_model=UserResponse)
async def get_user_by_clerk_id(clerk_id: str):
    """Obtener usuario por Clerk ID"""
    user = await user_service.get_user_by_clerk_id(clerk_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# Obtener todos los usuarios
@router.get("/", response_model=List[UserResponse])
async def get_all_users(skip: int = 0, limit: int = 100):
    """Obtener todos los usuarios"""
    users = await user_service.get_all_users(skip=skip, limit=limit)
    return users

# Ruta alternativa sin slash para evitar 307 redirects
@router.get("", response_model=List[UserResponse])
async def get_all_users_no_slash(skip: int = 0, limit: int = 100):
    """Obtener todos los usuarios (sin slash final)"""
    users = await user_service.get_all_users(skip=skip, limit=limit)
    return users

# Actualizar usuario
@router.put("/clerk/{clerk_id}", response_model=UserResponse)
async def update_user(clerk_id: str, user_update: UserUpdate):
    """Actualizar usuario"""
    user = await user_service.update_user(clerk_id, user_update)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

# Eliminar usuario
@router.delete("/clerk/{clerk_id}")
async def delete_user(clerk_id: str):
    """Eliminar usuario (soft delete)"""
    success = await user_service.delete_user(clerk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Usuario eliminado exitosamente"}

# Endpoint de prueba para obtener información del usuario actual
@router.get("/me", response_model=UserResponse)
async def get_current_user(clerk_user_id: str = Header(None, alias="X-Clerk-User-Id")):
    """Obtener información del usuario actual basado en el header de Clerk"""
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="No se encontró ID de usuario en headers")
    
    user = await user_service.get_user_by_clerk_id(clerk_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado en la base de datos")
    
    return user
