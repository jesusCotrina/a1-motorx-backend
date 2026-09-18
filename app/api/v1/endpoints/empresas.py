import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.empresa import Empresa
from app.models.role import Role
from app.models.user import User
from app.schemas.empresa import (
    EmpresaAdminOut,
    EmpresaCreate,
    EmpresaEstadoUpdate,
    EmpresaUpdate,
    EmpresaUsuarioCreate,
    EmpresaUsuarioOut,
    EmpresaUsuarioUpdate,
    UsuarioEstadoUpdate,
)

router = APIRouter()

_GESTORES = ("super_admin", "admin")


def _verificar_acceso_empresa(user: User, empresa_id: uuid.UUID) -> None:
    """`admin` solo gestiona su propia empresa; `super_admin` gestiona todas."""
    if user.role.code == "admin" and user.empresa_id != empresa_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "No puedes gestionar otra organizacion"
        )


def _conteo_usuarios(db: Session, empresa_id: uuid.UUID) -> tuple[int, int]:
    total = (
        db.scalar(
            select(func.count()).select_from(User).where(User.empresa_id == empresa_id)
        )
        or 0
    )
    activos = (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.empresa_id == empresa_id, User.is_active.is_(True))
        )
        or 0
    )
    return total, activos


def _empresa_out(db: Session, empresa: Empresa) -> EmpresaAdminOut:
    total, activos = _conteo_usuarios(db, empresa.id)
    return EmpresaAdminOut.from_model(empresa, total, activos)


def _obtener_empresa(db: Session, empresa_id: uuid.UUID) -> Empresa:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizacion no encontrada")
    return empresa


@router.get("", response_model=list[EmpresaAdminOut])
def listar_empresas(
    user: User = Depends(require_roles(*_GESTORES)),
    db: Session = Depends(get_db),
) -> list[EmpresaAdminOut]:
    # super_admin ve todas las organizaciones del SaaS; admin solo la suya
    # (ver nota de "Multi-tenancy" en CLAUDE.md).
    stmt = select(Empresa).order_by(Empresa.nombre)
    if user.role.code == "admin":
        stmt = select(Empresa).where(Empresa.id == user.empresa_id)
    empresas = db.scalars(stmt)
    return [_empresa_out(db, e) for e in empresas]


@router.post("", response_model=EmpresaAdminOut, status_code=status.HTTP_201_CREATED)
def crear_empresa(
    data: EmpresaCreate,
    _: object = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> EmpresaAdminOut:
    codigo = data.codigo.strip().upper()
    if db.scalar(select(Empresa).where(Empresa.codigo == codigo)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una organizacion con ese codigo")

    if not data.usuarios:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Debes asignar al menos un usuario a la nueva organizacion",
        )
    if not any(u.role_code == "super_admin" for u in data.usuarios):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "La organizacion necesita al menos un usuario con rol Super Administrador",
        )

    correos = [u.email.strip().lower() for u in data.usuarios]
    if len(set(correos)) != len(correos):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Hay correos repetidos")

    ya_registrado = db.scalar(select(User.email).where(User.email.in_(correos)))
    if ya_registrado is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"El correo {ya_registrado} ya esta en uso"
        )

    roles = {r.code: r for r in db.scalars(select(Role))}
    for u in data.usuarios:
        if u.role_code not in roles:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Rol invalido: {u.role_code}"
            )

    empresa = Empresa(
        codigo=codigo,
        nombre=data.nombre.strip(),
        ruc=data.ruc.strip() if data.ruc else None,
        direccion=data.direccion.strip() if data.direccion else None,
        logo_url=data.logo_url,
    )
    db.add(empresa)
    db.flush()

    for u, correo in zip(data.usuarios, correos, strict=True):
        db.add(
            User(
                email=correo,
                password_hash=hash_password(u.password),
                full_name=u.full_name.strip(),
                role_id=roles[u.role_code].id,
                empresa_id=empresa.id,
            )
        )

    db.commit()
    db.refresh(empresa)
    return _empresa_out(db, empresa)


@router.patch("/{empresa_id}", response_model=EmpresaAdminOut)
def actualizar_empresa(
    empresa_id: uuid.UUID,
    data: EmpresaUpdate,
    user: User = Depends(require_roles(*_GESTORES)),
    db: Session = Depends(get_db),
) -> EmpresaAdminOut:
    _verificar_acceso_empresa(user, empresa_id)
    empresa = _obtener_empresa(db, empresa_id)

    codigo = data.codigo.strip().upper()
    if codigo != empresa.codigo:
        existe = db.scalar(
            select(Empresa).where(Empresa.codigo == codigo, Empresa.id != empresa_id)
        )
        if existe is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya existe una organizacion con ese codigo"
            )

    empresa.codigo = codigo
    empresa.nombre = data.nombre.strip()
    empresa.ruc = data.ruc.strip() if data.ruc else None
    empresa.direccion = data.direccion.strip() if data.direccion else None
    empresa.logo_url = data.logo_url
    db.commit()
    db.refresh(empresa)
    return _empresa_out(db, empresa)


@router.patch("/{empresa_id}/estado", response_model=EmpresaAdminOut)
def cambiar_estado_empresa(
    empresa_id: uuid.UUID,
    data: EmpresaEstadoUpdate,
    _: object = Depends(require_roles("super_admin")),
    db: Session = Depends(get_db),
) -> EmpresaAdminOut:
    empresa = _obtener_empresa(db, empresa_id)

    empresa.is_active = data.is_active
    db.commit()
    db.refresh(empresa)
    return _empresa_out(db, empresa)


