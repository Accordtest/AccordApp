-- Opret databasen til Accord
CREATE DATABASE accordfinal_database;
USE accordfinal_database;


-- Tabel til salgsforespørgsler
CREATE TABLE Forespørgsler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    Titel VARCHAR(255),
    Kunstner VARCHAR(255),
    Type VARCHAR(50),
    Genre VARCHAR(100),
    Udgivelsesaar INT,
    KundeNavn VARCHAR(255),
    Email VARCHAR(255),
    Besked TEXT
);
ALTER TABLE Forespørgsler ADD COLUMN Dato TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

SELECT * FROM Forespørgsler;

CREATE TABLE Wishlist (
    WishlistID INT AUTO_INCREMENT PRIMARY KEY,
    Titel VARCHAR(255) NOT NULL,
    Kunstner VARCHAR(255) NOT NULL,
    Type VARCHAR(50),
    Genre VARCHAR(100),
    Udgivelsesaar INT,
    Besked TEXT,
    KundeNavn VARCHAR(100) NOT NULL,
    Email VARCHAR(100) NOT NULL,
    Dato TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
SELECT * FROM Wishlist;