"""Données de référence : clubs, joueurs à floquer, entrepôts.

Ce sont des listes écrites à la main : elles décrivent le "monde" de la boutique.
Tout le reste (clients, commandes, stock) est généré aléatoirement à partir d'elles.
"""

# popularity : poids relatif dans les ventes (plus c'est haut, plus le club vend)
CLUBS = [
    # code, nom, championnat, pays, équipementier, popularité, joueurs (nom, numéro)
    ("PSG", "Paris Saint-Germain", "Ligue 1", "FR", "Nike", 10, [("DEMBELE", 10), ("HAKIMI", 2), ("VITINHA", 17)]),
    ("OM",  "Olympique de Marseille", "Ligue 1", "FR", "Puma", 7, [("GREENWOOD", 10), ("RULLI", 1)]),
    ("OL",  "Olympique Lyonnais", "Ligue 1", "FR", "Adidas", 5, [("TOLISSO", 8), ("FOFANA", 11)]),
    ("LOSC", "LOSC Lille", "Ligue 1", "FR", "New Balance", 3, [("ANDRE", 21), ("HARALDSSON", 7)]),
    ("RCL", "RC Lens", "Ligue 1", "FR", "Puma", 3, [("THOMASSON", 28)]),
    ("RMA", "Real Madrid", "LaLiga", "ES", "Adidas", 9, [("MBAPPE", 10), ("VINI JR", 7), ("BELLINGHAM", 5)]),
    ("FCB", "FC Barcelona", "LaLiga", "ES", "Nike", 9, [("YAMAL", 10), ("PEDRI", 8), ("RAPHINHA", 11)]),
    ("ATM", "Atletico Madrid", "LaLiga", "ES", "Nike", 4, [("GRIEZMANN", 7), ("ALVAREZ", 19)]),
    ("MCI", "Manchester City", "Premier League", "GB", "Puma", 7, [("HAALAND", 9), ("FODEN", 47)]),
    ("LIV", "Liverpool FC", "Premier League", "GB", "Adidas", 7, [("SALAH", 11), ("WIRTZ", 7)]),
    ("ARS", "Arsenal FC", "Premier League", "GB", "Adidas", 6, [("SAKA", 7), ("ODEGAARD", 8)]),
    ("MUN", "Manchester United", "Premier League", "GB", "Adidas", 6, [("FERNANDES", 8), ("MBEUMO", 19)]),
    ("JUV", "Juventus", "Serie A", "IT", "Adidas", 5, [("YILDIZ", 10), ("VLAHOVIC", 9)]),
    ("INT", "Inter Milan", "Serie A", "IT", "Nike", 5, [("LAUTARO", 10), ("THURAM", 9)]),
    ("ACM", "AC Milan", "Serie A", "IT", "Puma", 5, [("LEAO", 10), ("PULISIC", 11)]),
    ("FCBY", "Bayern Munich", "Bundesliga", "DE", "Adidas", 6, [("KANE", 9), ("MUSIALA", 10), ("OLISE", 17)]),
    ("BVB", "Borussia Dortmund", "Bundesliga", "DE", "Puma", 4, [("GUIRASSY", 9)]),
]

# Clubs qui ont aussi un maillot rétro, avec l'année du maillot d'origine
RETRO = {
    "OM": (1993, "Saison de la victoire en Ligue des champions"),
    "PSG": (1994, "Maillot Hechter"),
    "FCB": (2009, "Saison du sextuplé"),
    "MUN": (1999, "Saison du triplé"),
    "ACM": (1989, "Ère Sacchi"),
    "LIV": (2005, "Finale d'Istanbul"),
}

ADULT_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
KID_SIZES = ["6A", "8A", "10A", "12A", "14A"]
# Répartition des ventes par taille (les tailles du milieu se vendent plus)
SIZE_WEIGHTS = {"XS": 3, "S": 15, "M": 32, "L": 28, "XL": 15, "XXL": 7,
                "6A": 15, "8A": 22, "10A": 25, "12A": 23, "14A": 15}

# Prix en centimes selon (type, version, public)
PRICES = {
    ("replica", "adult"): 9999,
    ("authentic", "adult"): 14999,
    ("replica", "kid"): 7499,
    ("goalkeeper", "adult"): 9999,
    ("retro", "adult"): 8999,
}
FLOCKING_PRICE_CENTS = 1500

# Poids de vente selon le type de maillot (le domicile se vend le plus)
KIT_WEIGHTS = {"HOME-REP": 3.0, "AWAY-REP": 2.0, "THIRD-REP": 1.0, "HOME-AUTH": 0.7,
               "AWAY-AUTH": 0.4, "HOME-KID": 1.2, "GK-REP": 0.25, "RETRO": 0.6}

TECHNOLOGIES = {"Nike": "Dri-FIT ADV", "Adidas": "HEAT.RDY", "Puma": "ultraweave",
                "New Balance": "NB Dry"}

WAREHOUSES = [
    # id, code, ville, capacité (nombre de maillots)
    (1, "PAR-01", "Paris (Gonesse)", 12000),
    (2, "LYS-01", "Lyon (Saint-Priest)", 11000),
    (3, "MRS-01", "Marseille (Vitrolles)", 10500),
    (4, "LIL-01", "Lille (Lesquin)", 9200),
]

# Comptes applicatifs de démonstration : (identifiant, rôles, compte technique ?)
DEMO_USERS = [
    ("admin", ["admin"], False),
    ("lea.analyst", ["analyst"], False),
    ("karim.catalog", ["catalog_manager"], False),
    ("nora.logistics", ["logistics"], False),
    ("svc-orders", ["service_account"], True),
]