@router.get("/{empresa_id}/usuarios", response_model=list[EmpresaUsuarioOut])
def listar_usuarios_empresa(
    empresa_id: uuid.UUID,
    user: User = Depends(require_roles(*_GESTORES)),
    db: Session = Depends(get_db),
) -> list[EmpresaUsuarioOut]:
    _verificar_acceso_empresa(user, empresa_id)
    _obtener_empresa(db, empresa_id)
    usuarios = db.scalars(
        select(User).where(User.empresa_id == empresa_id).order_by(User.full_name)
    )
    return [
        EmpresaUsuarioOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role_code=u.role.code,
            role_name=u.role.name,
            is_active=u.is_active,
        )
        for u in usuarios
    ]


@router.post(
    "/{empresa_id}/usuarios",
    response_model=EmpresaUsuarioOut,
    status_code=status.HTTP_201_CREATED,
)
def agregar_usuario_empresa(
    empresa_id: uuid.UUID,
    data: EmpresaUsuarioCreate,
    user: User = Depends(require_roles(*_GESTORES)),
    db: Session = Depends(get_db),
) -> EmpresaUsuarioOut:
    _verificar_acceso_empresa(user, empresa_id)
    empresa = _obtener_empresa(db, empresa_id)

    rol = db.scalar(select(Role).where(Role.code == data.role_code))
    if rol is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Rol invalido: {data.role_code}")

    correo = data.email.strip().lower()
    if db.scalar(select(User).where(User.email == correo)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El correo {correo} ya esta en uso")

    usuario = User(
        email=correo,
        password_hash=hash_password(data.password),
        full_name=data.full_name.strip(),
        role_id=rol.id,
        empresa_id=empresa.id,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return EmpresaUsuarioOut(
        id=usuario.id,
        email=usuario.email,
        full_name=usuario.full_name,
        role_code=rol.code,
        role_name=rol.name,
        is_active=usuario.is_active,
    )


@router.patch("/{empresa_id}/usuarios/{usuario_id}/estado", response_model=EmpresaUsuarioOut)
def cambiar_estado_usuario_empresa(
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    data: UsuarioEstadoUpdate,
    user: User = Depends(require_roles(*_GESTORES)),
    db: Session = Depends(get_db),
) -> EmpresaUsuarioOut:
    _verificar_acceso_empresa(user, empresa_id)
    _obtener_empresa(db, empresa_id)
    usuario = db.scalar(
        select(User).where(User.id == usuario_id, User.empresa_id == empresa_id)
    )
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    if not data.is_active and usuario.role.code == "super_admin":
        otros_activos = db.scalar(
            select(func.count())
            .select_from(User)
            .join(Role)
            .where(
                User.empresa_id == empresa_id,
                User.is_active.is_(True),
                User.id != usuario_id,
                Role.code == "super_admin",
            )
        )
        if not otros_activos:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No puedes quitar al unico Super Administrador activo de la organizacion",
            )

    usuario.is_active = data.is_active
    db.commit()
    db.refresh(usuario)
    return EmpresaUsuarioOut(
        id=usuario.id,
        email=usuario.email,
        full_name=usuario.full_name,
        role_code=usuario.role.code,
        role_name=usuario.role.name,
        is_active=usuario.is_active,
    )


@router.patch("/{empresa_id}/usuarios/{usuario_id}", response_model=EmpresaUsuarioOut)
def editar_usuario_empresa(
    empresa_id: uuid.UUID,
    usuario_id: uuid.UUID,
    data: EmpresaUsuarioUpdate,
    user: User = Depends(require_roles(*_GESTORES)),
    db: Session = Depends(get_db),
) -> EmpresaUsuarioOut:
    _verificar_acceso_empresa(user, empresa_id)
    _obtener_empresa(db, empresa_id)
    usuario = db.scalar(
        select(User).where(User.id == usuario_id, User.empresa_id == empresa_id)
    )
    if usuario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")

    rol = db.scalar(select(Role).where(Role.code == data.role_code))
    if rol is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Rol invalido: {data.role_code}")

    correo = data.email.strip().lower()
    ya_en_uso = db.scalar(select(User).where(User.email == correo, User.id != usuario_id))
    if ya_en_uso is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"El correo {correo} ya esta en uso")

    if rol.code != "super_admin" and usuario.role.code == "super_admin":
        otros_activos = db.scalar(
            select(func.count())
            .select_from(User)
            .join(Role)
            .where(
                User.empresa_id == empresa_id,
                User.is_active.is_(True),
                User.id != usuario_id,
                Role.code == "super_admin",
            )
        )
        if not otros_activos:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No puedes quitarle el rol de Super Administrador al unico activo "
                "de la organizacion",
            )

    usuario.email = correo
    usuario.full_name = data.full_name.strip()
    usuario.role_id = rol.id
    db.commit()
    db.refresh(usuario)
    return EmpresaUsuarioOut(
        id=usuario.id,
        email=usuario.email,
        full_name=usuario.full_name,
        role_code=rol.code,
        role_name=rol.name,
        is_active=usuario.is_active,
    )
