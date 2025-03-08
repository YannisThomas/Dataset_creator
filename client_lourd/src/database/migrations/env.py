# src/database/migrations/env.py

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import des modèles pour les migrations automatiques
from src.database.db_manager_sqlalchemy import Base

# Ceci est l'objet Alembic Config, qui fournit
# l'accès à la configuration de l'exécution de la migration.
config = context.config

# Interprète le fichier config pour la configuration du logger Python.
fileConfig(config.config_file_name)

# Point d'entrée pour 'autogenerate'
target_metadata = Base.metadata

# Autres valeurs de l'envrironnement, définies par l'utilisateur.
# Ce peut être n'importe quoi.
# e.g. PYTHONPATH = ['/path/to/my/app', '/path/to/my/lib']
# target_metadata = mylib.MyModel.metadata


def run_migrations_offline():
    """
    Exécute les migrations en mode 'offline'.

    Cela configure le contexte avec juste une URL
    et pas un moteur, bien que l'Engine soit facultativement
    en jeu pour le cas où la configuration est
    une Engine (e.g., lorsque l'on invoque les migrations depuis
    l'application), il sera ignoré ici.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Exécute les migrations en mode 'online'.

    Dans ce scénario, on a besoin de créer un moteur
    et associer une connexion avec le contexte.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


# src/database/migrations/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}


# src/database/migrations/alembic.ini
# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = src/database/migrations

# template used to generate migration files
# file_template = %%(rev)s_%%(slug)s

# timezone to use when rendering the date
# within the migration file as well as the filename.
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .py files to be checked by the editor
# for Alembic command-line interface
# are you sure you want to use a string format here?
# sqlalchemy.url = driver://user:pass@localhost/dbname

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S


# src/database/migrations/versions/000001_initial_schema.py
"""Initial schema

Revision ID: 000001
Create Date: 2023-06-01

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Création des tables
    op.create_table(
        'datasets',
        sa.Column('name', sa.String(), nullable=False, primary_key=True),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('classes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True)
    )
    
    op.create_table(
        'images',
        sa.Column('id', sa.String(), nullable=False, primary_key=True),
        sa.Column('dataset_name', sa.String(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('modified_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_name'], ['datasets.name'], ondelete='CASCADE')
    )
    
    op.create_table(
        'annotations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('image_id', sa.String(), nullable=False),
        sa.Column('class_id', sa.Integer(), nullable=False),
        sa.Column('bbox_x', sa.Float(), nullable=False),
        sa.Column('bbox_y', sa.Float(), nullable=False),
        sa.Column('bbox_width', sa.Float(), nullable=False),
        sa.Column('bbox_height', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('type', sa.String(), nullable=False, default='bbox'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE')
    )
    
    op.create_table(
        'migrations',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=False, default=sa.func.now())
    )
    
    # Créer des index pour améliorer les performances
    op.create_index('idx_images_dataset', 'images', ['dataset_name'])
    op.create_index('idx_annotations_image', 'annotations', ['image_id'])
    
    # Enregistrer cette migration dans la table des migrations
    op.execute(
        """
        INSERT INTO migrations (version, description, applied_at)
        VALUES ('000001', 'Initial schema', CURRENT_TIMESTAMP)
        """
    )


def downgrade():
    # Suppression des tables en ordre inverse
    op.drop_table('migrations')
    op.drop_table('annotations')
    op.drop_table('images')
    op.drop_table('datasets')


# src/database/migrations/versions/000002_add_indexes.py
"""Add indexes for performance

Revision ID: 000002
Revises: 000001
Create Date: 2023-06-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '000002'
down_revision = '000001'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter des index pour améliorer les performances des requêtes
    op.create_index('idx_annotations_class', 'annotations', ['class_id'])
    op.create_index('idx_images_source', 'images', ['source'])
    
    # Enregistrer cette migration
    op.execute(
        """
        INSERT INTO migrations (version, description, applied_at)
        VALUES ('000002', 'Add indexes for performance', CURRENT_TIMESTAMP)
        """
    )


def downgrade():
    # Supprimer les index ajoutés
    op.drop_index('idx_annotations_class', table_name='annotations')
    op.drop_index('idx_images_source', table_name='images')


# src/database/migrations/versions/000003_add_stats_table.py
"""Add statistics table

Revision ID: 000003
Revises: 000002
Create Date: 2023-06-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '000003'
down_revision = '000002'
branch_labels = None
depends_on = None


def upgrade():
    # Ajouter une table pour les statistiques
    op.create_table(
        'dataset_stats',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True, autoincrement=True),
        sa.Column('dataset_name', sa.String(), nullable=False),
        sa.Column('stat_date', sa.Date(), nullable=False),
        sa.Column('image_count', sa.Integer(), nullable=False, default=0),
        sa.Column('annotation_count', sa.Integer(), nullable=False, default=0),
        sa.Column('class_distribution', sa.JSON(), nullable=True),
        sa.Column('avg_annotations_per_image', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_name'], ['datasets.name'], ondelete='CASCADE')
    )
    
    # Créer un index pour accélérer les recherches par date et dataset
    op.create_index('idx_stats_dataset_date', 'dataset_stats', ['dataset_name', 'stat_date'])
    
    # Enregistrer cette migration
    op.execute(
        """
        INSERT INTO migrations (version, description, applied_at)
        VALUES ('000003', 'Add statistics table', CURRENT_TIMESTAMP)
        """
    )


def downgrade():
    # Supprimer la table des statistiques
    op.drop_table('dataset_stats')