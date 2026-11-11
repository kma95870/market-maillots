// =====================================================================
// Catalogue des maillots (MongoDB).
// Exécuté au PREMIER démarrage du conteneur uniquement.
//
// Pourquoi un "validator" alors que MongoDB est sans schéma ?
// -> On impose les champs COMMUNS à tous les maillots (nom, club, prix...)
//    et on laisse le champ "attributes" totalement libre : c'est là que
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
      required: ["product_id", "name", "club", "season", "kit_type", "version",
                 "audience", "brand", "price_cents", "sizes", "is_active"],
      properties: {
        product_id:  { bsonType: "string", description: "Identifiant partagé avec PostgreSQL" },
        name:        { bsonType: "string" },
        club: {
          bsonType: "object",
          required: ["code", "name", "league", "country"],
          properties: {
            code:    { bsonType: "string" },
            name:    { bsonType: "string" },
            league:  { bsonType: "string" },
            country: { bsonType: "string" },
          },
        },
        season:      { bsonType: "string", pattern: "^[0-9]{4}/[0-9]{2}$" },
        kit_type:    { enum: ["home", "away", "third", "goalkeeper", "retro"] },
        version:     { enum: ["replica", "authentic"] },
        audience:    { enum: ["adult", "kid"] },
        brand:       { bsonType: "string" },
        price_cents: { bsonType: "int", minimum: 0, description: "Prix en centimes" },
        sizes:       { bsonType: "array", minItems: 1, items: { bsonType: "string" } },
        flocking: {
          bsonType: "object",
          properties: {
            available:   { bsonType: "bool" },
            price_cents: { bsonType: "int", minimum: 0 },
            players:     { bsonType: "array" },
          },
        },
        attributes:  { bsonType: "object", description: "Libre : dépend du type de maillot" },
        is_active:   { bsonType: "bool" },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});

// Index : ce qui accélère les recherches les plus fréquentes
catalog.products.createIndex({ product_id: 1 }, { unique: true });
catalog.products.createIndex({ "club.code": 1, season: -1 });
catalog.products.createIndex({ kit_type: 1, version: 1 });
catalog.products.createIndex({ name: "text", "club.name": "text" }); // recherche plein texte

print(`Catalogue initialisé dans la base "${dbName}"`);
