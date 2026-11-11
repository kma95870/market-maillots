// =====================================================================
// Catalogue des maillots (MongoDB).
// Exécuté au PREMIER démarrage du conteneur uniquement.
//
// Pourquoi un "validator" alors que MongoDB est sans schéma ?
// -> On impose les champs COMMUNS à tous les maillots (nom, club, prix...)
//    et on laisse le champ "attributs" totalement libre : c'est là que
//    vont les caractéristiques propres à chaque type de maillot.
// =====================================================================

const dbName = process.env.MONGO_DB || "catalog";
const catalog = db.getSiblingDB(dbName);

// Compte technique du service Catalogue : lecture/écriture sur SA base seulement
catalog.createUser({
  user: process.env.MONGO_CATALOG_USER,
  pwd: process.env.MONGO_CATALOG_PASSWORD,
  roles: [{ role: "readWrite", db: dbName }],
});

catalog.createCollection("products", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["id_produit", "nom", "club", "saison", "type_maillot", "version",
                 "marque", "prix_centimes", "tailles", "actif"],
      properties: {
        id_produit:    { bsonType: "string", description: "Identifiant partagé avec PostgreSQL" },
        nom:           { bsonType: "string" },
        club: {
          bsonType: "object",
          required: ["code", "nom", "championnat", "pays"],
          properties: {
            code:        { bsonType: "string" },
            nom:         { bsonType: "string" },
            championnat: { bsonType: "string" },
            pays:        { bsonType: "string" },
          },
        },
        saison:        { bsonType: "string", pattern: "^[0-9]{4}/[0-9]{2}$" },
        type_maillot:  { enum: ["home", "away", "third", "goalkeeper", "retro"] },
        version:       { enum: ["replica", "authentic"] },
        marque:        { bsonType: "string" },
        prix_centimes: { bsonType: "int", minimum: 0, description: "Prix en centimes d'euro" },
        tailles:       { bsonType: "array", minItems: 1, items: { bsonType: "string" } },
        flocage: {
          bsonType: "object",
          properties: {
            disponible:    { bsonType: "bool" },
            prix_centimes: { bsonType: "int", minimum: 0 },
            joueurs:       { bsonType: "array" },
          },
        },
        attributs:     { bsonType: "object", description: "Libre : dépend du type de maillot" },
        actif:         { bsonType: "bool" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

// Index : ce qui accélère les recherches les plus fréquentes
catalog.products.createIndex({ id_produit: 1 }, { unique: true });
catalog.products.createIndex({ "club.code": 1, saison: -1 });
catalog.products.createIndex({ type_maillot: 1, version: 1 });
catalog.products.createIndex({ nom: "text", "club.nom": "text" }); // recherche plein texte

print(`Catalogue initialisé dans la base "${dbName}"`);
