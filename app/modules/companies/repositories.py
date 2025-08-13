from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from datetime import datetime

from ...database import get_database
from .models import CompanyModel

class CompanyRepository:
    """
    Repository para operaciones de empresas en MongoDB
    """
    
    def __init__(self):
        self.db = get_database()
        self.collection: AsyncIOMotorCollection = self.db.companies
    
    async def create_company(self, company_data: Dict[str, Any]) -> CompanyModel:
        """Crear una nueva empresa"""
        # Asegurar timestamps
        company_data["fecha_registro"] = datetime.now()
        company_data["fecha_actualizacion"] = datetime.now()
        
        # Insertar en MongoDB
        result = await self.collection.insert_one(company_data)
        
        # Obtener el documento insertado
        company_doc = await self.collection.find_one({"_id": result.inserted_id})
        return CompanyModel(**company_doc)
    
    async def get_company_by_ruc(self, ruc: str) -> Optional[CompanyModel]:
        """Obtener empresa por RUC"""
        company_doc = await self.collection.find_one({"ruc": ruc})
        if company_doc:
            return CompanyModel(**company_doc)
        return None
    
    async def get_company_by_id(self, company_id: str) -> Optional[CompanyModel]:
        """Obtener empresa por ID"""
        try:
            company_doc = await self.collection.find_one({"_id": ObjectId(company_id)})
            if company_doc:
                return CompanyModel(**company_doc)
        except Exception:
            pass
        return None
    
    async def update_company(self, ruc: str, update_data: Dict[str, Any]) -> Optional[CompanyModel]:
        """Actualizar empresa por RUC"""
        # Agregar timestamp de actualización
        update_data["fecha_actualizacion"] = datetime.now()
        
        # Actualizar documento
        result = await self.collection.find_one_and_update(
            {"ruc": ruc},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            return CompanyModel(**result)
        return None
    
    async def delete_company(self, ruc: str) -> bool:
        """Eliminar empresa por RUC (soft delete)"""
        result = await self.collection.update_one(
            {"ruc": ruc},
            {
                "$set": {
                    "activa": False,
                    "fecha_actualizacion": datetime.now()
                }
            }
        )
        return result.modified_count > 0
    
    async def list_companies(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        activas_only: bool = False,
        con_sire_only: bool = False
    ) -> List[CompanyModel]:
        """Listar empresas con filtros opcionales"""
        filter_query = {}
        
        if activas_only:
            filter_query["activa"] = True
        
        if con_sire_only:
            filter_query["sire_activo"] = True
        
        cursor = self.collection.find(filter_query).skip(skip).limit(limit)
        companies_docs = await cursor.to_list(length=limit)
        
        return [CompanyModel(**doc) for doc in companies_docs]
    
    async def count_companies(self, activas_only: bool = False, con_sire_only: bool = False) -> int:
        """Contar empresas con filtros"""
        filter_query = {}
        
        if activas_only:
            filter_query["activa"] = True
            
        if con_sire_only:
            filter_query["sire_activo"] = True
        
        return await self.collection.count_documents(filter_query)
    
    async def search_companies(self, query: str, limit: int = 10) -> List[CompanyModel]:
        """Buscar empresas por texto (RUC, razón social)"""
        search_filter = {
            "$or": [
                {"ruc": {"$regex": query, "$options": "i"}},
                {"razon_social": {"$regex": query, "$options": "i"}}
            ]
        }
        
        cursor = self.collection.find(search_filter).limit(limit)
        companies_docs = await cursor.to_list(length=limit)
        
        return [CompanyModel(**doc) for doc in companies_docs]
    
    async def get_companies_with_sire(self) -> List[CompanyModel]:
        """Obtener solo empresas con SIRE configurado"""
        filter_query = {
            "sire_activo": True,
            "sire_client_id": {"$ne": None},
            "sire_client_secret": {"$ne": None},
            "sunat_usuario": {"$ne": None},
            "sunat_clave": {"$ne": None}
        }
        
        cursor = self.collection.find(filter_query)
        companies_docs = await cursor.to_list(length=None)
        
        return [CompanyModel(**doc) for doc in companies_docs]
    
    async def exists_company(self, ruc: str) -> bool:
        """Verificar si existe una empresa con el RUC dado"""
        count = await self.collection.count_documents({"ruc": ruc})
        return count > 0
    
    async def configure_sire(
        self, 
        ruc: str, 
        client_id: str, 
        client_secret: str,
        sunat_usuario: str, 
        sunat_clave: str
    ) -> Optional[CompanyModel]:
        """Configurar credenciales SIRE para una empresa"""
        print(f"🗃️  [REPOSITORY] configure_sire para RUC: {ruc}")
        print(f"🔑 [REPOSITORY] client_id: {client_id[:10]}...")
        print(f"🔐 [REPOSITORY] sunat_usuario: {sunat_usuario}")
        
        update_data = {
            "sire_client_id": client_id,
            "sire_client_secret": client_secret,
            "sunat_usuario": sunat_usuario,
            "sunat_clave": sunat_clave,
            "sire_activo": True,
            "fecha_actualizacion": datetime.now()
        }
        
        print(f"📝 [REPOSITORY] Datos de actualización: {list(update_data.keys())}")
        
        try:
            result = await self.update_company(ruc, update_data)
            print(f"💾 [REPOSITORY] Resultado update_company: {result is not None}")
            return result
        except Exception as e:
            print(f"❌ [REPOSITORY] Error en configure_sire: {type(e).__name__}: {str(e)}")
            raise
    
    async def disable_sire(self, ruc: str) -> Optional[CompanyModel]:
        """Desactivar SIRE para una empresa"""
        update_data = {
            "sire_activo": False,
            "fecha_actualizacion": datetime.now()
        }
        
        return await self.update_company(ruc, update_data)
