"""
ANÁLISIS PROFUNDO DEL TOKEN
Verificar qué audiencias tiene y por qué falla en endpoints SIRE
"""

import json
import base64
from datetime import datetime


def analizar_token():
    """Analizar el token JWT para entender el problema"""
    print("🔍 ANÁLISIS PROFUNDO DEL TOKEN JWT")
    print("=" * 60)
    
    # Cargar token
    try:
        with open("sunat_token_oficial.json", "r") as f:
            data = json.load(f)
            token = data["token_data"]["access_token"]
        print(f"✅ Token cargado correctamente")
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Decodificar JWT (sin verificar firma)
    try:
        # Dividir token en partes
        parts = token.split('.')
        if len(parts) != 3:
            print(f"❌ Token JWT malformado")
            return
        
        header_data = parts[0]
        payload_data = parts[1]
        signature = parts[2]
        
        print(f"\n📋 ESTRUCTURA JWT:")
        print(f"   Header: {len(header_data)} chars")
        print(f"   Payload: {len(payload_data)} chars") 
        print(f"   Signature: {len(signature)} chars")
        
        # Decodificar header
        header_decoded = base64.urlsafe_b64decode(header_data + '==')
        header_json = json.loads(header_decoded)
        
        print(f"\n🔐 HEADER:")
        print(f"   {json.dumps(header_json, indent=3, ensure_ascii=False)}")
        
        # Decodificar payload
        payload_decoded = base64.urlsafe_b64decode(payload_data + '==')
        payload_json = json.loads(payload_decoded)
        
        print(f"\n📄 PAYLOAD COMPLETO:")
        print(f"   {json.dumps(payload_json, indent=3, ensure_ascii=False)}")
        
        # Analizar audiencias
        print(f"\n🎯 ANÁLISIS DE AUDIENCIAS:")
        print("-" * 40)
        
        aud = payload_json.get('aud', '')
        if isinstance(aud, str):
            # Parsear audiencias (parece estar como string JSON)
            try:
                aud_parsed = json.loads(aud)
                print(f"📊 Audiencias encontradas: {len(aud_parsed)}")
                
                sire_found = False
                for i, audience in enumerate(aud_parsed):
                    if isinstance(audience, dict) and 'api' in audience:
                        api_url = audience['api']
                        recursos = audience.get('recurso', [])
                        
                        print(f"\n   API #{i+1}: {api_url}")
                        print(f"      Recursos disponibles: {len(recursos)}")
                        
                        for recurso in recursos:
                            resource_id = recurso.get('id', '')
                            indicador = recurso.get('indicador', '')
                            gt = recurso.get('gt', '')
                            print(f"         • {resource_id} (indicador: {indicador}, gt: {gt})")
                        
                        if 'sire' in api_url.lower():
                            sire_found = True
                            print(f"      🟢 ¡SIRE ENCONTRADO!")
                            
                            # Verificar si tiene el recurso correcto para RVIE
                            for recurso in recursos:
                                resource_id = recurso.get('id', '')
                                if 'migeigv' in resource_id:
                                    print(f"      🟢 ¡RECURSO RVIE ENCONTRADO: {resource_id}!")
                                elif 'libros' in resource_id:
                                    print(f"      🟡 Recurso libros: {resource_id}")
                
                if not sire_found:
                    print(f"\n   ❌ SIRE NO ENCONTRADO EN AUDIENCIAS")
                    print(f"   💡 Esto explica el ERROR 401 en endpoints SIRE")
                else:
                    print(f"\n   ✅ SIRE SÍ ESTÁ EN AUDIENCIAS")
                    print(f"   💡 El problema debe estar en otra parte...")
                    
            except Exception as e:
                print(f"   ❌ Error parseando audiencias: {e}")
                print(f"   📄 Audiencias raw: {aud}")
        
        # Verificar expiración
        exp = payload_json.get('exp', 0)
        exp_datetime = datetime.fromtimestamp(exp)
        now = datetime.now()
        
        print(f"\n⏰ EXPIRACIÓN:")
        print(f"   Expira: {exp_datetime}")
        print(f"   Ahora: {now}")
        print(f"   Válido: {'✅ SÍ' if exp_datetime > now else '❌ NO'}")
        
        # Verificar otros campos importantes
        sub = payload_json.get('sub', '')
        iss = payload_json.get('iss', '')
        client_id = payload_json.get('clientId', '')
        
        print(f"\n🔑 OTROS CAMPOS:")
        print(f"   Subject (RUC): {sub}")
        print(f"   Issuer: {iss}")
        print(f"   Client ID: {client_id}")
        
        # Verificar datos de usuario
        userdata = payload_json.get('userdata', {})
        if userdata:
            print(f"\n👤 DATOS DE USUARIO:")
            print(f"   RUC: {userdata.get('numRUC', '')}")
            print(f"   Usuario SOL: {userdata.get('usuarioSOL', '')}")
            print(f"   Login: {userdata.get('login', '')}")
            print(f"   Ticket: {userdata.get('ticket', '')}")
        
    except Exception as e:
        print(f"❌ Error decodificando token: {e}")
    
    print(f"\n📋 CONCLUSIONES:")
    print(f"Si SIRE está en audiencias pero tenemos 401:")
    print(f"• Token válido pero recurso específico no autorizado")
    print(f"• URL del endpoint incorrecta")
    print(f"• Headers adicionales requeridos")
    print(f"• Período sin datos disponibles")


if __name__ == "__main__":
    analizar_token()
