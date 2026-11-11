"""Données de référence : le "monde" de la boutique, écrit à la main.

Rien n'est aléatoire dans ce fichier. Le générateur (generate.py) part de ces
listes et tire au hasard tout le reste : stock, clients, commandes, paiements.
"""

# Une ligne par club. Les colonnes, dans l'ordre :
#   code, nom, championnat, pays, équipementier, popularité, joueurs à floquer (nom, numéro)
# La popularité est un poids : un club à 10 vend environ 2 fois plus qu'un club à 5.
# Le PREMIER joueur de la liste est la star du club (il sera floqué plus souvent).
CLUBS = [
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

# Clubs qui ont aussi un maillot rétro : code du club -> (année du maillot d'origine, histoire)
RETRO = {
    "OM": (1993, "Saison de la victoire en Ligue des champions"),
    "PSG": (1994, "Maillot Hechter"),
    "FCB": (2009, "Saison du sextuplé"),
    "MUN": (1999, "Saison du triplé"),
    "ACM": (1989, "Ère Sacchi"),
    "LIV": (2005, "Finale d'Istanbul"),
}

# Tailles proposées. Un maillot enfant a des tailles en âge (6A = 6 ans).
TAILLES_ADULTE = ["XS", "S", "M", "L", "XL", "XXL"]
TAILLES_ENFANT = ["6A", "8A", "10A", "12A", "14A"]

# Poids de vente de chaque taille : M et L se vendent beaucoup plus que XS ou XXL.
POIDS_TAILLES = {"XS": 3, "S": 15, "M": 32, "L": 28, "XL": 15, "XXL": 7,
                 "6A": 15, "8A": 22, "10A": 25, "12A": 23, "14A": 15}

# Prix en centimes d'euro, selon (version ou type, public visé)
PRIX = {
    ("replica", "adulte"): 9999,      # 99,99 €
    ("authentic", "adulte"): 14999,   # 149,99 €
    ("replica", "enfant"): 7499,
    ("gardien", "adulte"): 9999,
    ("retro", "adulte"): 8999,
}
PRIX_FLOCAGE_CENTIMES = 1500           # 15 € pour le nom + le numéro

# Poids de vente de chaque type de maillot : le domicile se vend le plus, le gardien le moins.
# La clé est le suffixe de l'identifiant produit (ex. PSG-2526-HOME-REP).
POIDS_TYPES = {"HOME-REP": 3.0, "AWAY-REP": 2.0, "THIRD-REP": 1.0, "HOME-AUTH": 0.7,
               "AWAY-AUTH": 0.4, "HOME-KID": 1.2, "GK-REP": 0.25, "RETRO": 0.6}

# Technologie de tissu de chaque équipementier (sert aux maillots authentic).
# Si tu ajoutes un club avec un nouvel équipementier, ajoute-le ici aussi.
TECHNOLOGIES = {"Nike": "Dri-FIT ADV", "Adidas": "HEAT.RDY", "Puma": "ultraweave",
                "New Balance": "NB Dry"}

# Entrepôts : (id, ville, capacité en nombre de maillots)
ENTREPOTS = [
    (1, "Paris (Gonesse)", 12000),
    (2, "Lyon (Saint-Priest)", 11000),
    (3, "Marseille (Vitrolles)", 10500),
    (4, "Lille (Lesquin)", 9200),
]

# Comptes de l'équipe interne pour la démo : (email, liste des rôles)
# Un compte technique se reconnaît à son rôle service_account.
UTILISATEURS_DEMO = [
    ("admin@maillots.example", ["admin"]),
    ("lea.analyst@maillots.example", ["analyst"]),
    ("karim.catalog@maillots.example", ["catalog_manager"]),
    ("nora.logistics@maillots.example", ["logistics"]),
    ("svc-orders@maillots.example", ["service_account"]),
]
