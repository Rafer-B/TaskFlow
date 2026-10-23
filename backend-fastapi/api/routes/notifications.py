from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.models import Notification, User
from app.schemas import NotificationPublic
from db.session import get_db

router = APIRouter(prefix="/api/notifications", tags=["Notificações"])


@router.get("", response_model=list[NotificationPublic])
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.created_at.desc())
        ).all()
    )


# Marcar como lida e uma operacao idempotente em termos de autorizacao: apenas
# o dono da notificacao pode alterar o estado.
@router.patch("/{notification_id}/read", response_model=NotificationPublic)
def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
