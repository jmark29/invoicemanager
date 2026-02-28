from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # singleton, always 1
    company_name: Mapped[str] = mapped_column(String, default="29ventures GmbH")
    address_line1: Mapped[str] = mapped_column(String, default="Kleiststraße 23")
    address_line2: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    zip_city: Mapped[str] = mapped_column(String, default="65187 Wiesbaden")
    managing_director: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="Jan Markmann"
    )
    tax_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    vat_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="DE294406946"
    )
    bank_name: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="Commerzbank Düsseldorf"
    )
    iban: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="DE51 3004 0000 0122 0029 00"
    )
    bic: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="COBADEDDXXX"
    )
    email: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="info@29ventures.com"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="(0611) 945 897 -80"
    )
    fax: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="(0611) 945 897 -81"
    )
    website: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="www.29ventures.com"
    )
    register_info: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, default="Handelsregister: 32062, AG Wiesbaden"
    )
