from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# --- Schemas de Entrada (Requests) ---
# Usado quando o usuário está se cadastrando
class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8)

# Usado apenas para login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# --- Schemas de Atualização (Requests) ---
# Usado para atualizar dados do usuário (opcional, mas recomendado)
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    avatar_url: Optional[str] = None
    # Permitir atualizar o check semanal via API se necessário
    last_weekly_check: Optional[datetime] = None

# --- Schemas de Saída (Responses) ---
# Usado para devolver os dados do usuário para o front-end
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    # Mapeando 'full_name' do banco. O 'name' do UserCreate geralmente vira 'full_name' no banco
    full_name: Optional[str] = None
    
    is_active: bool = True
    is_admin: bool = False
    is_profile_completed: bool = False
    
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    # O CAMPO NOVO: Essencial para o front-end saber a data!
    last_weekly_check: Optional[datetime] = None

    # Esta configuração permite que o Pydantic leia direto do objeto do Banco de Dados
    class Config:
        from_attributes = True # Para Pydantic V2
        # orm_mode = True      # Se estiver usando Pydantic V1 (antigo), descomente esta linha e comente a de cima
