# app/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from . import schemas # Para o esquema schemas.TokenData

load_dotenv() 

SECRET_KEY = "minha_palavra_chave_secreta_e_longa_para_o_palcoapp_12345_!@#$%" 
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_senha(senha_texto_plano: str, senha_hasheada: str) -> bool:
    # print(f"DEBUG security.verificar_senha: Verificando senha...") # DEBUG
    try:
        resultado = pwd_context.verify(senha_texto_plano, senha_hasheada)
        # print(f"DEBUG security.verificar_senha: Resultado da verificação: {resultado}") # DEBUG
        return resultado
    except Exception as e:
        # print(f"ERRO em security.verificar_senha: {type(e).__name__} - {e}") # DEBUG
        return False

def obter_hash_da_senha(senha: str) -> str:
    # print(f"DEBUG security.obter_hash_da_senha: Gerando hash...") # DEBUG
    return pwd_context.hash(senha)

def criar_access_token(
    data: dict, # Espera {'sub': email, 'user_id': id, 'role': 'musico' ou 'fan'}
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    # print(f"DEBUG security.criar_access_token: Entrando com data: {to_encode}") # DEBUG
    try:
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        # print(f"DEBUG security.criar_access_token: Payload para codificar: {to_encode}") # DEBUG
        
        if not SECRET_KEY:
            # print("ERRO FATAL security.criar_access_token: SECRET_KEY não está definida!") # DEBUG
            raise ValueError("SECRET_KEY não configurada para JWT.")

        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        # print(f"DEBUG security.criar_access_token: Token JWT codificado: {encoded_jwt[:20]}...") # DEBUG
        return encoded_jwt
    except JWTError as e:
        # print(f"ERRO JWTError em security.criar_access_token: {e}") # DEBUG
        raise
    except Exception as e:
        # print(f"ERRO GERAL em security.criar_access_token: {type(e).__name__} - {e}") # DEBUG
        raise

# OAuth2PasswordBearer para o endpoint de login dos músicos
oauth2_scheme_musico = OAuth2PasswordBearer(tokenUrl="/token")

# OAuth2PasswordBearer para o (futuro) endpoint de login dos fãs
oauth2_scheme_fan = OAuth2PasswordBearer(tokenUrl="/usuarios/token") 
# Usaremos oauth2_scheme_fan na dependência de decodificação quando soubermos que é um fã,
# ou podemos ter uma função de dependência genérica que tenta decodificar.
# Por agora, a decodificar_validar_token pode continuar usando um scheme default
# se o token sempre vier no mesmo header. A distinção do tokenUrl é mais para o Swagger UI.

# A função decodificar_validar_token pode ser usada por ambos, pois o token JWT é padrão.
# O que vai mudar é a lógica *depois* de decodificar, para buscar o tipo de usuário correto.
# Mas a dependência que INJETA o token pode ser específica se quisermos que o Swagger UI
# aponte para o tokenUrl correto.
# Para simplificar, vamos manter uma função de decodificação, mas as dependências de obter usuário serão específicas.

async def decodificar_validar_token_base(token: str) -> schemas.TokenData: # Função base sem Depends
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        user_id: Optional[int] = payload.get("user_id")
        role: Optional[str] = payload.get("role")

        if email is None or user_id is None or role is None:
            raise credentials_exception
        
        token_data = schemas.TokenData(email=email, user_id=user_id, role=role)
    except JWTError:
        raise credentials_exception
    except Exception: # Captura outras exceções durante o processo
        raise credentials_exception
    return token_data

# Dependência que usa o scheme de músico (para documentação)
async def obter_payload_token_musico(token: str = Depends(oauth2_scheme_musico)) -> schemas.TokenData:
    return await decodificar_validar_token_base(token)

# Dependência que usa o scheme de fã (para documentação)
async def obter_payload_token_fan(token: str = Depends(oauth2_scheme_fan)) -> schemas.TokenData:
    return await decodificar_validar_token_base(token)