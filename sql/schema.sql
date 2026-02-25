
PRAGMA foreign_keys = ON;

-- ===========================
-- CONTINENT TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS Continent (
    ContinentId INTEGER PRIMARY KEY,
    Continent TEXT NOT NULL
);

-- ===========================
-- REGION TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS Region (
    RegionId INTEGER PRIMARY KEY,
    Region TEXT NOT NULL,
    ContinentId INTEGER NOT NULL,
    FOREIGN KEY (ContinentId) REFERENCES Continent(ContinentId)
);

-- ===========================
-- COUNTRY TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS Country (
    CountryId INTEGER PRIMARY KEY,
    Country TEXT NOT NULL,
    RegionId INTEGER NOT NULL,
    FOREIGN KEY (RegionId) REFERENCES Region(RegionId)
);

-- ===========================
-- CITY TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS City (
    CityId INTEGER PRIMARY KEY,
    CityName TEXT NOT NULL,
    CountryId INTEGER NOT NULL,
    FOREIGN KEY (CountryId) REFERENCES Country(CountryId)
);

-- ===========================
-- USER TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS User (
    UserId INTEGER PRIMARY KEY,
    ContinentId INTEGER NOT NULL,
    RegionId INTEGER NOT NULL,
    CountryId INTEGER NOT NULL,
    CityId INTEGER NOT NULL,
    FOREIGN KEY (ContinentId) REFERENCES Continent(ContinentId),
    FOREIGN KEY (RegionId) REFERENCES Region(RegionId),
    FOREIGN KEY (CountryId) REFERENCES Country(CountryId),
    FOREIGN KEY (CityId) REFERENCES City(CityId)
);

-- ===========================
-- MODE TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS Mode (
    VisitModeId INTEGER PRIMARY KEY,
    VisitMode TEXT NOT NULL UNIQUE
);

-- ===========================
-- ATTRACTION TYPE TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS Type (
    AttractionTypeId INTEGER PRIMARY KEY,
    AttractionType TEXT NOT NULL
);

-- ===========================
-- ATTRACTION TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS Attraction (
    AttractionId INTEGER PRIMARY KEY,
    AttractionCityId INTEGER NOT NULL,
    AttractionTypeId INTEGER NOT NULL,
    Attraction TEXT NOT NULL,
    AttractionAddress TEXT,
    FOREIGN KEY (AttractionCityId) REFERENCES City(CityId),
    FOREIGN KEY (AttractionTypeId) REFERENCES Type(AttractionTypeId)
);

-- ===========================
-- TRANSACTION TABLE
-- ===========================
CREATE TABLE IF NOT EXISTS TransactionTable (
    TransactionId INTEGER PRIMARY KEY,
    UserId INTEGER NOT NULL,
    VisitYear INTEGER NOT NULL,
    VisitMonth INTEGER NOT NULL,
    VisitModeId INTEGER NOT NULL,
    AttractionId INTEGER NOT NULL,
    Rating REAL NOT NULL CHECK (Rating >= 1 AND Rating <= 5),
    FOREIGN KEY (UserId) REFERENCES User(UserId),
    FOREIGN KEY (VisitModeId) REFERENCES Mode(VisitModeId),
    FOREIGN KEY (AttractionId) REFERENCES Attraction(AttractionId)
);
