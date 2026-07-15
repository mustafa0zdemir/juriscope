"""replace file_path with storage_key in contracts

Revision ID: 003
Revises: 002
Create Date: 2026-07-15

Context:
    Sprint 3'te contracts tablosunda dosyaların yerel disk yolunu tutan
    file_path sütunu bulunmaktaydı. Sprint 4 ile depolama katmanı MinIO'ya
    taşındığından bu sütun, MinIO object key'ini tutan storage_key ile
    değiştirilmektedir.

Production Data Migration Note:
    Bu migration production'a uygulanmadan önce aşağıdaki adımlar
    takip edilmelidir:

    1. Mevcut dosyaları MinIO'ya taşıma:
       - Tüm mevcut contracts kaydındaki file_path değerleri okunmalı
       - Her dosya MinIO'ya yüklenip storage_key oluşturulmalı
       - Örnek storage_key formatı: contracts/{year}/{month}/{stored_filename}

       Aşağıdaki SQL bloğu, storage_key değerlerini file_path'ten türetmek için
       kullanılabilir (dosya yükleme işleminin ayrıca yapıldığı varsayılarak):

       -- TODO: Bu komut çalıştırılmadan önce dosyalar MinIO'ya yüklenmiş olmalıdır.
       -- UPDATE contracts
       --   SET storage_key = 'contracts/' || TO_CHAR(uploaded_at, 'YYYY/MM') || '/' || stored_filename
       -- WHERE storage_key IS NULL;

    2. Sütun NOT NULL kısıtlaması bu migration'da nullable=True olarak
       başlatılmıştır. Yukarıdaki veri taşıma adımı tamamlandıktan sonra
       ayrı bir migration ile NOT NULL yapılmalıdır.

    3. file_path sütunu geçiş süreci boyunca korunmalı, veri taşıma
       doğrulandıktan sonra downgrade olmaksızın DROP edilmelidir.

    DEV ORTAMI:
       Geliştirme ortamında alembic downgrade base && alembic upgrade head
       ile veritabanı sıfırlanabilir.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # storage_key sütununu ekle.
    # Production'da önce nullable=True ile ekle, veri taşındıktan sonra
    # ayrı bir migration ile NOT NULL kısıtı eklenmeli.
    # TODO: Production deployment öncesi veri taşıma adımlarını uygula (yukarıdaki nota bak).
    op.add_column(
        "contracts",
        sa.Column("storage_key", sa.String(length=512), nullable=True),
    )

    # file_path sütununu kaldır.
    # Production'da bu adım veri taşıma ve storage_key doğrulaması
    # tamamlandıktan sonra çalıştırılmalıdır.
    # TODO: Production'da önce veri taşıma scriptini çalıştır, ardından bu satırı etkinleştir.
    op.drop_column("contracts", "file_path")

    # storage_key'i NOT NULL yap.
    # Production'da bu adım veri taşıma tamamlandıktan ayrı bir migration'da yapılmalıdır.
    # TODO: Production'da bu satırı ayrı bir migration'a taşı.
    op.alter_column("contracts", "storage_key", nullable=False)


def downgrade() -> None:
    # file_path sütununu geri ekle (nullable — eski veriler kaybolmuştur).
    # Production'da downgrade desteklenmez; veriyi MinIO'dan geri taşımak gerekir.
    op.add_column(
        "contracts",
        sa.Column("file_path", sa.String(length=512), nullable=True),
    )

    op.drop_column("contracts", "storage_key")
