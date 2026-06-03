from datetime import date
from pathlib import Path

from sqlalchemy import Column, Date, Integer, MetaData, String, Table, create_engine, func, select


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "dashboard.db"
TABLE_NAME = "suivi_dpi_sites"


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}")
    metadata = MetaData()

    records = Table(
        TABLE_NAME,
        metadata,
        Column("id", Integer, primary_key=True),
        Column("etablissement_sanitaire", String(160), nullable=False),
        Column("region_sanitaire", String(80), nullable=False),
        Column("district_sanitaire", String(100), nullable=False),
        Column("type_etablissement", String(100), nullable=False),
        Column("bailleur", String(80), nullable=False),
        Column("statut_deploiement", String(60), nullable=False),
        Column("date_deploiement", Date),
        Column("statut_operationnel", String(80), nullable=False),
        Column("motif_principal", String(160)),
        Column("point_focal", String(120)),
        Column("observation", String(255)),
        Column("date_modification", Date, nullable=False),
        Column("date_import", Date, nullable=False),
    )

    metadata.create_all(engine)

    sample_rows = [
        {
            "id": 1,
            "etablissement_sanitaire": "HG Abobo",
            "region_sanitaire": "Abidjan 1",
            "district_sanitaire": "Abobo Est",
            "type_etablissement": "HG Public",
            "bailleur": "Etat",
            "statut_deploiement": "Déployé",
            "date_deploiement": date(2026, 1, 8),
            "statut_operationnel": "Fonctionnel",
            "motif_principal": "",
            "point_focal": "Equipe DPI",
            "observation": "Site pilote opérationnel.",
            "date_modification": date(2026, 5, 18),
            "date_import": date(2026, 5, 18),
        },
        {
            "id": 2,
            "etablissement_sanitaire": "ESPC Marcory",
            "region_sanitaire": "Abidjan 2",
            "district_sanitaire": "Marcory",
            "type_etablissement": "ESPC",
            "bailleur": "Banque mondiale",
            "statut_deploiement": "Déployé",
            "date_deploiement": date(2026, 2, 14),
            "statut_operationnel": "Partiellement fonctionnel",
            "motif_principal": "Connectivité instable",
            "point_focal": "Equipe district",
            "observation": "Suivi technique en cours.",
            "date_modification": date(2026, 5, 22),
            "date_import": date(2026, 5, 22),
        },
        {
            "id": 3,
            "etablissement_sanitaire": "CHR Bouaké",
            "region_sanitaire": "Gbêkê",
            "district_sanitaire": "Bouaké Nord-Ouest",
            "type_etablissement": "CHR Public",
            "bailleur": "AFD",
            "statut_deploiement": "En cours",
            "date_deploiement": None,
            "statut_operationnel": "Non fonctionnel",
            "motif_principal": "Formation complémentaire requise",
            "point_focal": "Direction régionale",
            "observation": "Déploiement planifié.",
            "date_modification": date(2026, 5, 20),
            "date_import": date(2026, 5, 20),
        },
        {
            "id": 4,
            "etablissement_sanitaire": "ESPC Daloa Centre",
            "region_sanitaire": "Haut-Sassandra",
            "district_sanitaire": "Daloa",
            "type_etablissement": "ESPC",
            "bailleur": "UNICEF",
            "statut_deploiement": "Non démarré",
            "date_deploiement": None,
            "statut_operationnel": "Non fonctionnel",
            "motif_principal": "Matériel non livré",
            "point_focal": "Equipe logistique",
            "observation": "Approvisionnement attendu.",
            "date_modification": date(2026, 5, 24),
            "date_import": date(2026, 5, 24),
        },
        {
            "id": 5,
            "etablissement_sanitaire": "HG San-Pédro",
            "region_sanitaire": "San-Pédro",
            "district_sanitaire": "San-Pédro",
            "type_etablissement": "HG Public",
            "bailleur": "Etat",
            "statut_deploiement": "Déployé",
            "date_deploiement": date(2026, 3, 4),
            "statut_operationnel": "Fonctionnel",
            "motif_principal": "",
            "point_focal": "Equipe DPI",
            "observation": "Utilisation régulière.",
            "date_modification": date(2026, 5, 25),
            "date_import": date(2026, 5, 25),
        },
        {
            "id": 6,
            "etablissement_sanitaire": "ESPC Man",
            "region_sanitaire": "Tonkpi",
            "district_sanitaire": "Man",
            "type_etablissement": "ESPC",
            "bailleur": "GIZ",
            "statut_deploiement": "Déployé",
            "date_deploiement": date(2026, 4, 12),
            "statut_operationnel": "Non fonctionnel",
            "motif_principal": "Maintenance serveur",
            "point_focal": "Support informatique",
            "observation": "Ticket ouvert.",
            "date_modification": date(2026, 5, 26),
            "date_import": date(2026, 5, 26),
        },
    ]

    with engine.begin() as connection:
        existing_count = connection.execute(select(func.count()).select_from(records)).scalar_one()
        if existing_count == 0:
            connection.execute(records.insert(), sample_rows)

    print(f"Sample database ready: {DB_PATH}")
    print(f"Sample table ready: {TABLE_NAME}")


if __name__ == "__main__":
    main()
