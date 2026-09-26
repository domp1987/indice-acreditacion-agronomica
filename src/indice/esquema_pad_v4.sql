-- Esquema v4: campos de la variante 2026 de los PAD (actividades desglosadas por semana).
ALTER TABLE pad ADD COLUMN relacion_creditos TEXT;            -- p. ej. '1-2' (así lo escribe el PAD)
ALTER TABLE pad_rea ADD COLUMN peso REAL;                     -- % del REA en la nota del CADI
ALTER TABLE pad_bibliografia ADD COLUMN url TEXT;             -- enlace al catálogo de la biblioteca o al recurso
ALTER TABLE pad_actividad ADD COLUMN analisis_retroalimentacion TEXT;   -- "Descripción de la Fase 7 y 8"

-- Fases del Modelo (MCA) y lo que ocurre en cada una en este CADI
CREATE TABLE IF NOT EXISTS pad_fase (
  pad_id INTEGER NOT NULL REFERENCES pad(id),
  orden INTEGER NOT NULL,
  fase TEXT NOT NULL,
  descripcion TEXT,
  PRIMARY KEY (pad_id, orden)
);
