DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS character;
DROP TABLE IF EXISTS comic;
DROP TABLE IF EXISTS comic_page;

-- ───────────────────────────────────────────────────────────────────
CREATE TABLE user (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL
);

CREATE TABLE character (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title     TEXT NOT NULL,
  image     BLOB NOT NULL,
  FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE comic (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  author_id INTEGER NOT NULL,
  created   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  title     TEXT NOT NULL,
  FOREIGN KEY (author_id) REFERENCES user (id)   -- ← kept
);

CREATE TABLE comic_page (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  comic_id    INTEGER NOT NULL,
  page_number INTEGER NOT NULL,
  image       BLOB    NOT NULL,
  created     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (comic_id) REFERENCES comic (id),
  UNIQUE (comic_id, page_number)
);