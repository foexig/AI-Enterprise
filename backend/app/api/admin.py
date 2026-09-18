import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Agent, Role, User
from app.schemas.admin import (
    AdminAgentOut,
    AdminUserOut,
    AgentCreate,
    AgentRolesUpdate,
    AgentUpdate,
    RoleCreate,
    RoleOut,
    UserCreate,
    UserUpdate,
)
from app.security.deps import get_current_admin
from app.security.password import hash_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


# ------------------------- Hilfsfunktionen -------------------------

def _user_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        roles=[r.name for r in user.roles],
        created_at=user.created_at,
    )


def _agent_out(agent: Agent) -> AdminAgentOut:
    return AdminAgentOut(
        id=agent.id,
        name=agent.name,
        slug=agent.slug,
        description=agent.description,
        system_prompt=agent.system_prompt,
        model_id=agent.model_id,
        is_active=agent.is_active,
        roles=[r.name for r in agent.roles],
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def _resolve_roles(db: Session, role_ids: list[int]) -> list[Role]:
    roles = db.query(Role).filter(Role.id.in_(role_ids)).all() if role_ids else []
    if len(roles) != len(set(role_ids)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Mindestens eine Rollen-ID existiert nicht")
    return roles


# ------------------------- Benutzer -------------------------

@router.get("/users", response_model=list[AdminUserOut])
def list_users(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return [_user_out(u) for u in db.query(User).order_by(User.id).all()]


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="E-Mail bereits registriert")

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        is_admin=payload.is_admin,
        roles=_resolve_roles(db, payload.role_ids),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Admin %s legte Benutzer user_id=%s an", admin.id, user.id)
    return _user_out(user)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Benutzer nicht gefunden")

    if payload.is_active is False and user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Man kann sich nicht selbst deaktivieren")

    if payload.name is not None:
        user.name = payload.name
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.role_ids is not None:
        user.roles = _resolve_roles(db, payload.role_ids)

    db.commit()
    db.refresh(user)
    return _user_out(user)


# ------------------------- Rollen -------------------------

@router.get("/roles", response_model=list[RoleOut])
def list_roles(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.id).all()


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if db.query(Role).filter(Role.name == payload.name.strip()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Rolle existiert bereits")
    role = Role(name=payload.name.strip())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


# ------------------------- Agents -------------------------

@router.get("/agents", response_model=list[AdminAgentOut])
def list_agents_admin(admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    return [_agent_out(a) for a in db.query(Agent).order_by(Agent.id).all()]


@router.post("/agents", response_model=AdminAgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, admin: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    if db.query(Agent).filter(Agent.slug == payload.slug).first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug bereits vergeben")

    agent = Agent(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        system_prompt=payload.system_prompt,
        model_id=payload.model_id,
        is_active=payload.is_active,
        roles=_resolve_roles(db, payload.role_ids),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info("Admin %s legte Agent agent_id=%s an", admin.id, agent.id)
    return _agent_out(agent)


@router.patch("/agents/{agent_id}", response_model=AdminAgentOut)
def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Agent nicht gefunden")

    if payload.slug is not None and payload.slug != agent.slug:
        if db.query(Agent).filter(Agent.slug == payload.slug).first():
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug bereits vergeben")
        agent.slug = payload.slug
    if payload.name is not None:
        agent.name = payload.name
    if payload.description is not None:
        agent.description = payload.description
    if payload.system_prompt is not None:
        agent.system_prompt = payload.system_prompt
    if payload.model_id is not None:
        agent.model_id = payload.model_id
    if payload.is_active is not None:
        agent.is_active = payload.is_active

    db.commit()
    db.refresh(agent)
    return _agent_out(agent)


@router.post("/agents/{agent_id}/roles", response_model=AdminAgentOut)
def assign_agent_roles(
    agent_id: int,
    payload: AgentRolesUpdate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Ersetzt die Rollen-Zuordnung eines Agents vollständig."""
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Agent nicht gefunden")

    agent.roles = _resolve_roles(db, payload.role_ids)
    db.commit()
    db.refresh(agent)
    return _agent_out(agent)
