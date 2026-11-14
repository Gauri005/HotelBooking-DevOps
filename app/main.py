
import os
import uuid
from datetime import date

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, String, Integer, Date,
    ForeignKey, select
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column,
    sessionmaker, Session
)
from sqlalchemy.exc import IntegrityError

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://hotel_app:hotel_pass@localhost:5432/hotel_booking"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_type: Mapped[str] = mapped_column(String(30), index=True)
    price: Mapped[int] = mapped_column(Integer)


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_reference: Mapped[str] = mapped_column(
        String(40), unique=True, index=True
    )
    customer_name: Mapped[str] = mapped_column(String(100))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")


class BookingRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    room_type: str
    check_in: date
    check_out: date


app = FastAPI(
    title="Hotel Booking API",
    description="Room availability and reservation service",
    version="1.0.0"
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database():
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        if db.scalar(select(Room.id).limit(1)) is None:
            db.add_all([
                Room(room_type="Standard", price=2000),
                Room(room_type="Standard", price=2000),
                Room(room_type="Deluxe", price=3500),
                Room(room_type="Deluxe", price=3500),
                Room(room_type="Suite", price=5000),
            ])
            db.commit()


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {"message": "Hotel Booking API is running"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(Room.id).limit(1))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.get("/availability")
def availability(
    check_in: date,
    check_out: date,
    room_type: str,
    db: Session = Depends(get_db)
):
    if check_out <= check_in:
        raise HTTPException(400, "Check-out must be after check-in")

    rooms = db.scalars(
        select(Room).where(Room.room_type == room_type)
    ).all()

    available = []

    for room in rooms:
        conflict = db.scalar(
            select(Reservation.id).where(
                Reservation.room_id == room.id,
                Reservation.status == "confirmed",
                Reservation.check_in < check_out,
                Reservation.check_out > check_in
            ).limit(1)
        )

        if conflict is None:
            available.append(room.id)

    return {
        "room_type": room_type,
        "available": len(available) > 0,
        "available_rooms": len(available)
    }


@app.post("/reservations", status_code=201)
def create_reservation(
    request: BookingRequest,
    db: Session = Depends(get_db)
):
    if request.check_out <= request.check_in:
        raise HTTPException(400, "Invalid date range")

    try:
        with db.begin():
            # Lock matching room rows to serialize competing bookings.
            rooms = db.scalars(
                select(Room)
                .where(Room.room_type == request.room_type)
                .order_by(Room.id)
                .with_for_update()
            ).all()

            if not rooms:
                raise HTTPException(404, "Room type not found")

            selected_room = None

            for room in rooms:
                conflict = db.scalar(
                    select(Reservation.id).where(
                        Reservation.room_id == room.id,
                        Reservation.status == "confirmed",
                        Reservation.check_in < request.check_out,
                        Reservation.check_out > request.check_in
                    ).limit(1)
                )

                if conflict is None:
                    selected_room = room
                    break

            if selected_room is None:
                raise HTTPException(409, "No rooms available for these dates")

            reference = "HTL-" + uuid.uuid4().hex[:10].upper()

            booking = Reservation(
                booking_reference=reference,
                customer_name=request.customer_name,
                room_id=selected_room.id,
                check_in=request.check_in,
                check_out=request.check_out,
                status="confirmed"
            )

            db.add(booking)
            db.flush()

        return {
            "booking_reference": reference,
            "customer_name": request.customer_name,
            "room_type": request.room_type,
            "check_in": request.check_in,
            "check_out": request.check_out,
            "status": "confirmed"
        }

    except IntegrityError:
        raise HTTPException(409, "Booking conflict. Please retry.")
