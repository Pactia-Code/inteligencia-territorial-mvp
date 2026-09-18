"""corridas de scoring append-only

El score se normaliza min-max dentro de la cohorte, así que **solo es
comparable contra los de su propia corrida**. Hasta aquí vivía como atributo de
`(ciclo, municipio)` con `uq_score_ciclo_municipio`, de modo que cualquier
recálculo pisaba el ranking anterior en su sitio: un informe publicado
empezaría a mostrar un orden distinto del que las gerencias calificaron, sin
forma de reconstruir el original. Eso rompe H4, que es bloqueante.

El score deja de ser un atributo del municipio y pasa a ser **un hecho de una
corrida**. Nada se sobrescribe.

Qué hace, en orden:

  1. Crea `corrida_scoring`.
  2. **Migra lo que ya existe** en vez de borrarlo: una corrida histórica por
     ciclo, con las dos listas de municipios reconstruidas del propio dato.
  3. Reapunta `score_municipio` a la corrida y le quita `id_ciclo`, que ahora
     es de la corrida: denormalizarlo permitiría que una fila discrepara de su
     propia corrida.
  4. Le da a `informe` su `id_corrida` y el `CheckConstraint` que a `estado`
     le faltaba.

Sobre las corridas históricas: se marcan `v1+migrado` y con `pesos` vacíos
porque **esas corridas no registraron su versión ni sus pesos** — el campo no
existía. Inventarlos sería peor que dejarlos vacíos: daría una falsa sensación
de auditabilidad sobre datos que no la tienen.

`fecha_corte_cohorte` queda en NULL por lo mismo. A partir de la primera
corrida nueva se computa **solo con SECOP II**, que es de donde salen F1, F2 y
F3, y sobre los municipios **que tienen fecha**: `municipios_sin_fecha` recoge
los que no la tienen, para que la incertidumbre quede declarada en vez de
aniquilar el campo. `corte_por_fuente` guarda el corte de cada fuente aparte.

Revision ID: 41d077a78426
Revises: 5ae7d724433d
Create Date: 2026-09-18 11:13:00.000000

"""

from collections.abc import Sequence
from datetime import UTC, date, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '41d077a78426'
down_revision: str | Sequence[str] | None = '5ae7d724433d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERSION_MIGRADA = "v1+migrado"


