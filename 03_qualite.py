import sqlite3
from pathlib import Path
import pandas as pd

conn = sqlite3.connect("olist.db")
Path("exports").mkdir(exist_ok=True)

def compter(requete):
    """Exécute une requête SQL qui renvoie un seul nombre."""
    return conn.execute(requete).fetchone()[0]

# 1. Valeurs manquantes par table
print("=== Valeurs manquantes ===")
tables = ["orders", "order_items", "order_payments", "order_reviews",
          "products", "customers", "sellers"]
for t in tables:
    df = pd.read_sql(f"SELECT * FROM {t}", conn)
    manquants = df.isna().sum()
    manquants = manquants[manquants > 0]
    if len(manquants) > 0:
        print(f"\n{t} ({len(df)} lignes) :")
        print(manquants.to_string())

# 2. Contrôles de cohérence
controles = [
    ("Commandes sans aucun article",
     "SELECT COUNT(*) FROM orders WHERE order_id NOT IN (SELECT order_id FROM order_items)",
     "Exclues des analyses de CA"),
    ("Doublons d'identifiant de commande",
     "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM orders",
     "Aucune action si 0"),
    ("Commandes 'delivered' sans date de livraison",
     "SELECT COUNT(*) FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL",
     "Exclues des calculs de délai"),
    ("Livraison enregistrée avant l'achat",
     "SELECT COUNT(*) FROM orders WHERE order_delivered_customer_date < order_purchase_timestamp",
     "Exclues des calculs de délai"),
    ("Paiements de type 'not_defined'",
     "SELECT COUNT(*) FROM order_payments WHERE payment_type = 'not_defined'",
     "Exclus de l'analyse des paiements"),
    ("Produits sans catégorie",
     "SELECT COUNT(*) FROM products WHERE product_category_name IS NULL",
     "Regroupés en catégorie 'inconnue'"),
    ("Articles avec un prix nul ou négatif",
     "SELECT COUNT(*) FROM order_items WHERE price <= 0",
     "Aucune action si 0"),
    ("Commandes avec plusieurs avis",
     "SELECT COUNT(*) FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1)",
     "Risque de double comptage dans les jointures"),
    ("Mois incomplets (moins de 100 commandes)",
     "SELECT COUNT(*) FROM (SELECT strftime('%Y-%m', order_purchase_timestamp) m FROM orders GROUP BY m HAVING COUNT(*) < 100)",
     "Exclus des analyses de tendance"),
]

resultats = []
for nom, requete, decision in controles:
    resultats.append({"controle": nom, "nb_lignes": compter(requete), "decision": decision})

qualite = pd.DataFrame(resultats)
print("\n=== Contrôles de cohérence ===")
print(qualite.to_string(index=False))

qualite.to_csv("exports/qualite.csv", index=False)
print("\nExport : exports/qualite.csv")