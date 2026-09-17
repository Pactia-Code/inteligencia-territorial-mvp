"""linaje de origen y consolidacion en insight

Cinco columnas para que un insight diga quién lo produjo y, si es un
consolidado del Correlacionador, de qué insights salió. `ids_insight_origen`
es la trazabilidad de CA-M4.4 en la base: sin ella, un consolidado no se puede
deshacer hasta sus orígenes y el linaje se rompe al salir de memoria.

Dos cosas que autogenerate no hizo y se añadieron a mano:

  · **Las CheckConstraint.** Alembic no las detecta sobre una tabla existente.
    Sin `ck_origen_insight` y `ck_confianza`, el modelo declara un dominio que
    la base no aplica, y la divergencia no se nota hasta que alguien escribe
    un valor inválido por SQL.
  · **Los server_default de las columnas NOT NULL.** Hoy `insight` está vacía
    y la migración pasaría igual, pero en cuanto haya filas —y el objetivo de
    este trabajo es justamente que las haya— un NOT NULL sin default falla.
    Una migración que solo funciona sobre una tabla vacía es una trampa.

Revision ID: 5ae7d724433d
Revises: 949a8ff9e15d
Create Date: 2026-09-17 16:00:26.079797

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5ae7d724433d'
down_revision: str | Sequence[str] | None = '949a8ff9e15d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('insight', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'origen',
                sa.String(length=20),
                nullable=False,
                server_default='clasificador',
            )
        )
        batch_op.add_column(sa.Column('version_prompt', sa.String(length=20), nullable=True))
        batch_op.add_column(
            sa.Column(
                'ids_insight_origen',
                sa.JSON(),
                nullable=False,
                server_default='[]',
            )
        )
        batch_op.add_column(sa.Column('por_que_convergen', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('confianza', sa.String(length=10), nullable=True))
        batch_op.create_index(batch_op.f('ix_insight_origen'), ['origen'], unique=False)
        batch_op.create_check_constraint(
            'ck_origen_insight',
            "origen IN ('clasificador', 'correlacionador')",
        )
        batch_op.create_check_constraint(
            'ck_confianza',
            "confianza IS NULL OR confianza IN ('alta', 'media', 'baja')",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('insight', schema=None) as batch_op:
        batch_op.drop_constraint('ck_confianza', type_='check')
        batch_op.drop_constraint('ck_origen_insight', type_='check')
        batch_op.drop_index(batch_op.f('ix_insight_origen'))
        batch_op.drop_column('confianza')
        batch_op.drop_column('por_que_convergen')
        batch_op.drop_column('ids_insight_origen')
        batch_op.drop_column('version_prompt')
        batch_op.drop_column('origen')