def _a_fecha(valor) -> date | None:
    """SQLite devuelve las fechas como texto en una consulta cruda.

    PostgreSQL las devuelve ya como `date`, así que hay que aceptar ambas: una
    migración que solo funcione en el motor local no sirve de nada (D8).
    """
    if valor is None or isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def _tabla_corrida() -> sa.TableClause:
    return sa.table(
        "corrida_scoring",
        sa.column("id_ciclo", sa.Integer),
        sa.column("fecha_corrida", sa.DateTime),
        sa.column("tipo_corrida", sa.String),
        sa.column("ventana_desde", sa.Date),
        sa.column("ventana_hasta", sa.Date),
        sa.column("fecha_corte_cohorte", sa.Date),
        sa.column("municipios_sin_fecha", sa.JSON),
        sa.column("corte_por_fuente", sa.JSON),
        sa.column("municipios_objetivo", sa.JSON),
        sa.column("municipios_en_cohorte", sa.JSON),
        sa.column("version_scoring", sa.String),
        sa.column("pesos", sa.JSON),
    )


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'corrida_scoring',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('id_ciclo', sa.Integer(), nullable=False),
        sa.Column('fecha_corrida', sa.DateTime(timezone=True), nullable=False),
        sa.Column('tipo_corrida', sa.String(length=10), nullable=False),
        sa.Column('ventana_desde', sa.Date(), nullable=True),
        sa.Column('ventana_hasta', sa.Date(), nullable=True),
        sa.Column('fecha_corte_cohorte', sa.Date(), nullable=True),
        sa.Column('municipios_sin_fecha', sa.JSON(), nullable=False),
        sa.Column('corte_por_fuente', sa.JSON(), nullable=False),
        sa.Column('municipios_objetivo', sa.JSON(), nullable=False),
        sa.Column('municipios_en_cohorte', sa.JSON(), nullable=False),
        sa.Column('version_scoring', sa.String(length=40), nullable=True),
        sa.Column('pesos', sa.JSON(), nullable=False),
        sa.CheckConstraint("tipo_corrida IN ('completa', 'parcial')", name='ck_tipo_corrida'),
        sa.ForeignKeyConstraint(['id_ciclo'], ['ciclo.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('corrida_scoring', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_corrida_scoring_id_ciclo'), ['id_ciclo'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_corrida_scoring_tipo_corrida'), ['tipo_corrida'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_corrida_scoring_version_scoring'), ['version_scoring'], unique=False
        )

    # --- Migración de los scores existentes a corridas históricas ---
    conexion = op.get_bind()
    objetivo = [
        d for (d,) in conexion.execute(
            sa.text("SELECT divipola FROM municipio ORDER BY divipola")
        )
    ]
    ciclos = conexion.execute(
        sa.text(
            "SELECT s.id_ciclo, c.fecha_desde, c.fecha_hasta "
            "FROM (SELECT DISTINCT id_ciclo FROM score_municipio) s "
            "JOIN ciclo c ON c.id = s.id_ciclo ORDER BY s.id_ciclo"
        )
    ).all()

    filas = []
    for id_ciclo, desde, hasta in ciclos:
        cohorte = [
            d for (d,) in conexion.execute(
                sa.text(
                    "SELECT divipola FROM score_municipio "
                    "WHERE id_ciclo = :c ORDER BY divipola"
                ),
                {"c": id_ciclo},
            )
        ]
        filas.append(
            {
                "id_ciclo": id_ciclo,
                "fecha_corrida": datetime.now(UTC),
                # Se calcula, no se afirma: comparar las dos listas es lo que
                # hace que la marca sea reverificable más adelante.
                "tipo_corrida": "completa" if set(cohorte) >= set(objetivo) else "parcial",
                "ventana_desde": _a_fecha(desde),
                "ventana_hasta": _a_fecha(hasta),
                "fecha_corte_cohorte": None,
                "municipios_sin_fecha": [],
                "corte_por_fuente": {},
                "municipios_objetivo": objetivo,
                "municipios_en_cohorte": cohorte,
                "version_scoring": VERSION_MIGRADA,
                "pesos": {},
            }
        )
    if filas:
        op.bulk_insert(_tabla_corrida(), filas)

    # --- score_municipio: nullable, rellenar, y solo entonces exigir ---
    op.add_column('score_municipio', sa.Column('id_corrida', sa.Integer(), nullable=True))
    op.add_column('score_municipio', sa.Column('ultima_fecha_captura', sa.Date(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE score_municipio SET id_corrida = ("
            "  SELECT c.id FROM corrida_scoring c WHERE c.id_ciclo = score_municipio.id_ciclo"
            ")"
        )
    )

    with op.batch_alter_table('score_municipio', schema=None) as batch_op:
        batch_op.alter_column('id_corrida', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_index(batch_op.f('ix_score_municipio_id_ciclo'))
        batch_op.drop_constraint('uq_score_ciclo_municipio', type_='unique')
        batch_op.create_index(
            batch_op.f('ix_score_municipio_id_corrida'), ['id_corrida'], unique=False
        )
        batch_op.create_unique_constraint(
            'uq_score_corrida_municipio', ['id_corrida', 'divipola']
        )
        batch_op.create_foreign_key(
            'fk_score_corrida', 'corrida_scoring', ['id_corrida'], ['id']
        )
        # Al soltar la columna se va con ella su clave foránea a `ciclo`, así
        # que no hace falta drop_constraint sobre una restricción sin nombre.
        batch_op.drop_column('id_ciclo')

    # --- informe: la corrida que lo sustenta, y el dominio de `estado` ---
    with op.batch_alter_table('informe', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id_corrida', sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_informe_id_corrida'), ['id_corrida'], unique=False
        )
        batch_op.create_foreign_key(
            'fk_informe_corrida', 'corrida_scoring', ['id_corrida'], ['id']
        )
        # Autogenerate no detecta CheckConstraint sobre tabla existente.
        batch_op.create_check_constraint(
            'ck_estado_informe', "estado IN ('publicado', 'archivado')"
        )


def downgrade() -> None:
    """Downgrade schema.

    Reconstruye `score_municipio.id_ciclo` desde la corrida antes de soltarla,
    para no perder a qué ciclo pertenecía cada fila. Lo que sí se pierde es el
    historial: al volver a `uq_score_ciclo_municipio` solo cabe una fila por
    (ciclo, municipio), así que **si hay más de una corrida por ciclo, bajar de
    versión falla** en vez de elegir una en silencio.
    """
    with op.batch_alter_table('informe', schema=None) as batch_op:
        batch_op.drop_constraint('ck_estado_informe', type_='check')
        batch_op.drop_constraint('fk_informe_corrida', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_informe_id_corrida'))
        batch_op.drop_column('id_corrida')

    op.add_column('score_municipio', sa.Column('id_ciclo', sa.INTEGER(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE score_municipio SET id_ciclo = ("
            "  SELECT c.id_ciclo FROM corrida_scoring c WHERE c.id = score_municipio.id_corrida"
            ")"
        )
    )

    with op.batch_alter_table('score_municipio', schema=None) as batch_op:
        batch_op.alter_column('id_ciclo', existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_constraint('fk_score_corrida', type_='foreignkey')
        batch_op.drop_constraint('uq_score_corrida_municipio', type_='unique')
        batch_op.drop_index(batch_op.f('ix_score_municipio_id_corrida'))
        batch_op.create_unique_constraint(
            'uq_score_ciclo_municipio', ['id_ciclo', 'divipola']
        )
        batch_op.create_index(
            batch_op.f('ix_score_municipio_id_ciclo'), ['id_ciclo'], unique=False
        )
        batch_op.create_foreign_key('fk_score_ciclo', 'ciclo', ['id_ciclo'], ['id'])
        batch_op.drop_column('ultima_fecha_captura')
        batch_op.drop_column('id_corrida')

    with op.batch_alter_table('corrida_scoring', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_corrida_scoring_version_scoring'))
        batch_op.drop_index(batch_op.f('ix_corrida_scoring_tipo_corrida'))
        batch_op.drop_index(batch_op.f('ix_corrida_scoring_id_ciclo'))
    op.drop_table('corrida_scoring')
