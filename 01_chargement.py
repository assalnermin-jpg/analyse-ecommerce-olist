import sqlite3
from pathlib import Path
import pandas as pd

DOSSIER_DATA = Path(__file__).parent / "data"
BASE = Path(__file__).parent / "olist.db"

def nom_table(fichier):
    nom = fichier.stem
    nom = nom.removeprefix("olist_").removesuffix("_dataset")
    return nom

fichiers = sorted(DOSSIER_DATA.glob("*.csv"))
if not fichiers:
    print("Aucun CSV trouvé dans le dossier data/")
else:
    with sqlite3.connect(BASE) as conn:
        for f in fichiers:
            df = pd.read_csv(f)
            table = nom_table(f)
            df.to_sql(table, conn, if_exists="replace", index=False)
            print(f"{table:<35} {len(df):>8} lignes  {df.shape[1]:>3} colonnes")
    print("Base créée :", BASE)
