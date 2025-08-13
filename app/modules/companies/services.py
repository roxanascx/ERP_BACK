import os
from typing import List, Optional, Dict, Any
from datetime import datetime

from .models import CompanyModel
from .repositories import CompanyRepository
from .schemas import (
    CompanyCreate, CompanyUpdate, SireConfigRequest, AdditionalCredentialsUpdate,
    CompanyResponse, CompanyDetailResponse, CompanySummaryResponse, 
    CompanyListResponse, SireCredentialsResponse, SireInfoResponse,
    CurrentCompanyResponse, SireMethod
)

class CompanyService:
    """
    Servicio de gestión de empresas con soporte completo para SIRE
    Adaptado del EmpresaService original con arquitectura del proyecto
    Implementa patrón Singleton para mantener estado de empresa actual
    """
    
    _instance = None
    _empresa_actual: Optional[CompanyModel] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.repository = CompanyRepository()
        return cls._instance
    
    @property
    def empresa_actual(self) -> Optional[CompanyModel]:
        return self._empresa_actual
    
    @empresa_actual.setter
    def empresa_actual(self, value: Optional[CompanyModel]):
        self._empresa_actual = value
    
    # =========================================
    # GESTIÓN BÁSICA DE EMPRESAS (CRUD)
    # =========================================
    
    async def create_company(self, company_data: CompanyCreate) -> CompanyResponse:
        """Crear una nueva empresa"""
        # Verificar que no existe una empresa con el mismo RUC
        if await self.repository.exists_company(company_data.ruc):
            raise ValueError(f"Ya existe una empresa con RUC {company_data.ruc}")
        
        # Convertir a dict y crear
        company_dict = company_data.model_dump()
        company = await self.repository.create_company(company_dict)
        
        return self._company_to_response(company)
    
    async def get_company(self, ruc: str) -> Optional[CompanyDetailResponse]:
        """Obtener empresa por RUC"""
        company = await self.repository.get_company_by_ruc(ruc)
        if company:
            return self._company_to_detail_response(company)
        return None
    
    async def update_company(self, ruc: str, update_data: CompanyUpdate) -> Optional[CompanyResponse]:
        """Actualizar empresa existente"""
        # Filtrar campos None
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
        
        if not update_dict:
            raise ValueError("No hay datos para actualizar")
        
        company = await self.repository.update_company(ruc, update_dict)
        if company:
            return self._company_to_response(company)
        return None
    
    async def delete_company(self, ruc: str) -> bool:
        """Eliminar empresa (soft delete)"""
        # No permitir eliminar si es la empresa actual
        if self.empresa_actual and self.empresa_actual.ruc == ruc:
            raise ValueError("No se puede eliminar la empresa actualmente seleccionada")
        
        return await self.repository.delete_company(ruc)
    
    async def list_companies(
        self, 
        skip: int = 0, 
        limit: int = 100,
        activas_only: bool = False,
        con_sire_only: bool = False
    ) -> CompanyListResponse:
        """Listar empresas con metadatos"""
        try:
            print(f"🔧 [SERVICE] list_companies iniciado")
            companies = await self.repository.list_companies(skip, limit, activas_only, con_sire_only)
            print(f"📊 [SERVICE] Empresas obtenidas: {len(companies)}")
            
            total = await self.repository.count_companies(activas_only, con_sire_only)
            print(f"📊 [SERVICE] Total count: {total}")
            
            total_con_sire = await self.repository.count_companies(activas_only=False, con_sire_only=True)
            print(f"📊 [SERVICE] Total con SIRE: {total_con_sire}")
            
            print(f"🏗️  [SERVICE] Creando summaries...")
            company_summaries = []
            for i, company in enumerate(companies):
                try:
                    print(f"  📝 [SERVICE] Procesando empresa {i+1}: {company.ruc}")
                    
                    # Sanitizar datos corruptos
                    sire_activo = company.sire_activo
                    if isinstance(sire_activo, str):
                        sire_activo = sire_activo.lower() in ('true', '1', 'yes', 'on')
                    elif not isinstance(sire_activo, bool):
                        sire_activo = False
                    
                    summary = CompanySummaryResponse(
                        ruc=company.ruc,
                        razon_social=company.razon_social,
                        direccion=company.direccion or "",
                        telefono=company.telefono or "",
                        email=company.email or "",
                        activa=company.activa,
                        sire_activo=sire_activo,  # Usar valor sanitizado
                        tiene_sire=company.tiene_sire(),
                        es_actual=self.empresa_actual is not None and self.empresa_actual.ruc == company.ruc,
                        notas_internas=getattr(company, 'notas_internas', None)
                    )
                    company_summaries.append(summary)
                    print(f"  ✅ [SERVICE] Empresa {company.ruc} procesada exitosamente")
                except Exception as e:
                    print(f"  ❌ [SERVICE] Error procesando empresa {company.ruc}: {type(e).__name__}: {str(e)}")
                    # Continuar con la siguiente empresa en lugar de fallar todo
                    continue
            
            print(f"🏁 [SERVICE] Creando respuesta final...")
            result = CompanyListResponse(
                companies=company_summaries,
                total=total,
                total_con_sire=total_con_sire,
                empresa_actual=self.empresa_actual.ruc if self.empresa_actual else None
            )
            print(f"✅ [SERVICE] list_companies completado exitosamente")
            return result
            
        except Exception as e:
            print(f"❌ [SERVICE] Error en list_companies: {type(e).__name__}: {str(e)}")
            raise
    
    async def search_companies(self, query: str, limit: int = 10) -> List[CompanySummaryResponse]:
        """Buscar empresas por texto"""
        companies = await self.repository.search_companies(query, limit)
        
        return [
            CompanySummaryResponse(
                ruc=company.ruc,
                razon_social=company.razon_social,
                direccion=company.direccion or "",
                telefono=company.telefono or "",
                email=company.email or "",
                activa=company.activa,
                sire_activo=company.sire_activo,
                tiene_sire=company.tiene_sire(),
                es_actual=self.empresa_actual is not None and self.empresa_actual.ruc == company.ruc,
                notas_internas=getattr(company, 'notas_internas', None)
            )
            for company in companies
        ]
    
    # =========================================
    # GESTIÓN MULTI-EMPRESA
    # =========================================
    
    async def select_current_company(self, ruc: str) -> bool:
        """Seleccionar empresa actual para operaciones"""
        company = await self.repository.get_company_by_ruc(ruc)
        if not company:
            raise ValueError(f"Empresa no encontrada: {ruc}")
        
        if not company.activa:
            raise ValueError(f"Empresa inactiva: {ruc}")
        
        self.empresa_actual = company
        
        # Sincronizar variables de entorno si es necesario
        await self._sync_environment_variables()
        
        return True
    
    async def get_current_company(self) -> CurrentCompanyResponse:
        """Obtener información de la empresa actual"""
        if self.empresa_actual:
            return CurrentCompanyResponse(
                empresa_seleccionada=True,
                ruc=self.empresa_actual.ruc,
                razon_social=self.empresa_actual.razon_social,
                sire_activo=self.empresa_actual.sire_activo,
                tiene_sire=self.empresa_actual.tiene_sire()
            )
        
        return CurrentCompanyResponse(
            empresa_seleccionada=False,
            ruc=None,
            razon_social=None,
            sire_activo=False,
            tiene_sire=False
        )
    
    # =========================================
    # GESTIÓN DE CREDENCIALES SIRE
    # =========================================
    
    async def configure_sire(self, ruc: str, sire_config: SireConfigRequest) -> Optional[SireInfoResponse]:
        """Configurar credenciales SIRE para una empresa"""
        print(f"🔧 [SERVICE] configure_sire llamado con RUC: {ruc}")
        print(f"📋 [SERVICE] Datos del config: {sire_config.dict()}")
        
        try:
            company = await self.repository.configure_sire(
                ruc=ruc,
                client_id=sire_config.client_id,
                client_secret=sire_config.client_secret,
                sunat_usuario=sire_config.sunat_usuario,
                sunat_clave=sire_config.sunat_clave
            )
            print(f"🏢 [SERVICE] Resultado del repository: {company is not None}")
            
            if company:
                # Actualizar empresa actual si es la misma
                if self.empresa_actual and self.empresa_actual.ruc == ruc:
                    self.empresa_actual = company
                
                response = SireInfoResponse(
                    ruc=company.ruc,
                    razon_social=company.razon_social,
                    sire_activo=company.sire_activo,
                    tiene_credenciales=company.tiene_sire(),
                    client_id=company.sire_client_id,
                    sunat_usuario=company.sunat_usuario,
                    fecha_actualizacion=company.fecha_actualizacion
                )
                print(f"✅ [SERVICE] Respuesta generada exitosamente")
                return response
                
            print(f"❌ [SERVICE] No se pudo configurar SIRE - company es None")
            return None
            
        except Exception as e:
            print(f"❌ [SERVICE] Error en configure_sire: {type(e).__name__}: {str(e)}")
            raise
    
    async def get_sire_credentials(self, ruc: str, method: SireMethod = SireMethod.ORIGINAL) -> Optional[SireCredentialsResponse]:
        """Obtener credenciales SIRE de una empresa"""
        company = await self.repository.get_company_by_ruc(ruc)
        if not company or not company.tiene_sire():
            return None
        
        if method == SireMethod.ORIGINAL:
            creds = company.obtener_credenciales_sire_original()
        else:
            creds = company.obtener_credenciales_sire_migrado()
        
        if creds:
            return SireCredentialsResponse(
                ruc=creds.get('ruc', company.ruc),
                client_id=creds['client_id'],
                username=creds['username'],
                endpoint_url=creds['endpoint_url'],
                metodo=creds['metodo']
            )
        return None
    
    async def disable_sire(self, ruc: str) -> Optional[SireInfoResponse]:
        """Desactivar SIRE para una empresa"""
        company = await self.repository.disable_sire(ruc)
        
        if company:
            # Actualizar empresa actual si es la misma
            if self.empresa_actual and self.empresa_actual.ruc == ruc:
                self.empresa_actual = company
            
            return SireInfoResponse(
                ruc=company.ruc,
                razon_social=company.razon_social,
                sire_activo=company.sire_activo,
                tiene_credenciales=company.tiene_sire(),
                client_id=company.sire_client_id,
                sunat_usuario=company.sunat_usuario,
                fecha_actualizacion=company.fecha_actualizacion
            )
        return None
    
    async def update_additional_credentials(self, ruc: str, credentials: AdditionalCredentialsUpdate) -> Optional[CompanyDetailResponse]:
        """Actualizar credenciales adicionales (bancarias, PDT, PLAME, etc.)"""
        # Filtrar campos None
        update_dict = {k: v for k, v in credentials.model_dump().items() if v is not None}
        
        if not update_dict:
            raise ValueError("No hay credenciales para actualizar")
        
        company = await self.repository.update_company(ruc, update_dict)
        if company:
            return self._company_to_detail_response(company)
        return None
    
    # =========================================
    # CONFIGURACIÓN DE VARIABLES DE ENTORNO
    # =========================================
    
    async def configure_environment_variables(self, method: SireMethod = SireMethod.ORIGINAL) -> bool:
        """Configurar variables de entorno para SIRE"""
        if not self.empresa_actual:
            raise ValueError("No hay empresa seleccionada")
        
        if not self.empresa_actual.tiene_sire():
            raise ValueError(f"Empresa {self.empresa_actual.ruc} no tiene SIRE configurado")
        
        if method == SireMethod.ORIGINAL:
            # Variables para método original
            os.environ['SUNAT_CLIENT_ID'] = self.empresa_actual.sire_client_id
            os.environ['SUNAT_CLIENT_SECRET'] = self.empresa_actual.sire_client_secret
            os.environ['SUNAT_SOL_USERNAME'] = f"{self.empresa_actual.ruc} {self.empresa_actual.sunat_usuario}"
            os.environ['SUNAT_SOL_PASSWORD'] = self.empresa_actual.sunat_clave
            
        elif method == SireMethod.MIGRADO:
            # Variables para método migrado
            os.environ['SUNAT_RUC'] = self.empresa_actual.ruc
            os.environ['SUNAT_USUARIO'] = self.empresa_actual.sunat_usuario
            os.environ['SUNAT_CLAVE_SOL'] = self.empresa_actual.sunat_clave
            os.environ['SUNAT_CLIENT_ID'] = self.empresa_actual.sire_client_id
            os.environ['SUNAT_CLIENT_SECRET'] = self.empresa_actual.sire_client_secret
        
        return True
    
    # =========================================
    # UTILIDADES Y HELPERS PRIVADOS
    # =========================================
    
    def _company_to_response(self, company: CompanyModel) -> CompanyResponse:
        """Convertir modelo a response básico"""
        return CompanyResponse(
            id=str(company.id) if company.id else None,
            ruc=company.ruc,
            razon_social=company.razon_social,
            direccion=company.direccion or "",
            telefono=company.telefono or "",
            email=company.email or "",
            activa=company.activa,
            sire_activo=company.sire_activo,
            tiene_sire=company.tiene_sire(),
            fecha_registro=company.fecha_registro,
            fecha_actualizacion=company.fecha_actualizacion
        )
    
    def _company_to_detail_response(self, company: CompanyModel) -> CompanyDetailResponse:
        """Convertir modelo a response detallado"""
        return CompanyDetailResponse(
            id=str(company.id) if company.id else None,
            ruc=company.ruc,
            razon_social=company.razon_social,
            direccion=company.direccion or "",
            telefono=company.telefono or "",
            email=company.email or "",
            activa=company.activa,
            sire_activo=company.sire_activo,
            tiene_sire=company.tiene_sire(),
            fecha_registro=company.fecha_registro,
            fecha_actualizacion=company.fecha_actualizacion,
            sire_client_id=company.sire_client_id,
            sunat_usuario=company.sunat_usuario,
            sunat_usuario_secundario=company.sunat_usuario_secundario,
            sistema_bancario=company.sistema_bancario,
            banco_usuario=company.banco_usuario,
            pdt_usuario=company.pdt_usuario,
            plame_usuario=company.plame_usuario,
            configuraciones=company.configuraciones or {},
            notas_internas=company.notas_internas
        )
    
    async def _sync_environment_variables(self):
        """Sincronizar variables de entorno automáticamente"""
        # Aquí podrías agregar lógica para sincronizar con sistemas externos
        # Por ejemplo, actualizar ClsVariableGlobales si existe
        pass
