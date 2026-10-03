-- database: ./olist.db

-- Use the ▷ button in the top right corner to run the entire file.

SELECT * FROM orders LIMIT 5;
-- Q1. Commandes et chiffre d'affaires par mois
SELECT
    strftime('%Y-%m', o.order_purchase_timestamp) AS mois,
    COUNT(DISTINCT o.order_id)                     AS nb_commandes,
    ROUND(SUM(i.price), 0)                         AS chiffre_affaires
FROM orders o
JOIN order_items i ON o.order_id = i.order_id
GROUP BY mois
ORDER BY mois;

-- Q2. Top 10 des catégories par chiffre d'affaires
SELECT
    COALESCE(t.product_category_name_english, p.product_category_name, 'inconnue') AS categorie,
    COUNT(DISTINCT i.order_id)                                       AS nb_commandes,
    ROUND(SUM(i.price), 0)                                           AS chiffre_affaires,
    ROUND(SUM(i.price) * 100.0 / (SELECT SUM(price) FROM order_items), 1) AS part_ca_pct
FROM order_items i
JOIN products p
    ON i.product_id = p.product_id
LEFT JOIN product_category_name_translation t
    ON p.product_category_name = t.product_category_name
GROUP BY categorie
ORDER BY chiffre_affaires DESC
LIMIT 10;

-- Q3. Panier moyen par commande
SELECT
    COUNT(*)                     AS nb_commandes,
    ROUND(AVG(montant), 2)       AS panier_moyen,
    ROUND(AVG(nb_articles), 2)   AS articles_par_commande,
    ROUND(AVG(frais_port), 2)    AS frais_port_moyens
FROM (
    SELECT
        order_id,
        SUM(price + freight_value) AS montant,
        COUNT(*)                   AS nb_articles,
        SUM(freight_value)         AS frais_port
    FROM order_items
    GROUP BY order_id
);

-- Q4. Répartition des moyens de paiement
SELECT
    payment_type                                                         AS moyen_paiement,
    COUNT(*)                                                             AS nb_paiements,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM order_payments), 1)   AS part_pct,
    ROUND(AVG(payment_installments), 1)                                  AS nb_versements_moyen,
    ROUND(AVG(payment_value), 2)                                         AS montant_moyen
FROM order_payments
GROUP BY payment_type
ORDER BY nb_paiements DESC;

-- Q5. Délai de livraison et taux de retard par État
SELECT
    c.customer_state                                       AS etat,
    COUNT(*)                                               AS nb_commandes,
    ROUND(AVG(julianday(o.order_delivered_customer_date)
            - julianday(o.order_purchase_timestamp)), 1)   AS delai_moyen_jours,
    ROUND(AVG(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date
                   THEN 1.0 ELSE 0 END) * 100, 1)          AS taux_retard_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY etat
ORDER BY delai_moyen_jours DESC;