"""corridas de agentes append-only

El hermano de `41d077a78426` un nivel más abajo. Los insights vivían como
atributo de `(ciclo, municipio, origen)` y `_borrar_previos` **borraba** la
primera pasada al correr la segunda, así que dos pasadas del mismo ciclo no
podían compararse — que es justo lo que el pendiente A6 necesita medir.

La segunda cara es peor: `calificacion.id_insight` apunta a `insight.id`.
Mientras no hubiera calificaciones no mordía, pero desde que exista M7 un
reproceso habría borrado los insights que las gerencias calificaron. Es el
mismo agujero de H4 que se cerró para el ranking, esperando a la semana 7.

Qué hace, en orden:

  1. Crea `corrida_agentes`.
  2. **Migra lo que ya existe**: una corrida histórica por ciclo con insights,
     con las dos listas de municipios reconstruidas del propio dato y las
     versiones de prompt leídas de las filas, no inventadas.
  3. Reapunta `insight` a la corrida y le quita `id_ciclo`, que ahora es de la
     corrida: denormalizarlo permitiría que una fila discrepara de su pasada.

Las corridas migradas salen **parciales**, y es correcto: el ciclo 1 solo tiene
insights de Carepa y Chigorodó, el ciclo 2 solo de Barranquilla. Nunca se corrió
un ciclo entero. La guarda se ejercita desde el primer día.

Revision ID: cb034d1c967b
Revises: 41d077a78426
Create Date: 2026-09-18 13:10:00.000000

"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'cb034d1c967b'
down_revision: str | Sequence[str] | None = '41d077a78426'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tabla_corrida() -> sa.TableClause:
    return sa.table(
        "corrida_agentes",
        sa.column("id_ciclo", sa.Integer),
        sa.column("fecha_corrida", sa.DateTime),
        sa.column("tipo_corrida", sa.String),
        sa.column("municipios_objetivo", sa.JSON),
        sa.column("municipios_en_cohorte", sa.JSON),
        sa.column("version_clasificador", sa.String),
        sa.column("version_correlacionador", sa.String),
        sa.column("senales_procesadas", sa.Integer),
        sa.column("tokens_entrada", sa.Integer),
        sa.column("tokens_salida", sa.Integer),
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'corrida_agentes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_ciclo', sa.Integer(), nullable=False),
        sa.Column('fecha_corrida', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tipo_corrida', sa.String(length=10), nullable=False),
        sa.Column('municipios_objetivo', sa.JSON(), nullable=False),
        sa.Column('municipios_en_cohorte', sa.JSON(), nullable=False),
        sa.Column('version_clasificador', sa.String(length=20), nullable=True),
        sa.Column('version_correlacionador', sa.String(length=20), nullable=True),
        sa.Column('senales_procesadas', sa.Integer(), nullable=False),
        sa.Column('tokens_entrada', sa.Integer(), nullable=False),
        sa.Column('tokens_salida', sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "tipo_corrida IN ('completa', 'parcial')", name='ck_tipo_corrida_agentes'
        ),
        sa.ForeignKeyConstraint(['id_ciclo'], ['ciclo.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('corrida_agentes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_corrida_agentes_id_ciclo'), ['id_ciclo'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_corrida_agentes_tipo_corrida'), ['tipo_corrida'], unique=False
        )

    # --- Una corrida histórica por ciclo con insights ---
    conexion = op.get_bind()
    objetivo = [
        d for (d,) in conexion.execute(
            sa.text("SELECT divipola FROM municipio ORDER BY divipola")
        )
    ]
    ciclos = [
        c for (c,) in conexion.execute(
            sa.text("SELECT DISTINCT id_ciclo FROM insight ORDER BY id_ciclo")
        )
    ]

    filas = []
    for id_ciclo in ciclos:
        cohorte = [
            d for (d,) in conexion.execute(
                sa.text(
                    "SELECT DISTINCT divipola FROM insight "
                    "WHERE id_ciclo = :c ORDER BY divipola"
                ),
                {"c": id_ciclo},
            )
        ]
        # Las versiones se leen de las propias filas, no se inventan.
        versiones = dict(
            conexion.execute(
                sa.text(
                    "SELECT origen, MAX(version_prompt) FROM insight "
                    "WHERE id_ciclo = :c GROUP BY origen"
                ),
                {"c": id_ciclo},
            ).all()
        )
        filas.append(
            {
                "id_ciclo": id_ciclo,
                "fecha_corrida": datetime.now(UTC),
                "tipo_corrida": "completa" if set(cohorte) >= set(objetivo) else "parcial",
                "municipios_objetivo": objetivo,
                "municipios_en_cohorte": cohorte,
                "version_clasificador": versiones.get("clasificador"),
                "version_correlacionador": versiones.get("correlacionador"),
                # No se registraron en su momento; cero es «no se sabe», y
                # inventar un número daría falsa sensación de auditabilidad.
                "senales_procesadas": 0,
                "tokens_entrada": 0,
                "tokens_salida": 0,
            }
        )
    if filas:
        op.bulk_insert(_tabla_corrida(), filas)

    # --- insight: nullable, rellenar, y solo entonces exigir ---
    op.add_column('insight', sa.Column('id_corrida', sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE insight SET id_corrida = ("
            "  SELECT c.id FROM corrida_agentes c WHERE c.id_ciclo = insight.id_ciclo"
            ")"
        )
    )

    with op.batch_alter_table('insight', schema=None) as batch_op:
        batch_op.alter_column('id_corrida', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_index(batch_op.f('ix_insight_id_ciclo'))
        batch_op.create_index(
            batch_op.f('ix_insight_id_corrida'), ['id_corrida'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_insight_corrida', 'corrida_agentes', ['id_corrida'], ['id']
        )
        # Al soltar la columna se va con ella su clave foránea a `ciclo`.
        batch_op.drop_column('id_ciclo')


def downgrade() -> None:
    """Downgrade schema.

    Reconstruye `insight.id_ciclo` desde la corrida antes de soltarla. Lo que se
    pierde es la separación entre pasadas: al volver atrás, dos pasadas del
    mismo ciclo quedan indistinguibles. No falla —no hay restricción de unicidad
    que lo impida— pero deja de haber forma de saber cuál insight vino de cuál.
    """
    op.add_column('insight', sa.Column('id_ciclo', sa.INTEGER(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE insight SET id_ciclo = ("
            "  SELECT c.id_ciclo FROM corrida_agentes c WHERE c.id = insight.id_corrida"
            ")"
        )
    )

    with op.batch_alter_table('insight', schema=None) as batch_op:
        batch_op.alter_column('id_ciclo', existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_constraint('fk_insight_corrida', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_insight_id_corrida'))
        batch_op.create_index(batch_op.f('ix_insight_id_ciclo'), ['id_ciclo'], unique=False)
        batch_op.create_foreign_key('fk_insight_ciclo', 'ciclo', ['id_ciclo'], ['id'])
        batch_op.drop_column('id_corrida')

    with op.batch_alter_table('corrida_agentes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_corrida_agentes_tipo_corrida'))
        batch_op.drop_index(batch_op.f('ix_corrida_agentes_id_ciclo'))
    op.drop_table('corrida_agentes')
