"""CRUD endpoints for clients."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.client import Client
from backend.schemas.client import ClientCreate, ClientResponse, ClientUpdate

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=list[ClientResponse])
def list_clients(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Client)
    if active_only:
        query = query.filter(Client.active.is_(True))
    return query.order_by(Client.name).all()


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: str, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, f"Client '{client_id}' not found")
    return client


@router.post("", response_model=ClientResponse, status_code=201)
def create_client(data: ClientCreate, db: Session = Depends(get_db)):
    if db.get(Client, data.id):
        raise HTTPException(409, f"Client '{data.id}' already exists")
    client = Client(**data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(client_id: str, data: ClientUpdate, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, f"Client '{client_id}' not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client
