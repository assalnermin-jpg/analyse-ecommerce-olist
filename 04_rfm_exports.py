import sqlite3
from pathlib import Path
import pandas as pd

conn = sqlite3.connect("olist.db")
Path("exports").mkdir(exist_ok=True)

# ---------------------------------------------------------------
# 1. Table "commandes" : une ligne par commande livrée
# ---------------------------------------------------------------
commandes = pd.read_sql("""
    SELECT
        o.order_id,
        c.customer_unique_id,
        c.customer_state                              AS etat_client,
        date(o.order_purchase_timestamp)              AS date_achat,
        strftime('%Y-%m', o.order_purchase_timestamp) AS mois,
        julianday(o.order_delivered_customer_date)
          - julianday(o.order_purchase_timestamp)     AS delai_jours,
        CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
             THEN 1 ELSE 0 END                        AS en_retard,
        it.montant,
        it.nb_articles,
        rv.note
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN (SELECT order_id,
                 SUM(price + freight_value) AS montant,
                 COUNT(*)                   AS nb_articles
          FROM order_items GROUP BY order_id) it ON o.order_id = it.order_id
    LEFT JOIN (SELECT order_id, AVG(review_score) AS note
               FROM order_reviews GROUP BY order_id) rv ON o.order_id = rv.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
""", conn)

# Exclure les mois incomplets (moins de 100 commandes) repérés au contrôle qualité
volumes = commandes.groupby("mois")["order_id"].transform("count")
commandes = commandes[volumes >= 100].copy()
commandes["delai_jours"] = commandes["delai_jours"].round(1)
commandes["montant"] = commandes["montant"].round(2)
print(f"Commandes livrées retenues : {len(commandes)}")

# ---------------------------------------------------------------
# 2. Table "ventes" : une ligne par article (pour l'analyse par catégorie)
# ---------------------------------------------------------------
ventes = pd.read_sql("""
    SELECT
        i.order_id,
        strftime('%Y-%m', o.order_purchase_timestamp) AS mois,
        COALESCE(t.product_category_name_english,
                 p.product_category_name, 'inconnue') AS categorie,
        i.price                                       AS prix,
        i.freight_value                               AS frais_port,
        s.seller_state                                AS etat_vendeur
    FROM order_items i
    JOIN orders o   ON i.order_id = o.order_id
    JOIN products p ON i.product_id = p.product_id
    JOIN sellers s  ON i.seller_id = s.seller_id
    LEFT JOIN product_category_name_translation t
           ON p.product_category_name = t.product_category_name
    WHERE o.order_status = 'delivered'
""", conn)
ventes = ventes[ventes["order_id"].isin(commandes["order_id"])]
print(f"Articles vendus retenus : {len(ventes)}")

# ---------------------------------------------------------------
# 3. Segmentation RFM : une ligne par client
# ---------------------------------------------------------------
commandes["date_achat"] = pd.to_datetime(commandes["date_achat"])
date_reference = commandes["date_achat"].max() + pd.Timedelta(days=1)

rfm = commandes.groupby("customer_unique_id").agg(
    recence=("date_achat", lambda d: (date_reference - d.max()).days),
    frequence=("order_id", "count"),
    montant=("montant", "sum"),
).reset_index()

# Scores de 1 (faible) à 4 (fort) par quartiles
rfm["score_R"] = pd.qcut(rfm["recence"], 4, labels=[4, 3, 2, 1]).astype(int)  # récent = 4
rfm["score_M"] = pd.qcut(rfm["montant"], 4, labels=[1, 2, 3, 4]).astype(int)


def segment(ligne):
    recent = ligne["score_R"] >= 3
    fidele = ligne["frequence"] >= 2
    gros_panier = ligne["score_M"] >= 3
    if fidele and recent:
        return "Clients fidèles"
    if fidele:
        return "Fidèles à réactiver"
    if recent and gros_panier:
        return "Nouveaux à fort potentiel"
    if recent:
        return "Nouveaux clients"
    if gros_panier:
        return "À risque (gros paniers)"
    return "Perdus"


rfm["segment"] = rfm.apply(segment, axis=1)
rfm["montant"] = rfm["montant"].round(2)

# Résumé des segments
resume = rfm.groupby("segment").agg(
    nb_clients=("customer_unique_id", "count"),
    recence_moy=("recence", "mean"),
    montant_moy=("montant", "mean"),
).round(1).sort_values("nb_clients", ascending=False)
resume["part_pct"] = (resume["nb_clients"] / len(rfm) * 100).round(1)

print(f"\nClients uniques : {len(rfm)}")
print(f"Clients ayant commandé une seule fois : "
      f"{(rfm['frequence'] == 1).mean() * 100:.1f} %")
print("\n=== Segments RFM ===")
print(resume.to_string())

# ---------------------------------------------------------------
# 4. Exports pour Power BI
# ---------------------------------------------------------------
commandes["date_achat"] = commandes["date_achat"].dt.date
commandes.to_csv("exports/commandes.csv", index=False)
ventes.to_csv("exports/ventes.csv", index=False)
rfm.to_csv("exports/rfm.csv", index=False)
print("\nExports : exports/commandes.csv, ventes.csv, rfm.csv (+ qualite.csv)")