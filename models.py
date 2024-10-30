from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    first_name = Column(String, unique=False, nullable=False)
    last_name = Column(String, unique=False, nullable=False)
    patronymic = Column(String, unique=False, nullable=True)
    email = Column(String, unique=True, nullable=False)
    telegram_id = Column(Integer, unique=True, nullable=False)

    transactions = relationship(
        "Transaction", back_populates="client", foreign_keys="[Transaction.client_id]"
    )
    loans = relationship(
        "Loan", back_populates="client", foreign_keys="[Loan.client_id]"
    )
    cards = relationship(
        "Card", back_populates="client", foreign_keys="[Card.client_id]"
    )

    def __repr__(self):
        return f"<Client(id={self.id}, username={self.first_name, self.last_name, self.patronymic}, email={self.email})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(
        String, nullable=False
    )  # 'deposit', 'withdraw', 'transfer'
    recipient_id = Column(Integer, ForeignKey("clients.id"))

    client = relationship(
        "Client", back_populates="transactions", foreign_keys=[client_id]
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, type={self.transaction_type})>"


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Float, nullable=False)
    interest_rate = Column(Float, nullable=False)
    status = Column(String, default="active")  # 'active', 'paid'
    due_date = Column(Date, default=None)

    client = relationship("Client", back_populates="loans", foreign_keys=[client_id])

    def __repr__(self):
        return f"<Loan(id={self.id}, amount={self.amount}, status={self.status})>"


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    card_number = Column(String, unique=True, nullable=False)
    expiration_date = Column(Date, nullable=False)  # YYYY-MM-DD
    status = Column(String, default="active")  # 'active', 'frozen', 'blocked'
    balance = Column(Float, default=0.0, nullable=False)

    client = relationship("Client", back_populates="cards", foreign_keys=[client_id])

    def __repr__(self):
        return f"<Card(id={self.id}, card_number={self.card_number}, status={self.status})>"
